import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ...database import get_db
import logging

from tempfile import NamedTemporaryFile
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ...utils.batch_processor import BatchProcessor

router = APIRouter()

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