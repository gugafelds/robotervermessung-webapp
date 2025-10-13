from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard_data")
async def get_dashboard_data(conn=Depends(get_db)):
    try:
        # Bahnen und Filenames zählen - diese sind wichtig genug für exakte Zählung
        filenames_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT record_filename) FROM bewegungsdaten.bahn_info"
        )

        bahnen_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT bahn_id) FROM bewegungsdaten.bahn_info"
        )

        stats = {}

        # Velocity Distribution
        velocity_query = """
            WITH vel_stats AS (
                SELECT MAX(max_twist_ist) as max_val
                FROM bewegungsdaten.bahn_meta
                WHERE bahn_id = segment_id
                  AND max_twist_ist IS NOT NULL
            )
            SELECT 
                width_bucket(max_twist_ist, 
                    0, 
                    (SELECT max_val FROM vel_stats), 
                    7
                ) AS bucket, 
                COUNT(*)
            FROM bewegungsdaten.bahn_meta
            WHERE bahn_id = segment_id
              AND max_twist_ist IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        velocity_rows = await conn.fetch(velocity_query)
        velocity_max = await conn.fetchval("""
            SELECT MAX(max_twist_ist) 
            FROM bewegungsdaten.bahn_meta 
            WHERE bahn_id = segment_id AND max_twist_ist IS NOT NULL
        """)
        stats["velocityDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in velocity_rows],
            "meta": {
                "useRanges": True,
                "min": 0,
                "max": velocity_max or 3000,
                "numBuckets": 7,
                "unit": "mm/s",
                "label": "Geschwindigkeit"
            }
        }

        # Weight Distribution
        weight_query = """
            SELECT weight AS bucket, COUNT(*)
            FROM bewegungsdaten.bahn_meta
            WHERE bahn_id = segment_id
              AND weight IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        weight_rows = await conn.fetch(weight_query)
        stats["weightDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in weight_rows],
            "meta": {
                "useRanges": False,
                "unit": "kg",
                "label": "Last"
            }
        }

        # Waypoint Distribution
        waypoints_query = """
            SELECT np_ereignisse AS bucket, COUNT(*)
            FROM bewegungsdaten.bahn_info
            GROUP BY bucket
            ORDER BY bucket
        """
        waypoint_rows = await conn.fetch(waypoints_query)
        stats["waypointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in waypoint_rows],
            "meta": {
                "useRanges": False,
                "unit": "-",
                "label": "Zielpunkte"
            }
        }

        # Performance SIDTW Distribution
        sidtw_query = """
            WITH sidtw_stats AS (
                SELECT MAX(i.sidtw_average_distance) as max_val
                FROM auswertung.info_sidtw i
                INNER JOIN bewegungsdaten.bahn_info b ON i.bahn_id = b.bahn_id
                WHERE i.bahn_id = i.segment_id
                  AND i.sidtw_average_distance IS NOT NULL
                  AND b.source_data_ist = 'leica_at960'
            )
            SELECT 
                width_bucket(i.sidtw_average_distance, 
                    0, 
                    (SELECT max_val FROM sidtw_stats), 
                    10
                ) AS bucket, 
                COUNT(*)
            FROM auswertung.info_sidtw i
            INNER JOIN bewegungsdaten.bahn_info b ON i.bahn_id = b.bahn_id
            WHERE i.bahn_id = i.segment_id
              AND i.sidtw_average_distance IS NOT NULL
              AND b.source_data_ist = 'leica_at960'
            GROUP BY bucket
            ORDER BY bucket
        """
        sidtw_rows = await conn.fetch(sidtw_query)
        sidtw_max = await conn.fetchval("""
            SELECT MAX(sidtw_average_distance) 
            FROM auswertung.info_sidtw i
            INNER JOIN bewegungsdaten.bahn_info b ON i.bahn_id = b.bahn_id
            WHERE i.bahn_id = i.segment_id 
              AND i.sidtw_average_distance IS NOT NULL
              AND b.source_data_ist = 'leica_at960'
        """)
        stats["performanceSIDTWDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in sidtw_rows],
            "meta": {
                "useRanges": True,
                "min": 0,
                "max": sidtw_max or 3.2475,
                "numBuckets": 10,
                "unit": "mm",
                "label": "Genauigkeit"
            }
        }

        # Stop Point Distribution
        stop_query = """
            SELECT stop_point AS bucket, COUNT(*)
            FROM bewegungsdaten.bahn_info
            WHERE stop_point IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        stop_rows = await conn.fetch(stop_query)
        stats["stopPointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in stop_rows],
            "meta": {
                "useRanges": False,
                "unit": "%",
                "label": "Stopp-Punkte"
            }
        }

        # Wait Time Distribution
        wait_query = """
            SELECT wait_time AS bucket, COUNT(*)
            FROM bewegungsdaten.bahn_info
            WHERE wait_time IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        wait_rows = await conn.fetch(wait_query)
        stats["waitTimeDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wait_rows],
            "meta": {
                "useRanges": False,
                "unit": "s",
                "label": "Wartezeit"
            }
        }

        return {
            "filenamesCount": filenames_count,
            "bahnenCount": bahnen_count,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/dashboard_sidtw_timeline")
@cache(expire=24600)
async def get_dashboard_sidtw_timeline(conn=Depends(get_db)):
    """
    Endpoint für SIDTW-Werte über Zeit
    Gibt durchschnittliche SIDTW-Werte pro Aufnahmedatum zurück
    """
    try:
        query = """
                SELECT
                    DATE (bi.recording_date) as date, AVG (info.sidtw_average_distance) as avg_sidtw, MIN (info.sidtw_average_distance) as min_sidtw, MAX (info.sidtw_average_distance) as max_sidtw, COUNT (*) as count
                FROM bewegungsdaten.bahn_info bi
                    INNER JOIN auswertung.info_sidtw info
                ON bi.bahn_id = info.bahn_id
                    AND bi.bahn_id = info.segment_id
                WHERE
                    bi.recording_date IS NOT NULL
                  AND info.sidtw_average_distance IS NOT NULL
                GROUP BY DATE (bi.recording_date)
                ORDER BY date ASC \
                """

        rows = await conn.fetch(query)

        return {
            "timeline": [
                {
                    "date": str(row['date']),
                    "avg_sidtw": float(row['avg_sidtw']),
                    "min_sidtw": float(row['min_sidtw']),
                    "max_sidtw": float(row['max_sidtw']),
                    "count": int(row['count'])
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/dashboard_sidtw_vs_parameters")
@cache(expire=24600)
async def get_dashboard_sidtw_vs_parameters(conn=Depends(get_db)):
    """
    Endpoint für SIDTW vs. verschiedene Bewegungsparameter als Box Plot Daten
    Gruppiert Parameter in Bins und gibt alle SIDTW-Werte pro Bin zurück
    """
    try:
        query = """
                WITH sampled_data AS (SELECT info.sidtw_average_distance as sidtw, \
                                             bm.max_twist_ist            as velocity, \
                                             bm.max_acceleration_ist     as acceleration, \
                                             bm.weight                   as weight, \
                                             bi.stop_point               as stop_point, \
                                             bi.wait_time                as wait_time \
                                      FROM auswertung.info_sidtw info \
                                               INNER JOIN bewegungsdaten.bahn_meta bm \
                                                          ON info.bahn_id = bm.bahn_id \
                                                              AND info.bahn_id = bm.segment_id \
                                                              AND bm.bahn_id = bm.segment_id \
                                               INNER JOIN bewegungsdaten.bahn_info bi \
                                                          ON info.bahn_id = bi.bahn_id \
                                      WHERE info.bahn_id = info.segment_id \
                                        AND info.sidtw_average_distance IS NOT NULL \
                                        AND bi.source_data_ist = 'leica_at960' \
                                        AND bm.max_twist_ist IS NOT NULL \
                                        AND bm.max_acceleration_ist IS NOT NULL \
                                        AND bm.weight IS NOT NULL \
                                        AND bi.stop_point IS NOT NULL \
                                        AND bi.wait_time IS NOT NULL \
                                      ORDER BY RANDOM()
                    LIMIT 10000
                    )
                SELECT * \
                FROM sampled_data \
                """

        rows = await conn.fetch(query)

        # Gib Rohdaten zurück - Binning wird im Frontend gemacht
        return {
            "data": [
                {
                    "sidtw": float(row['sidtw']),
                    "velocity": float(row['velocity']),
                    "acceleration": float(row['acceleration']),
                    "weight": float(row['weight']),
                    "stop_point": float(row['stop_point']),
                    "wait_time": float(row['wait_time'])
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW vs parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/dashboard_workarea")
@cache(expire=24600)
async def get_dashboard_workarea(conn=Depends(get_db)):
    try:
        workarea_query = """
                         WITH numbered_events AS (SELECT be.x_reached, \
                                                         be.y_reached, \
                                                         be.z_reached, \
                                                         s.sidtw_average_distance, \
                                                         ROW_NUMBER() OVER (PARTITION BY be.bahn_id ORDER BY be.timestamp) as rn \
                                                  FROM bewegungsdaten.bahn_events be \
                                                           JOIN auswertung.info_sidtw s ON be.bahn_id = s.bahn_id \
                                                           JOIN bewegungsdaten.bahn_info bi ON be.bahn_id = bi.bahn_id \
                                                  WHERE s.bahn_id <> s.segment_id \
                                                    AND s.sidtw_average_distance IS NOT NULL \
                                                    AND be.x_reached IS NOT NULL \
                                                    AND be.y_reached IS NOT NULL \
                                                    AND be.z_reached IS NOT NULL \
                                                    AND bi.recording_date >= '2025-03-01'
                         )
                         SELECT x_reached, y_reached, z_reached, sidtw_average_distance
                         FROM numbered_events
                         WHERE rn % 1 = 0 \
                         """

        workarea_rows = await conn.fetch(workarea_query)

        return {
            "points": [
                {
                    "x": r["x_reached"],
                    "y": r["y_reached"],
                    "z": r["z_reached"],
                    "sidtw": r["sidtw_average_distance"]
                }
                for r in workarea_rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching workarea data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

########################## BEWEGUNGSDATEN #########################################

@router.get("/bahn_info")
async def get_bahn_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # Zähle die Gesamtanzahl der Einträge für die Metadaten
        count_query = "SELECT COUNT(*) FROM bewegungsdaten.bahn_info"
        total_count = await conn.fetchval(count_query)

        # Abfrage mit LIMIT und OFFSET für Pagination
        query = "SELECT * FROM bewegungsdaten.bahn_info ORDER BY recording_date DESC LIMIT $1 OFFSET $2"
        rows = await conn.fetch(query, page_size, offset)

        bahn_info_list = [dict(row) for row in rows]

        if not bahn_info_list and page > 1:
            # Falls die angeforderte Seite keine Daten enthält, aber es gibt vorherige Seiten
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # Berechne die Gesamtanzahl der Seiten
        total_pages = (total_count + page_size - 1) // page_size

        # Pagination-Metadaten zum Ergebnis hinzufügen
        return {
            "bahn_info": bahn_info_list,
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


@router.get("/bahn_search")
async def search_bahn_info(
        query: str = Query(None, description="Suchbegriff für Freitext-Suche (Filename, ID, Datum)"),
        pick_place: bool = Query(None, description="Nur Pick-and-Place-Läufe"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        setted_velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
        recording_date: str = Query(None, description="Datumsfilter"),
        conn=Depends(get_db)
):
    try:
        # Basis-Query erstellen
        base_query = "SELECT * FROM bewegungsdaten.bahn_info WHERE 1=1"
        params = []
        param_index = 1

        # Filter hinzufügen basierend auf Parametern
        if query:
            # Da bahn_id ein varchar ist, behandeln wir alle Suchen als Text
            search_conditions = []

            # bahn_id (teilweise Übereinstimmung)
            search_conditions.append(f"bahn_id ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Dateiname (teilweise Übereinstimmung)
            search_conditions.append(f"record_filename ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Datum
            search_conditions.append(f"recording_date ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Alle Bedingungen mit OR verbinden
            base_query += f" AND ({' OR '.join(search_conditions)})"

        if pick_place is not None:
            base_query += f" AND pick_and_place = ${param_index}"
            params.append(pick_place)
            param_index += 1

        if points_events is not None:
            base_query += f" AND np_ereignisse = ${param_index}"
            params.append(points_events)
            param_index += 1

        if weight is not None:
            tolerance = 0.5
            base_query += f" AND weight BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([weight - tolerance, weight + tolerance])
            param_index += 2

        if setted_velocity is not None:
            base_query += f" AND setted_velocity = ${param_index} OR velocity_picking = ${param_index}"
            params.append(setted_velocity)
            param_index += 1

        if recording_date is not None:
            # Jahr (4 Ziffern): 2024
            if recording_date.isdigit() and len(recording_date) == 4:
                base_query += f" AND recording_date LIKE ${param_index}"
                params.append(f"{recording_date}-%")
                param_index += 1

            # DD.MM.YYYY Format: 09.07.2024
            elif '.' in recording_date and ':' not in recording_date:
                try:
                    parts = recording_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        # Format: 2024-07-09
                        postgres_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        base_query += f" AND recording_date LIKE ${param_index}"
                        params.append(f"{postgres_date}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid date format: {recording_date}")

            # DD.MM.YYYY HH:MM Format: 09.07.2024 17:52
            elif '.' in recording_date and ':' in recording_date:
                try:
                    date_time_parts = recording_date.split(' ')
                    if len(date_time_parts) == 2:
                        date_part, time_part = date_time_parts
                        day, month, year = date_part.split('.')
                        hour, minute = time_part.split(':')

                        # Format: 2024-07-09 17:52
                        datetime_pattern = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}"
                        base_query += f" AND recording_date LIKE ${param_index}"
                        params.append(f"{datetime_pattern}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid datetime format: {recording_date}")

        # Zähle Gesamtanzahl für Pagination
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS filtered_data"
        total_count = await conn.fetchval(count_query, *params)

        # Füge Sortierung und Pagination hinzu
        query = base_query + f" ORDER BY recording_date DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([page_size, (page - 1) * page_size])

        rows = await conn.fetch(query, *params)
        bahn_info_list = [dict(row) for row in rows]

        # Keine Ergebnisse und Seite > 1
        if not bahn_info_list and page > 1:
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "bahn_info": bahn_info_list,
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

@router.get("/bahn_info/{bahn_id}")
@cache(expire=24000)
async def get_bahn_info_by_id(bahn_id: str, conn = Depends(get_db)):
    try:
        bahn_info = await conn.fetchrow(
            "SELECT * FROM bewegungsdaten.bahn_info WHERE bahn_id = $1",
            bahn_id
        )
        if bahn_info is None:
            raise HTTPException(status_code=404, detail="Bahn info not found")
        return dict(bahn_info)
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/check_transformed_data/{bahn_id}")
@cache(expire=24000)
async def check_transformed_data(bahn_id: str, conn = Depends(get_db)):
    try:
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM bewegungsdaten.bahn_pose_trans 
                WHERE bahn_id = $1
                LIMIT 1
            )
        """, bahn_id)
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking transformed data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bahn_pose_ist/{bahn_id}")
@cache(expire=2400)
async def get_bahn_pose_ist_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_pose_ist WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_pose_trans/{bahn_id}")
@cache(expire=2400)
async def get_bahn_pose_trans_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_pose_trans WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]


@router.get("/bahn_twist_ist/{bahn_id}")
@cache(expire=2400)
async def get_bahn_twist_ist_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_twist_ist WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_accel_ist/{bahn_id}")
@cache(expire=2400)
async def get_bahn_accel_ist_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_accel_ist WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_accel_soll/{bahn_id}")
@cache(expire=2400)
async def get_bahn_accel_soll_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_accel_soll WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_position_soll/{bahn_id}")
@cache(expire=2400)
async def get_bahn_position_soll_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_position_soll WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/segment_position_soll/{segment_id}")
@cache(expire=2400)
async def get_segment_position_soll_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_position_soll WHERE segment_id = $1 ORDER BY timestamp ASC",
        segment_id
    )
    return [dict(row) for row in rows]


@router.get("/bahn_orientation_soll/{bahn_id}")
@cache(expire=2400)
async def get_bahn_orientation_soll_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_orientation_soll WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_twist_soll/{bahn_id}")
@cache(expire=2400)
async def get_bahn_twist_soll_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_speed_soll FROM bewegungsdaten.bahn_twist_soll WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_joint_states/{bahn_id}")
@cache(expire=2400)
async def get_bahn_joint_states_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_joint_states WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_events/{bahn_id}")
@cache(expire=2400)
async def get_bahn_events_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_events WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]

@router.get("/segment_events/{segment_id}")
@cache(expire=2400)
async def get_segment_events_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_events WHERE segment_id = $1 ORDER BY timestamp ASC",
        segment_id
    )
    return [dict(row) for row in rows]

@router.get("/bahn_imu/{bahn_id}")
@cache(expire=2400)
async def get_bahn_imu_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_imu WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]


