from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard_data")
@cache(expire=86400)  # 24 Stunden
async def get_dashboard_data(conn=Depends(get_db)):
    try:
        # Bahnen und Filenames zählen - diese sind wichtig genug für exakte Zählung
        filenames_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT record_filename) FROM bewegungsdaten.bahn_info"
        )

        bahnen_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT bahn_id) FROM bewegungsdaten.bahn_info"
        )

        # Für die anderen Tabellen verwenden wir Statistiken
        # Die n_distinct Spalte in pg_stats gibt Schätzungen der Anzahl eindeutiger Werte
        component_counts = {}
        for table, key in [
            ('bahn_pose_ist', 'bahnPoseIst'),
            ('bahn_twist_ist', 'bahnTwistIst'),
            ('bahn_twist_soll', 'bahnTwistSoll'),
            ('bahn_accel_ist', 'bahnAccelIst'),
            ('bahn_position_soll', 'bahnPositionSoll'),
            ('bahn_orientation_soll', 'bahnOrientationSoll'),
            ('bahn_accel_soll', 'bahnAccelSoll'),
            ('bahn_joint_states', 'bahnJointStates'),
            ('bahn_events', 'bahnEvents'),
            ('bahn_pose_trans', 'bahnPoseTrans'),
        ]:
            # Zuerst prüfen wir, ob Statistiken vorhanden sind
            stats_query = """
            SELECT 
                CASE 
                    WHEN n_distinct > 0 THEN n_distinct::integer  -- Positive Werte sind absolute Anzahlen
                    WHEN n_distinct < 0 THEN (-n_distinct * reltuples)::integer  -- Negative Werte sind Prozentsätze
                    ELSE 0
                END as distinct_count
            FROM pg_stats 
            JOIN pg_class ON pg_stats.tablename = pg_class.relname
            WHERE 
                pg_stats.schemaname = 'bewegungsdaten'
                AND pg_stats.tablename = $1
                AND pg_stats.attname = 'bahn_id'
            """

            distinct_count = await conn.fetchval(stats_query, table)

            # Fallback zu direkter Zählung, falls keine Statistiken verfügbar
            if distinct_count is None:
                count_query = f"SELECT COUNT(DISTINCT bahn_id) FROM bewegungsdaten.{table}"
                distinct_count = await conn.fetchval(count_query)

                # Nach der Zählung ANALYZE ausführen, damit künftige Statistik-Abfragen funktionieren
                analyze_query = f"ANALYZE bewegungsdaten.{table}(bahn_id)"
                await conn.execute(analyze_query)

            component_counts[key] = distinct_count or 0

        # Gleiches Vorgehen für Auswertungstabellen
        analysis_counts = {}
        for table, key in [
            ('info_dfd', 'infoDFD'),
            ('info_dtw', 'infoDTW'),
            ('info_euclidean', 'infoEA'),
            ('info_lcss', 'infoLCSS'),
            ('info_sidtw', 'infoSIDTW'),
        ]:
            stats_query = """
            SELECT 
                CASE 
                    WHEN n_distinct > 0 THEN n_distinct::integer  -- Positive Werte sind absolute Anzahlen
                    WHEN n_distinct < 0 THEN (-n_distinct * reltuples)::integer  -- Negative Werte sind Prozentsätze
                    ELSE 0
                END as distinct_count
            FROM pg_stats 
            JOIN pg_class ON pg_stats.tablename = pg_class.relname
            WHERE 
                pg_stats.schemaname = 'auswertung'
                AND pg_stats.tablename = $1
                AND pg_stats.attname = 'bahn_id'
            """

            distinct_count = await conn.fetchval(stats_query, table)

            # Fallback zu direkter Zählung
            if distinct_count is None:
                count_query = f"SELECT COUNT(DISTINCT bahn_id) FROM auswertung.{table}"
                distinct_count = await conn.fetchval(count_query)

                # Nach der Zählung ANALYZE ausführen
                analyze_query = f"ANALYZE auswertung.{table}(bahn_id)"
                await conn.execute(analyze_query)

            analysis_counts[key] = distinct_count or 0

        return {
            "filenamesCount": filenames_count,
            "bahnenCount": bahnen_count,
            "componentCounts": component_counts,
            "analysisCounts": analysis_counts,
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
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

@router.get("/bahn_imu/{bahn_id}")
@cache(expire=2400)
async def get_bahn_imu_by_id(bahn_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM bewegungsdaten.bahn_imu WHERE bahn_id = $1 ORDER BY timestamp ASC",
        bahn_id
    )
    return [dict(row) for row in rows]


