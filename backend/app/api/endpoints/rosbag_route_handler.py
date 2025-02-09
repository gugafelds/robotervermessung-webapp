
import rclpy
from ...utils.rosbag_processor import RosbagProcessor
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import tempfile
import shutil
import os
from pathlib import Path
import tarfile

router = APIRouter()
TEMP_DIR = tempfile.mkdtemp()

def get_final_csvs(directory):
    return list(Path(directory).glob('*_final.csv'))

@router.post("/process-rosbag")
def process_rosbag(file: UploadFile = File(...)):
    request_temp_dir = os.path.join(TEMP_DIR, str(hash(file.filename + str(os.urandom(8)))))
    os.makedirs(request_temp_dir, exist_ok=True)

    try:
        temp_file_path = os.path.join(request_temp_dir, file.filename)
        with open(temp_file_path, 'wb') as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        rclpy.init(args=None)
        processor = RosbagProcessor()
        success = processor.process_single_bag(temp_file_path, request_temp_dir)
        processor.destroy_node()
        rclpy.shutdown()

        if not success:
            raise HTTPException(status_code=500, detail="Processing failed")

        final_csvs = get_final_csvs(request_temp_dir)
        if not final_csvs:
            raise HTTPException(status_code=500, detail="No final CSV files were generated")

        if len(final_csvs) == 1:
            return FileResponse(
                path=str(final_csvs[0]),
                media_type='text/csv',
                filename=final_csvs[0].name
            )

        tar_path = os.path.join(request_temp_dir, f"{file.filename}_final_data.tar.gz")
        with tarfile.open(tar_path, "w:gz") as tar:
            for csv_file in final_csvs:
                tar.add(csv_file, arcname=csv_file.name)

        return FileResponse(
            path=tar_path,
            media_type='application/x-tar',
            filename=f"{file.filename}_final_data.tar.gz"
        )

    except Exception as e:
        shutil.rmtree(request_temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Error processing {file.filename}: {str(e)}")


@router.on_event("shutdown")
def cleanup():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)