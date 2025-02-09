from fastapi import APIRouter, HTTPException, Depends
import matlab.engine

router = APIRouter()
matlab_eng = matlab.engine.start_matlab()
matlab_eng.addpath('path/to/matlab/functions')

@router.post("/transform-trajectory/{bahn_id}")
async def transform_trajectory(bahn_id: str, conn = Depends(get_db)):
    try:
        # Fetch data
        data_ist = await conn.fetch("""
            SELECT * FROM robotervermessung.bewegungsdaten.bahn_pose_ist 
            WHERE bahn_id = $1 ORDER BY timestamp
        """, bahn_id)

        data_orientation_soll = await conn.fetch("""
            SELECT * FROM robotervermessung.bewegungsdaten.bahn_orientation_soll 
            WHERE bahn_id = $1 ORDER BY timestamp
        """, bahn_id)

        # Prepare MATLAB data
        q_ist = matlab_eng.double([[r['qw'], r['qx'], r['qy'], r['qz']] for r in data_ist])
        q_soll = matlab_eng.double([[r['qw'], r['qx'], r['qy'], r['qz']] for r in data_orientation_soll])
        ist_times = matlab_eng.double([float(r['timestamp']) for r in data_ist])
        soll_times = matlab_eng.double([float(r['timestamp']) for r in data_orientation_soll])

        # Transform quaternions
        q_transformed, error_metrics = matlab_eng.transformQuaternionsWithCoordinates(
            q_ist, q_soll, ist_times, soll_times, 'ZYX', 'ZYX', False, nargout=2
        )

        # Store results
        await conn.executemany("""
            INSERT INTO robotervermessung.bewegungsdaten.bahn_pose_trans
            (bahn_id, timestamp, x_trans, y_trans, z_trans, qw_trans, qx_trans, qy_trans, qz_trans)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, [(
            bahn_id,
            row['timestamp'],
            row['x'], row['y'], row['z'],
            q_transformed[i][0], q_transformed[i][1], q_transformed[i][2], q_transformed[i][3]
        ) for i, row in enumerate(data_ist)])

        return {"message": f"Successfully transformed trajectory for bahn_id {bahn_id}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))