import json
import sys

sys.path.append(
    r"c:\Users\muell\Desktop\Arbeit\Robotervermessung\robotervermessung-webapp\backend\scripts"
)
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
import logging
from fastapi_cache.decorator import cache
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/data")
async def get_setpoint_data(conn=Depends(get_db)):
    try:
        query = """
                SELECT 
                    t.x_cmd AS x_start,
                    t.y_cmd AS y_start,
                    t.z_cmd AS z_start,
                    s.x_reached AS x_end,
                    s.y_reached AS y_end,
                    s.z_reached AS z_end,
                    m.movement_type AS movement
                FROM motion.traj_setpoints s

                JOIN (
                    SELECT DISTINCT ON (seg_id)
                        seg_id,
                        x_cmd,
                        y_cmd,
                        z_cmd
                    FROM motion.traj_position_cmd
                    ORDER BY seg_id
                ) t
                ON s.seg_id = t.seg_id

                JOIN (
                    SELECT DISTINCT ON (seg_id)
                        seg_id,
                        movement_type
                    FROM motion.traj_metadata
                    WHERE movement_type IN ('linear', 'circular')
                    ORDER BY seg_id
                ) m
                ON s.seg_id = m.seg_id;
        """

        result = await conn.fetch(query)

        return result

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


import asyncio


async def main():
    async for conn in get_db():
        try:
            data = await get_setpoint_data(conn)
            with open(
                "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/newdata2.csv",
                "w",
                newline="",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "x_start",
                        "y_start",
                        "z_start",
                        "x_end",
                        "y_end",
                        "z_end",
                        "movement",
                    ]
                )

                for row in data:
                    writer.writerow(
                        [
                            row["x_start"],
                            row["y_start"],
                            row["z_start"],
                            row["x_end"],
                            row["y_end"],
                            row["z_end"],
                            row["movement"],
                        ]
                    )

            print(f"CSV gespeichert ({len(data)} Punkte)")

        except Exception as e:
            logger.error(f"Fehler im Script: {e}")

        break


if __name__ == "__main__":
    asyncio.run(main())
