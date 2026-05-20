import sys
import asyncio
from plot import plot

sys.path.append(
    r"\robotervermessung-webapp\backend"
)
from scripts.similarity_gen.similarity_search import search_similar
from app.database import get_db_pool, db

traj = [
    {"x_cmd": 1315.092, "y_cmd": -30.11032, "z_cmd": 1074.671},
    {"x_cmd": 1315, "y_cmd": -180, "z_cmd": 1075},
    {"x_cmd": 1465, "y_cmd": -180, "z_cmd": 925},
    {"x_cmd": 1465, "y_cmd": -30, "z_cmd": 925},
    {"x_cmd": 1315, "y_cmd": -30, "z_cmd": 1075},
]


async def main():
    pool = await get_db_pool()
    conn = await db.get_connection()

    try:
        result = await search_similar(
            str(traj),
            limit=5,
            stage2_active=True,
            metric="sidtw",
            pool=pool,
            conn=conn,
        )
        plot(result)
    finally:
        await db.release_connection(conn)
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
