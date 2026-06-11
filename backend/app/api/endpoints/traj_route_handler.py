from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

########################## BEWEGUNGSDATEN #########################################

@router.get("/traj_info")
async def get_traj_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # Zähle die Gesamtanzahl der Einträge für die Metadaten
        count_query = "SELECT COUNT(*) FROM motion.traj_info"
        total_count = await conn.fetchval(count_query)

        # Abfrage mit LIMIT und OFFSET für Pagination
        query = "SELECT * FROM motion.traj_info ORDER BY recording_date DESC LIMIT $1 OFFSET $2"
        rows = await conn.fetch(query, page_size, offset)

        traj_info_list = [dict(row) for row in rows]

        if not traj_info_list and page > 1:
            # Falls die angeforderte Seite keine Daten enthält, aber es gibt vorherige Seiten
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # Berechne die Gesamtanzahl der Seiten
        total_pages = (total_count + page_size - 1) // page_size

        # Pagination-Metadaten zum Ergebnis hinzufügen
        return {
            "traj_info": traj_info_list,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/traj_search")
async def search_traj_info(
        query: str = Query(None, description="Suchbegriff für Freitext-Suche (Filename, ID, Datum)"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        setted_velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
        recording_date: str = Query(None, description="Datumsfilter"),
        sidtw_distance: float = Query(None, description="SIDTW Distance (±10% Toleranz)"),
        conn=Depends(get_db)
):
    try:
        # Basis-Query erstellen
        base_query = """
                        SELECT b.*, i.sidtw_average_distance 
                        FROM motion.traj_info b
                        LEFT JOIN evaluation.sidtw_info i ON b.traj_id = i.traj_id AND i.traj_id = i.seg_id
                        WHERE 1=1
                    """
        params = []
        param_index = 1

        # Filter hinzufügen basierend auf Parametern
        if query:
            # Da traj_id ein varchar ist, behandeln wir alle Suchen als Text
            search_conditions = []

            # traj_id (teilweise Übereinstimmung)
            search_conditions.append(f"b.traj_id ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Dateiname (teilweise Übereinstimmung)
            search_conditions.append(f"b.record_filename ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Datum
            search_conditions.append(f"b.recording_date ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Alle Bedingungen mit OR verbinden
            base_query += f" AND ({' OR '.join(search_conditions)})"

        if points_events is not None:
            base_query += f" AND b.number_setpoints = ${param_index}"
            params.append(points_events)
            param_index += 1

        if weight is not None:
            tolerance = 0.5
            base_query += f" AND b.weight BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([weight - tolerance, weight + tolerance])
            param_index += 2

        if setted_velocity is not None:
            base_query += f" AND (b.setted_velocity = ${param_index})"
            params.append(setted_velocity)
            param_index += 1

        if recording_date is not None:
            if recording_date.isdigit() and len(recording_date) == 4:
                base_query += f" AND b.recording_date LIKE ${param_index}"
                params.append(f"{recording_date}-%")
                param_index += 1

            elif '.' in recording_date and ':' not in recording_date:
                try:
                    parts = recording_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        # Format: 2024-07-09
                        postgres_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        base_query += f" AND b.recording_date LIKE ${param_index}"
                        params.append(f"{postgres_date}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid date format: {recording_date}")

            elif '.' in recording_date and ':' in recording_date:
                try:
                    date_time_parts = recording_date.split(' ')
                    if len(date_time_parts) == 2:
                        date_part, time_part = date_time_parts
                        day, month, year = date_part.split('.')
                        hour, minute = time_part.split(':')

                        # Format: 2024-07-09 17:52
                        datetime_pattern = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}"
                        base_query += f" AND b.recording_date LIKE ${param_index}"
                        params.append(f"{datetime_pattern}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid datetime format: {recording_date}")
        
        if sidtw_distance is not None:
            tolerance = sidtw_distance * 0.1  # 10% Toleranz
            base_query += f" AND i.sidtw_average_distance IS NOT NULL AND i.sidtw_average_distance BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([sidtw_distance - tolerance, sidtw_distance + tolerance])
            param_index += 2

        # Zähle Gesamtanzahl für Pagination
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS filtered_data"
        total_count = await conn.fetchval(count_query, *params)

        # Füge Sortierung und Pagination hinzu
        query = base_query + f" ORDER BY b.recording_date DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([page_size, (page - 1) * page_size])

        rows = await conn.fetch(query, *params)
        traj_info_list = [dict(row) for row in rows]

        # Keine Ergebnisse und Seite > 1
        if not traj_info_list and page > 1:
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "traj_info": traj_info_list,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    except Exception as e:
        logger.error(f"Error searching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/traj_info/{traj_id}")
@cache(expire=24000)
async def get_traj_info_by_id(traj_id: str, conn = Depends(get_db)):
    try:
        traj_info = await conn.fetchrow(
            "SELECT * FROM motion.traj_info WHERE traj_id = $1",
            traj_id
        )
        if traj_info is None:
            raise HTTPException(status_code=404, detail="Bahn info not found")
        return dict(traj_info)
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/traj_pose_act/{traj_id}")
@cache(expire=2400)
async def get_traj_pose_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_pose_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_vel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_twist_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_vel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_accel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_accel_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_position_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_position_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_position_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/seg_position_cmd/{segment_id}")
@cache(expire=2400)
async def get_segment_position_soll_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_position_cmd WHERE seg_id = $1 ORDER BY timestamp ASC",
        segment_id
    )
    return [dict(row) for row in rows]


@router.get("/traj_orientation_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_orientation_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_orientation_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_vel_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_twist_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_vel_cmd FROM motion.traj_vel_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_joint_states/{traj_id}")
@cache(expire=2400)
async def get_traj_joint_states_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_joint_states WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_setpoints/{traj_id}")
@cache(expire=2400)
async def get_traj_events_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_setpoints WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]


