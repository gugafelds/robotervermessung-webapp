import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db, get_db_pool
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

########################## BEWEGUNGSDATEN #########################################

@router.get("/traj_info")
async def get_traj_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        pool=Depends(get_db_pool)
):
    try:
        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # Count und Seite sind unabhängig voneinander, laufen also parallel
        # statt nacheinander auf derselben Connection.
        total_count, rows = await asyncio.gather(
            pool.fetchval("SELECT COUNT(*) FROM motion.traj_info"),
            pool.fetch(
                "SELECT * FROM motion.traj_info ORDER BY recording_date DESC LIMIT $1 OFFSET $2",
                page_size, offset,
            ),
        )

        traj_info_list = [dict(row) for row in rows]

        if not traj_info_list and page > 1:
            # Falls die angeforderte Seite keine Daten enthält, aber es gibt vorherige Seiten
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # Berechne die Gesamtanzahl der Seiten
        total_pages = (total_count + page_size - 1) // page_size

        # Pagination-Metadaten zum Ergebnis hinzufügen
        return {
            "traj_info": traj_info_list,
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


@router.get("/traj_search")
async def search_traj_info(
        query: str = Query(None, description="Suchbegriff für Freitext-Suche (Filename, ID, Datum)"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        setted_velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
        recording_date: str = Query(None, description="Datumsfilter"),
        sidtw_distance: float = Query(None, description="SIDTW Distance (±10% Toleranz)"),
        tag: str = Query(None, description="Tag-Filter"),
        pool=Depends(get_db_pool)
):
    try:
        # Basis-Query erstellen
        base_query = """
                        SELECT b.*, i.sidtw_average_distance 
                        FROM motion.traj_info b
                        LEFT JOIN evaluation.sidtw_info i ON b.traj_id = i.traj_id AND i.traj_id = i.seg_id
                        WHERE 1=1
                    """
        params = []
        param_index = 1

        # Filter hinzufügen basierend auf Parametern
        if query:
            # Da traj_id ein varchar ist, behandeln wir alle Suchen als Text
            search_conditions = []

            # traj_id (teilweise Übereinstimmung)
            search_conditions.append(f"b.traj_id ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Dateiname (teilweise Übereinstimmung)
            search_conditions.append(f"b.record_filename ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Datum
            search_conditions.append(f"b.recording_date ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Tag (teilweise Übereinstimmung)
            search_conditions.append(f"b.tag ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Alle Bedingungen mit OR verbinden
            base_query += f" AND ({' OR '.join(search_conditions)})"

        if points_events is not None:
            base_query += f" AND b.number_setpoints = ${param_index}"
            params.append(points_events)
            param_index += 1

        if weight is not None:
            tolerance = 0.5
            base_query += f" AND b.weight BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([weight - tolerance, weight + tolerance])
            param_index += 2

        if setted_velocity is not None:
            base_query += f" AND (b.setted_velocity = ${param_index})"
            params.append(setted_velocity)
            param_index += 1

        if recording_date is not None:
            if recording_date.isdigit() and len(recording_date) == 4:
                base_query += f" AND b.recording_date LIKE ${param_index}"
                params.append(f"{recording_date}-%")
                param_index += 1

            elif '.' in recording_date and ':' not in recording_date:
                try:
                    parts = recording_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        # Format: 2024-07-09
                        postgres_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        base_query += f" AND b.recording_date LIKE ${param_index}"
                        params.append(f"{postgres_date}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid date format: {recording_date}")

            elif '.' in recording_date and ':' in recording_date:
                try:
                    date_time_parts = recording_date.split(' ')
                    if len(date_time_parts) == 2:
                        date_part, time_part = date_time_parts
                        day, month, year = date_part.split('.')
                        hour, minute = time_part.split(':')

                        # Format: 2024-07-09 17:52
                        datetime_pattern = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}"
                        base_query += f" AND b.recording_date LIKE ${param_index}"
                        params.append(f"{datetime_pattern}%")
                        param_index += 1
                except Exception as e:
                    logger.warning(f"Invalid datetime format: {recording_date}")
        
        if tag is not None:
            base_query += f" AND b.tag = ${param_index}"
            params.append(tag)
            param_index += 1

        if sidtw_distance is not None:
            tolerance = sidtw_distance * 0.1  # 10% Toleranz
            base_query += f" AND i.sidtw_average_distance IS NOT NULL AND i.sidtw_average_distance BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([sidtw_distance - tolerance, sidtw_distance + tolerance])
            param_index += 2

        # Count und die paginierte Suche sind unabhängig, laufen also parallel.
        # Eigene Parameterlisten, da die Suche 2 zusätzliche (LIMIT/OFFSET) braucht.
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS filtered_data"
        search_query = base_query + f" ORDER BY b.recording_date DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        search_params = params + [page_size, (page - 1) * page_size]

        total_count, rows = await asyncio.gather(
            pool.fetchval(count_query, *params),
            pool.fetch(search_query, *search_params),
        )
        traj_info_list = [dict(row) for row in rows]

        # Keine Ergebnisse und Seite > 1
        if not traj_info_list and page > 1:
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "traj_info": traj_info_list,
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

@router.get("/traj_info/{traj_id}")
@cache(expire=24000)
async def get_traj_info_by_id(traj_id: str, conn = Depends(get_db)):
    try:
        traj_info = await conn.fetchrow(
            "SELECT * FROM motion.traj_info WHERE traj_id = $1",
            traj_id
        )
        if traj_info is None:
            raise HTTPException(status_code=404, detail="Bahn info not found")
        return dict(traj_info)
    except Exception as e:
        logger.error(f"Error fetching Bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/traj_pose_act/{traj_id}")
@cache(expire=2400)
async def get_traj_pose_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, x_act, y_act, z_act, qx_act, qy_act, qz_act, qw_act
           FROM motion.traj_pose_act WHERE traj_id = $1 ORDER BY timestamp ASC""",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_vel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_twist_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_vel_act FROM motion.traj_vel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_accel_act FROM motion.traj_accel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_accel_cmd FROM motion.traj_accel_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_position_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_position_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, x_cmd, y_cmd, z_cmd
           FROM motion.traj_position_cmd WHERE traj_id = $1 ORDER BY timestamp ASC""",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/seg_position_cmd/{segment_id}")
@cache(expire=2400)
async def get_segment_position_soll_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, x_cmd, y_cmd, z_cmd
           FROM motion.traj_position_cmd WHERE seg_id = $1 ORDER BY timestamp ASC""",
        segment_id
    )
    return [dict(row) for row in rows]


@router.get("/traj_orientation_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_orientation_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, qx_cmd, qy_cmd, qz_cmd, qw_cmd
           FROM motion.traj_orientation_cmd WHERE traj_id = $1 ORDER BY timestamp ASC""",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_vel_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_twist_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT timestamp, tcp_vel_cmd FROM motion.traj_vel_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_joint_states/{traj_id}")
@cache(expire=2400)
async def get_traj_joint_states_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6
           FROM motion.traj_joint_states WHERE traj_id = $1 ORDER BY timestamp ASC""",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_setpoints/{traj_id}")
@cache(expire=2400)
async def get_traj_events_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT timestamp, x_reached, y_reached, z_reached,
                  qx_reached, qy_reached, qz_reached, qw_reached,
                  x_support, y_support, z_support,
                  qx_support, qy_support, qz_support, qw_support,
                  vel_set, stop_point, timestamp_support
           FROM motion.traj_setpoints WHERE traj_id = $1 ORDER BY timestamp ASC""",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_metadata/{traj_id}")
@cache(expire=2400)
async def get_traj_metadata_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        """SELECT seg_id, traj_id, movement_type, duration, weight, length,
                  min_vel, max_vel, mean_vel, median_vel, std_vel,
                  min_accel, max_accel, mean_accel, median_accel, std_accel,
                  position_x, position_y, position_z
           FROM motion.traj_metadata WHERE traj_id = $1 ORDER BY seg_id ASC""",
        traj_id
    )
    return [dict(row) for row in rows]



@router.get("/traj_sim/{traj_id}")
@cache(expire=2400)
async def get_traj_sim_by_id(traj_id: str, conn = Depends(get_db)):
    """Simulated copy of a trajectory. Sim timestamps are seconds since traj start;
    shifted to the real (ns) time base so the frontend plots treat them like *_cmd data."""
    t0 = int(await conn.fetchval(
        "SELECT MIN(timestamp::numeric) FROM motion.traj_position_cmd WHERE traj_id = $1",
        traj_id
    ) or 0)

    async def fetch(cols: str, table: str):
        rows = await conn.fetch(
            f"SELECT timestamp, {cols} FROM simulation.{table} WHERE traj_id = $1 ORDER BY timestamp ASC",
            traj_id
        )
        return [dict(r) for r in rows]

    def to_ns(sec: float) -> str:
        return str(t0 + round(sec * 1e9))

    def series(rows):
        return [{**r, "timestamp": to_ns(r["timestamp"])} for r in rows]

    position = await fetch("seg_id, x_cmd, y_cmd, z_cmd", "sim_position")

    # Sim setpoints have no timestamps: reached = end of its segment,
    # support = nearest sim sample. ponytail: nearest-sample is approximate (~1 sample raster)
    setpoints = []
    for sp in await conn.fetch(
        """SELECT seg_id, x_reached, y_reached, z_reached, qx_reached, qy_reached, qz_reached, qw_reached,
                  x_support, y_support, z_support, qx_support, qy_support, qz_support, qw_support,
                  vel_set, stop_point
           FROM simulation.sim_setpoints WHERE traj_id = $1""",
        traj_id
    ):
        pts = [p for p in position if p["seg_id"] == sp["seg_id"]]
        if not pts:
            continue
        # linear segments have no support point (NULL) -> keep reached time, plot skips NULL y
        near = pts[-1] if sp["x_support"] is None else min(
            pts, key=lambda p: (p["x_cmd"] - sp["x_support"]) ** 2
            + (p["y_cmd"] - sp["y_support"]) ** 2 + (p["z_cmd"] - sp["z_support"]) ** 2)
        setpoints.append({**sp, "timestamp": to_ns(pts[-1]["timestamp"]),
                          "timestamp_support": to_ns(near["timestamp"])})
    setpoints.sort(key=lambda r: int(r["timestamp"]))

    return {
        "position": series(position),
        "orientation": series(await fetch("qx_cmd, qy_cmd, qz_cmd, qw_cmd", "sim_orientation")),
        "velocity": series(await fetch("tcp_vel_sim AS tcp_vel_cmd", "sim_velocity")),
        "joint_states": series(await fetch("joint_1, joint_2, joint_3, joint_4, joint_5, joint_6", "sim_joint_states")),
        "setpoints": setpoints,
        "metadata": [dict(r) for r in await conn.fetch(
            """SELECT seg_id, traj_id, movement_type, duration, weight, length,
                      min_vel, max_vel, mean_vel, median_vel, std_vel,
                      min_accel, max_accel, mean_accel, median_accel, std_accel,
                      position_x, position_y, position_z
               FROM simulation.sim_metadata WHERE traj_id = $1 ORDER BY seg_id ASC""",
            traj_id
        )],
    }
