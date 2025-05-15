# File: backend/app/api/endpoints/bahn.py
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from ...database import get_db
import logging
from tempfile import NamedTemporaryFile
import shutil

from ...utils.batch_processor import BatchProcessor
from ...utils.csv_processor import CSVProcessor
from ...utils.db_operations import DatabaseOperations
from ...utils.db_config import DB_PARAMS
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
        calibration: bool = Query(None, description="Nur Kalibrierungsläufe"),
        pick_place: bool = Query(None, description="Nur Pick-and-Place-Läufe"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
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

        if calibration is not None:
            base_query += f" AND calibration_run = ${param_index}"
            params.append(calibration)
            param_index += 1

        if pick_place is not None:
            base_query += f" AND pick_and_place = ${param_index}"
            params.append(pick_place)
            param_index += 1

        if points_events is not None:
            base_query += f" AND np_ereignisse = ${param_index}"
            params.append(points_events)
            param_index += 1

        if weight is not None:
            base_query += f" AND weight = ${param_index}"
            params.append(weight)
            param_index += 1

        if velocity is not None:
            base_query += f" AND velocity_picking = ${param_index}"
            params.append(velocity)
            param_index += 1

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


# Similar POST, PUT, and DELETE endpoints can be added for other models as needed

######################### CSV HOCHLADEN ##################################################

@router.post("/process-csv-batch")
async def process_csv_batch(
        files: list[UploadFile] = File(...),
        robot_model: str = Form(...),
        bahnplanung: str = Form(...),
        source_data_ist: str = Form(...),
        source_data_soll: str = Form(...),
        upload_database: bool = Form(...),
        segmentation_method: str = Form(default="fixed_segments"),  # Geändert zu fixed_segments als Standard
        num_segments: int = Form(default=3),  # Standardwert auf 3 erhöht
        reference_position: Optional[str] = Form(default=None),  # JSON-String für [x, y, z]
        conn=Depends(get_db)
):
    """Process multiple CSV files in a single batch upload"""
    try:
        start_time = datetime.now()
        logger.info(f"Starting batch processing of {len(files)} files at {start_time}")
        logger.info(f"Segmentation method: {segmentation_method}")

        # Parse reference_position aus JSON-String, wenn vorhanden
        ref_pos_tuple = None
        if reference_position:
            try:
                ref_pos_array = json.loads(reference_position)
                # Sicherstellen, dass es 3 Werte gibt und alle in Float umgewandelt werden können
                if len(ref_pos_array) == 3:
                    ref_pos_tuple = (float(ref_pos_array[0]), float(ref_pos_array[1]), float(ref_pos_array[2]))
                    logger.info(f"Reference position: {ref_pos_tuple}")
                else:
                    logger.warning(f"Invalid reference_position format: {reference_position}. Expected array with 3 elements.")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in reference_position: {reference_position}")
            except ValueError:
                logger.warning(f"Could not convert reference_position values to float: {reference_position}")

        # Validiere, dass Referenzpositionskoordinaten für reference_position-Methode bereitgestellt sind
        if segmentation_method == "reference_position" and ref_pos_tuple is None:
            raise HTTPException(
                status_code=400,
                detail="Reference position coordinates as JSON array [x, y, z] are required for 'reference_position' segmentation method"
            )

        # Create temporary files for each uploaded file
        temp_files = []
        files_and_paths = []

        for file in files:
            temp_file = NamedTemporaryFile(delete=False)
            shutil.copyfileobj(file.file, temp_file)
            temp_file.close()

            temp_files.append(temp_file.name)
            files_and_paths.append({
                'path': temp_file.name,
                'filename': file.filename
            })

        # Process all files in batch
        processor = BatchProcessor()
        file_results = await processor.process_csv_batch(
            files_and_paths,
            robot_model,
            bahnplanung,
            source_data_ist,
            source_data_soll,
            upload_database,
            segmentation_method,
            num_segments,
            conn,
            ref_pos_tuple  # Übergabe als Tuple, nicht als separate Parameter
        )

        # Clean up temporary files
        for temp_file in temp_files:
            os.unlink(temp_file)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Batch processing completed in {processing_time:.2f} seconds")

        return {
            "message": f"Batch processed {len(files)} files successfully",
            "processing_time_seconds": processing_time,
            "file_results": file_results
        }

    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        # Clean up any temporary files that might have been created
        for path in [f.get('path') for f in files_and_paths if 'path' in f]:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary file {path}: {str(cleanup_error)}")

        raise HTTPException(status_code=500, detail=f"Error in batch processing: {str(e)}")