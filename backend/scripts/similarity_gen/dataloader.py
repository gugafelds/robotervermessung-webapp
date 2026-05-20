import json
import sys

sys.path.append(
    r"\robotervermessung-webapp\backend\app"
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
                SELECT x_cmd, y_cmd, z_cmd FROM motion.traj_position_cmd WHERE traj_id = '1761929739'
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
                "/csvs/similarity_data.csv",
                "w",
                newline="",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "x_cmd",
                        "y_cmd",
                        "z_cmd"
                    ]
                )

                for row in data:
                    writer.writerow(
                        [
                            row["x_cmd"],
                            row["y_cmd"],
                            row["z_cmd"]
                        ]
                    )

            print(f"CSV gespeichert ({len(data)} Punkte)")

        except Exception as e:
            logger.error(f"Fehler im Script: {e}")

        break


if __name__ == "__main__":
    asyncio.run(main())
