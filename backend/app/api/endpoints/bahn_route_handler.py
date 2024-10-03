# File: backend/app/api/endpoints/bahn.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from ...database import get_db
from ...models.bahn_models import (
    BahnInfoDB, BahnPoseIstDB, BahnTwistIstDB, BahnAccelIstDB,
    BahnPositionSollDB, BahnOrientationSollDB, BahnTwistSollDB,
    BahnJointStatesDB, BahnEventsDB
)

from ...utils.db_operations import DatabaseOperations
from ...utils.db_config import DB_PARAMS

# Add these imports at the top of the file
from fastapi import UploadFile, File, Form
from tempfile import NamedTemporaryFile
import shutil

from ...utils.csv_processor import CSVProcessor

from sqlalchemy.testing.plugin.plugin_base import logging

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


###########################  DASHBOARD  #####################################
@router.get("/dashboard_data")
def get_dashboard_data(db: Session = Depends(get_db)):
    try:
        trajectories_count = db.query(func.count(func.distinct(BahnInfoDB.record_filename))).scalar()

        component_counts = {
            "bahnPoseIst": db.query(func.count(BahnPoseIstDB.id)).scalar(),
            "bahnTwistIst": db.query(func.count(BahnTwistIstDB.id)).scalar(),
            "bahnAccelIst": db.query(func.count(BahnAccelIstDB.id)).scalar(),
            "bahnPositionSoll": db.query(func.count(BahnPositionSollDB.id)).scalar(),
            "bahnOrientationSoll": db.query(func.count(BahnOrientationSollDB.id)).scalar(),
            "bahnJointStates": db.query(func.count(BahnJointStatesDB.id)).scalar(),
            "bahnEvents": db.query(func.count(BahnEventsDB.id)).scalar(),
        }

        frequency_result = db.execute(text("""
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
        """))

        frequency_data = {}
        for row in frequency_result:
            rounded_frequency = round(row.exact_frequency / 100) * 100
            key = str(rounded_frequency)
            if key not in frequency_data:
                frequency_data[key] = []
            frequency_data[key].extend(row.ids)

        return {
            "trajectoriesCount": trajectories_count,
            "componentCounts": component_counts,
            "frequencyData": frequency_data
        }
    except Exception as e:
        logging.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


###########################  BEWEGUNGSDATEN  #####################################

@router.get("/bahn_info")
def get_bahn_info(db: Session = Depends(get_db)):
    try:
        logger.info("Entering get_bahn_info function")
        query = text("""
            SELECT * FROM bewegungsdaten.bahn_info
            ORDER BY recording_date DESC
        """)
        logger.info(f"Executing query: {query}")
        result = db.execute(query)
        bahn_info_list = [dict(row._mapping) for row in result]
        if not bahn_info_list:
            logger.warning("No Bahn info found")
            raise HTTPException(status_code=404, detail="No Bahn info found")
        return {"bahn_info": bahn_info_list}
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/bahn_info/{bahn_id}")
def get_bahn_info_by_id(bahn_id: str, db: Session = Depends(get_db)):
    bahn_info = db.query(BahnInfoDB).filter(BahnInfoDB.bahn_id == bahn_id).first()
    if bahn_info is None:
        raise HTTPException(status_code=404, detail="Bahn info not found")
    return bahn_info


@router.get("/bahn_pose_ist/{bahn_id}")
def get_bahn_pose_ist_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnPoseIstDB).filter(BahnPoseIstDB.bahn_id == bahn_id).order_by(
        BahnPoseIstDB.timestamp.asc()).all()


@router.get("/bahn_twist_ist/{bahn_id}")
def get_bahn_twist_ist_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnTwistIstDB).filter(BahnTwistIstDB.bahn_id == bahn_id).order_by(
        BahnTwistIstDB.timestamp.asc()).all()


@router.get("/bahn_accel_ist/{bahn_id}")
def get_bahn_accel_ist_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnAccelIstDB).filter(BahnAccelIstDB.bahn_id == bahn_id).order_by(
        BahnAccelIstDB.timestamp.asc()).all()


@router.get("/bahn_position_soll/{bahn_id}")
def get_bahn_position_soll_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnPositionSollDB).filter(BahnPositionSollDB.bahn_id == bahn_id).order_by(
        BahnPositionSollDB.timestamp.asc()).all()


@router.get("/bahn_orientation_soll/{bahn_id}")
def get_bahn_orientation_soll_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnOrientationSollDB).filter(BahnOrientationSollDB.bahn_id == bahn_id).order_by(
        BahnOrientationSollDB.timestamp.asc()).all()


@router.get("/bahn_twist_soll/{bahn_id}")
def get_bahn_twist_soll_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnTwistSollDB).filter(BahnTwistSollDB.bahn_id == bahn_id).order_by(
        BahnTwistSollDB.timestamp.asc()).all()


@router.get("/bahn_joint_states/{bahn_id}")
def get_bahn_joint_states_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnJointStatesDB).filter(BahnJointStatesDB.bahn_id == bahn_id).order_by(
        BahnJointStatesDB.timestamp.asc()).all()


@router.get("/bahn_events/{bahn_id}")
def get_bahn_events_by_id(bahn_id: str, db: Session = Depends(get_db)):
    return db.query(BahnEventsDB).filter(BahnEventsDB.bahn_id == bahn_id).order_by(BahnEventsDB.timestamp.asc()).all()


# Similar POST, PUT, and DELETE endpoints can be added for other models as needed

######################### CSV HOCHLADEN ##################################################

# Add this new endpoint to your existing router
@router.post("/process-csv")
async def process_csv(
        file: UploadFile = File(...),
        robot_model: str = Form(...),
        bahnplanung: str = Form(...),
        source_data_ist: str = Form(...),
        source_data_soll: str = Form(...),
        upload_database: bool = Form(...),
        db: Session = Depends(get_db)
):
    try:
        # Save the uploaded file temporarily
        with NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        record_filename = file.filename

        # Process the CSV file
        csv_processor = CSVProcessor(temp_file_path)
        processed_data = csv_processor.process_csv(
            upload_database,
            robot_model,
            bahnplanung,
            source_data_ist,
            source_data_soll,
            record_filename
        )

        # Upload to database if requested
        if upload_database:
            save_processed_data_to_db(processed_data)

        # Clean up the temporary file
        import os
        os.unlink(temp_file_path)

        return {"message": "CSV processed successfully", "data": processed_data}
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


def save_processed_data_to_db(processed_data):
    db_ops = DatabaseOperations(DB_PARAMS)
    conn = db_ops.connect_to_db()
    try:
        db_ops.insert_bahn_info(conn, processed_data['bahn_info_data'])
        db_ops.insert_rapid_events_data(conn, processed_data['RAPID_EVENTS_MAPPING'])
        db_ops.insert_pose_data(conn, processed_data['POSE_MAPPING'])
        db_ops.insert_position_soll_data(conn, processed_data['POSITION_SOLL_MAPPING'])
        db_ops.insert_orientation_soll_data(conn, processed_data['ORIENTATION_SOLL_MAPPING'])
        db_ops.insert_twist_ist_data(conn, processed_data['TWIST_IST_MAPPING'])
        db_ops.insert_twist_soll_data(conn, processed_data['TWIST_SOLL_MAPPING'])
        db_ops.insert_accel_data(conn, processed_data['ACCEL_MAPPING'])
        db_ops.insert_joint_data(conn, processed_data['JOINT_MAPPING'])

        logger.info(f"Data for bahn_id {processed_data['bahn_info_data'][0]} inserted successfully")
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()
