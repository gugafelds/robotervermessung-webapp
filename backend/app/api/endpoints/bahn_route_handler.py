# File: backend/app/api/endpoints/bahn.py
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ...database import get_db
import logging
from tempfile import NamedTemporaryFile
import shutil
from ...utils.csv_processor import CSVProcessor
from ...utils.db_operations import DatabaseOperations
from ...utils.db_config import DB_PARAMS
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard_data")
@cache(expire=24000)
async def get_dashboard_data(conn = Depends(get_db)):
    try:
        filenames_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT record_filename) FROM bewegungsdaten.bahn_info"
        )

        bahnen_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT bahn_id) FROM bewegungsdaten.bahn_info"
        )
        

        component_counts = {
            "bahnPoseIst": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_pose_ist"),
            "bahnTwistIst": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_twist_ist"),
            "bahnAccelIst": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_accel_ist"),
            "bahnPositionSoll": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_position_soll"),
            "bahnOrientationSoll": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_orientation_soll"),
            "bahnJointStates": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_joint_states"),
            "bahnEvents": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_events"),
            "bahnPoseTrans": await conn.fetchval("SELECT COUNT(*) FROM bewegungsdaten.bahn_pose_trans"),
        }

        frequency_result = await conn.fetch("""
            SELECT 
                CASE 
                    WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
                    WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
                    WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
                    ELSE 0
                END as exact_frequency,
                ARRAY_AGG(bahn_id) as ids
            FROM bewegungsdaten.bahn_info
            GROUP BY 
                CASE 
                    WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
                    WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
                    WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
                    ELSE 0
                END
            HAVING 
                CASE 
                    WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
                    WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
                    WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
                    ELSE 0
                END > 0
            ORDER BY exact_frequency DESC
        """)

        frequency_data = {}
        for row in frequency_result:
            rounded_frequency = round(row['exact_frequency'] / 100) * 100
            key = str(rounded_frequency)
            if key not in frequency_data:
                frequency_data[key] = []
            frequency_data[key].extend(row['ids'])

        return {
            "filenamesCount": filenames_count,
            "bahnenCount": bahnen_count,
            "componentCounts": component_counts,
            "frequencyData": frequency_data
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/collection_sizes")
@cache(expire=24000)
async def get_collection_sizes(conn = Depends(get_db)):
    try:
        collection_sizes = {
            "bahnPoseIst": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_pose_ist')"
            ),
            "bahnTwistIst": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_twist_ist')"
            ),
            "bahnAccelIst": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_accel_ist')"
            ),
            "bahnPositionSoll": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_position_soll')"
            ),
            "bahnOrientationSoll": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_orientation_soll')"
            ),
            "bahnJointStates": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_joint_states')"
            ),
            "bahnEvents": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_events')"
            ),
            "bahnPoseTrans": await conn.fetchval(
                "SELECT pg_total_relation_size('bewegungsdaten.bahn_pose_trans')"
            ),
        }

        # Convert bytes to MB
        return {k: round(v / (1024 * 1024), 2) for k, v in collection_sizes.items()}
    except Exception as e:
        logger.error(f"Error fetching collection sizes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

########################## BEWEGUNGSDATEN #########################################

@router.get("/bahn_info")
async def get_bahn_info(conn = Depends(get_db)):
    try:
        query = "SELECT * FROM bewegungsdaten.bahn_info ORDER BY recording_date DESC"
        rows = await conn.fetch(query)
        bahn_info_list = [dict(row) for row in rows]
        if not bahn_info_list:
            logger.warning("No Bahn info found")
            raise HTTPException(status_code=404, detail="No Bahn info found")
        return {"bahn_info": bahn_info_list}
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
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
        "SELECT * FROM bewegungsdaten.bahn_twist_soll WHERE bahn_id = $1 ORDER BY timestamp ASC",
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


# Similar POST, PUT, and DELETE endpoints can be added for other models as needed

######################### CSV HOCHLADEN ##################################################

@router.post("/process-csv")
async def process_csv(
        file: UploadFile = File(...),
        robot_model: str = Form(...),
        bahnplanung: str = Form(...),
        source_data_ist: str = Form(...),
        source_data_soll: str = Form(...),
        upload_database: bool = Form(...),
        segmentation_method: str = Form(default="home"),  # Neue Parameter
        num_segments: int = Form(default=1),  # Neue Parameter
        conn=Depends(get_db)
):
    try:
        with NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        record_filename = file.filename

        csv_processor = CSVProcessor(temp_file_path)
        processed_data_list = csv_processor.process_csv(
            upload_database,
            robot_model,
            bahnplanung,
            source_data_ist,
            source_data_soll,
            record_filename,
            segmentation_method,  # Neue Parameter weitergeben
            num_segments  # Neue Parameter weitergeben
        )

        if upload_database and processed_data_list:
            segments_processed = len(processed_data_list)
            for segment_data in processed_data_list:
                await save_processed_data_to_db(segment_data, conn)
                logger.info(f"Processed segment with bahn_id {segment_data['bahn_info_data'][0]}")

        os.unlink(temp_file_path)

        return {
            "message": f"CSV processed successfully. Found {len(processed_data_list)} segments",
            "segments_found": len(processed_data_list),
            "data": processed_data_list
        }
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


async def save_processed_data_to_db(processed_data, conn):
    if not isinstance(processed_data, dict):
        raise ValueError(f"Expected dict but got {type(processed_data)}")

    try:
        db_ops = DatabaseOperations(DB_PARAMS)

        if 'bahn_info_data' not in processed_data:
            raise ValueError("No bahn_info_data found in processed data")

        # Insert bahn_info
        await db_ops.insert_bahn_info(conn, processed_data['bahn_info_data'])

        # Define mapping of data types to their insertion functions
        data_mappings = [
            ('RAPID_EVENTS_MAPPING', db_ops.insert_rapid_events_data),
            ('POSE_MAPPING', db_ops.insert_pose_data),
            ('POSITION_SOLL_MAPPING', db_ops.insert_position_soll_data),
            ('ORIENTATION_SOLL_MAPPING', db_ops.insert_orientation_soll_data),
            ('TWIST_IST_MAPPING', db_ops.insert_twist_ist_data),
            ('TWIST_SOLL_MAPPING', db_ops.insert_twist_soll_data),
            ('ACCEL_MAPPING', db_ops.insert_accel_data),
            ('JOINT_MAPPING', db_ops.insert_joint_data)
        ]

        # Insert each type of data
        bahn_id = processed_data['bahn_info_data'][0]
        for mapping_key, insert_func in data_mappings:
            if mapping_key in processed_data and processed_data[mapping_key]:
                try:
                    await insert_func(conn, processed_data[mapping_key])
                    logger.info(f"Inserted {mapping_key} data for bahn_id {bahn_id}")
                except Exception as e:
                    logger.error(f"Error inserting {mapping_key} for bahn_id {bahn_id}: {str(e)}")
                    raise

        logger.info(f"All data for bahn_id {bahn_id} inserted successfully")
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")