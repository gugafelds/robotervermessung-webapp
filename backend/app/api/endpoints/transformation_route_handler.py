import numpy as np
import asyncpg
import logging
from fastapi import APIRouter, Depends, HTTPException
from ...database import get_db
from typing import Dict
import matlab.engine
import os
import datetime
from pathlib import Path

router = APIRouter()


# Initialize MATLAB engine singleton
class MatlabEngine:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = matlab.engine.start_matlab()
            # Get the path to your MATLAB scripts
            matlab_scripts_path = os.getenv("MATLAB_SCRIPTS_PATH", "path/to/your/matlab/scripts")
            if not Path(matlab_scripts_path).exists():
                raise RuntimeError(f"MATLAB scripts path not found: {matlab_scripts_path}")
            cls._instance.addpath(matlab_scripts_path)
        return cls._instance


async def transform_trajectory_matlab(
        conn: asyncpg.Connection,
        bahn_id: str = None,
        schema: str = "bewegungsdaten",
        force_update: bool = False
) -> Dict:
    try:
        # Get MATLAB engine instance
        eng = MatlabEngine.get_instance()

        # Print current MATLAB path to debug
        print("MATLAB path:", eng.eval("path"))

        # Make sure your script directory is added
        matlab_path = "/home/gugafelds/robotervermessung-matlab-methods-applier/transform/"  # Update this path
        eng.addpath(matlab_path)

        # Verify the function exists
        exists = eng.eval(f"exist('transformBahn', 'file')")
        print(f"Function exists: {exists}")

        # Call the MATLAB function with parameters
        status, message = eng.transformBahn(
            str(bahn_id) if bahn_id else "",  # bahn_id (empty if uploading all)
            False,  # plots
            bahn_id is not None,  # upload_single
            bahn_id is None,  # upload_all
            False,  # transform_only
            str(schema),  # schema
            nargout=2
        )

        if not status:
            raise ValueError(message)

        return {
            "status": "success",
            "bahn_id": bahn_id if bahn_id else "all",
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logging.error(f"Error in transform_trajectory_matlab: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing {'bahn_id ' + bahn_id if bahn_id else 'all trajectories'}: {str(e)}"
        )

@router.post("/transform-trajectory/{bahn_id}")
async def transform_trajectory_endpoint(
        bahn_id: str,
        schema: str = "bewegungsdaten",
        force_update: bool = False,
        conn=Depends(get_db)
) -> Dict:
    """
    FastAPI endpoint to transform a trajectory using MATLAB engine.
    """
    return await transform_trajectory_matlab(conn, bahn_id, schema, force_update)


@router.post("/transform-all-trajectories")
async def transform_all_trajectories(
        schema: str = "bewegungsdaten",
        force_update: bool = False,
        conn=Depends(get_db)
) -> Dict:
    """
    Transform all trajectories that haven't been transformed yet.
    """
    try:
        # Get all bahn_ids that need transformation
        if force_update:
            bahn_ids = await conn.fetch(f"""
                SELECT bahn_id FROM robotervermessung.{schema}.bahn_info
                WHERE is_calibration = false
            """)
        else:
            bahn_ids = await conn.fetch(f"""
                SELECT bi.bahn_id 
                FROM robotervermessung.{schema}.bahn_info bi
                LEFT JOIN robotervermessung.{schema}.bahn_pose_trans bpt
                ON bi.bahn_id = bpt.bahn_id
                WHERE bi.is_calibration = false AND bpt.bahn_id IS NULL
            """)

        results = []
        for record in bahn_ids:
            try:
                result = await transform_trajectory_matlab(
                    conn,
                    record['bahn_id'],
                    schema,
                    force_update
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "status": "error",
                    "bahn_id": record['bahn_id'],
                    "error": str(e)
                })

        return {
            "status": "completed",
            "total_processed": len(bahn_ids),
            "successful": len([r for r in results if r['status'] == 'success']),
            "failed": len([r for r in results if r['status'] == 'error']),
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing trajectories: {str(e)}"
        )