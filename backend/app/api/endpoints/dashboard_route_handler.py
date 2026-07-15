from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

METRIC_MAP = {
    'sidtw': ('evaluation.sidtw_info', 'sidtw_average_distance'),
    'ed':    ('evaluation.ed_info',    'ed_average_distance'),
    'qdtw':  ('evaluation.qdtw_info',  'qdtw_average_distance'),
    'gd':    ('evaluation.gd_info',    'gd_average_distance'),
}

def _tf(tags, alias="bi", p=1):
    return (f"AND {alias}.tag = ANY(${p}::text[])", [tags]) if tags else ("", [])


@router.get("/tags")
@cache(expire=3600)
async def get_available_tags(conn=Depends(get_db)):
    rows = await conn.fetch(
        "SELECT DISTINCT tag FROM motion.traj_info WHERE tag IS NOT NULL ORDER BY tag"
    )
    return {"tags": [r["tag"] for r in rows]}


@router.get("/data")
@cache(expire=1800)
async def get_dashboard_data(tag: list[str] = Query(None), conn=Depends(get_db)):
    try:
        tc, tp = _tf(tag or None)

        segments_count = await conn.fetchval(
            f"SELECT SUM(number_setpoints) FROM motion.traj_info bi WHERE source_data_act = 'leica_at960' {tc}", *tp)
        trajs_count = await conn.fetchval(
            f"SELECT COUNT(DISTINCT traj_id) FROM motion.traj_info bi WHERE source_data_act = 'leica_at960' {tc}", *tp)
        median_sidtw = await conn.fetchval(f"""
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sidtw_average_distance)
            FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
            WHERE i.traj_id = i.seg_id AND i.sidtw_average_distance IS NOT NULL
            AND bi.source_data_act = 'leica_at960' {tc}""", *tp)
        mean_sidtw = await conn.fetchval(f"""
            SELECT AVG(sidtw_average_distance)
            FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
            WHERE i.traj_id = i.seg_id AND i.sidtw_average_distance IS NOT NULL
            AND bi.source_data_act = 'leica_at960' {tc}""", *tp)

        stats = {}

        vrows = await conn.fetch(f"""
            SELECT CASE WHEN max_vel < 500 THEN 1 WHEN max_vel < 1000 THEN 2
                        WHEN max_vel < 1500 THEN 3 WHEN max_vel < 2000 THEN 4
                        WHEN max_vel < 2500 THEN 5 WHEN max_vel < 3000 THEN 6 ELSE 7 END AS bucket, COUNT(*)
            FROM motion.traj_metadata m INNER JOIN motion.traj_info bi ON m.traj_id = bi.traj_id
            WHERE m.traj_id != m.seg_id AND m.max_vel IS NOT NULL {tc}
            GROUP BY bucket ORDER BY bucket""", *tp)
        stats["velocityDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in vrows],
            "meta": {"useRanges": True, "min": 0, "max": 3500, "numBuckets": 7, "unit": "mm/s", "label": "Velocity"}
        }

        wrows = await conn.fetch(f"""
            SELECT weight AS bucket, COUNT(*) FROM motion.traj_info bi
            WHERE source_data_act = 'leica_at960' {tc} GROUP BY bucket ORDER BY bucket""", *tp)
        stats["weightDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wrows],
            "meta": {"useRanges": False, "unit": "kg", "label": "Payload"}
        }

        wprows = await conn.fetch(f"""
            SELECT number_setpoints AS bucket, COUNT(*) FROM motion.traj_info bi
            WHERE source_data_act = 'leica_at960' {tc} GROUP BY bucket ORDER BY bucket""", *tp)
        stats["waypointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wprows],
            "meta": {"useRanges": False, "unit": "-", "label": "Setpoint"}
        }

        sidtw_max = await conn.fetchval(f"""
            SELECT MAX(i.sidtw_average_distance) FROM evaluation.sidtw_info i
            INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
            WHERE i.traj_id != i.seg_id AND i.sidtw_average_distance IS NOT NULL {tc}""", *tp)

        if tp:
            srows = await conn.fetch("""
                SELECT width_bucket(i.sidtw_average_distance, 0, $1::float, 11) AS bucket, COUNT(*)
                FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
                WHERE i.traj_id != i.seg_id AND i.sidtw_average_distance IS NOT NULL
                AND bi.tag = ANY($2::text[])
                GROUP BY bucket ORDER BY bucket""", float(sidtw_max or 2.0), tp[0])
        else:
            srows = await conn.fetch("""
                SELECT width_bucket(i.sidtw_average_distance, 0, $1::float, 11) AS bucket, COUNT(*)
                FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
                WHERE i.traj_id != i.seg_id AND i.sidtw_average_distance IS NOT NULL
                GROUP BY bucket ORDER BY bucket""", float(sidtw_max or 2.0))
        stats["performanceSIDTWDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in srows],
            "meta": {"useRanges": True, "min": 0, "max": float(sidtw_max or 2.0), "numBuckets": 11, "unit": "mm", "label": "Accuracy"}
        }

        sprows = await conn.fetch(f"""
            SELECT sp.stop_point AS bucket, COUNT(*) FROM motion.traj_setpoints sp
            INNER JOIN motion.traj_info bi ON sp.traj_id = bi.traj_id
            WHERE sp.stop_point IS NOT NULL {tc}
            GROUP BY bucket ORDER BY bucket""", *tp)
        stats["stopPointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in sprows],
            "meta": {"useRanges": False, "unit": "%", "label": "Stop point"}
        }

        return {
            "segmentsCount": segments_count,
            "trajsCount": trajs_count,
            "medianSIDTW": median_sidtw,
            "meanSIDTW": mean_sidtw,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performers")
@cache(expire=1800)
async def get_performers(
    metric: str = Query("sidtw"),
    with_trajectory: bool = Query(False),
    tag: list[str] = Query(None),
    conn=Depends(get_db)
):
    """Returns top performers. With tags: server-side filter, top 5. Without: top 100 for client-side use."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]
    tc, tp = _tf(tag or None)
    limit = 10 if with_trajectory else (5 if tag else 100)

    base = f"""
        SELECT i.traj_id, i.seg_id, i.{col} as metric_value,
               bi.weight, bi.number_setpoints as waypoints, bi.stop_point,
               m.max_vel as max_velocity, m.max_accel as max_acceleration,
               bi.tag
        FROM {table} i
        INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
        LEFT JOIN motion.traj_metadata m ON i.seg_id = m.seg_id
        WHERE i.traj_id = i.seg_id AND i.{col} IS NOT NULL
          AND bi.source_data_act = 'leica_at960' {tc}
        ORDER BY i.{col} {{order}} LIMIT {limit}"""

    best_raw = await conn.fetch(base.format(order="ASC"), *tp)
    worst_raw = await conn.fetch(base.format(order="DESC"), *tp)

    traj_map: dict = {}
    if with_trajectory:
        all_ids = list({r["traj_id"] for r in best_raw} | {r["traj_id"] for r in worst_raw})
        traj_points = await conn.fetch(
            "SELECT traj_id, x_cmd, y_cmd, z_cmd FROM motion.traj_position_cmd "
            "WHERE traj_id = ANY($1::text[]) ORDER BY traj_id, timestamp", all_ids)
        for p in traj_points:
            traj_map.setdefault(p["traj_id"], []).append({"x": p["x_cmd"], "y": p["y_cmd"], "z": p["z_cmd"]})

    def build(rows):
        return [{
            "traj_id": r["traj_id"], "seg_id": r["seg_id"],
            "metric_value": float(r["metric_value"]), "weight": r["weight"],
            "waypoints": r["waypoints"], "stop_point": r["stop_point"],
            "max_velocity": r["max_velocity"], "max_acceleration": r["max_acceleration"],
            "tag": r["tag"],
            **({"trajectory": traj_map.get(r["traj_id"], [])} if with_trajectory else {}),
        } for r in rows]

    return {"bestPerformers": build(best_raw), "worstPerformers": build(worst_raw)}


@router.get("/timeline")
@cache(expire=3600)
async def get_dashboard_timeline(metric: str = Query("sidtw"), conn=Depends(get_db)):
    """Returns per (date, tag) rows. Client aggregates for selected tags."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]

    rows = await conn.fetch(f"""
        SELECT DATE(bi.recording_date) as date,
               bi.tag as tag,
               AVG(info.{col}) as avg_val,
               MIN(info.{col}) as min_val,
               MAX(info.{col}) as max_val,
               COUNT(*) as count
        FROM motion.traj_info bi
        INNER JOIN {table} info ON bi.traj_id = info.traj_id AND bi.traj_id = info.seg_id
        WHERE bi.recording_date IS NOT NULL AND info.{col} IS NOT NULL
        GROUP BY DATE(bi.recording_date), bi.tag
        ORDER BY date ASC, bi.tag""")

    return {"timeline": [{
        "date": str(r["date"]), "tag": r["tag"],  # tag may be None for untagged trajectories
        "avg_val": float(r["avg_val"]), "min_val": float(r["min_val"]),
        "max_val": float(r["max_val"]), "count": int(r["count"]),
    } for r in rows]}


@router.get("/influence")
@cache(expire=3600)
async def get_dashboard_influence(metric: str = Query("sidtw"), conn=Depends(get_db)):
    """Returns 5000 samples with tag field. Client filters by tag."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]

    rows = await conn.fetch(f"""
        WITH sampled AS (
            SELECT info.{col} as metric_value,
                   bm.max_vel as velocity, bm.max_accel as acceleration,
                   bi.weight as weight, bx.stop_point as stop_point,
                   bi.tag as tag
            FROM {table} info
            INNER JOIN motion.traj_metadata bm ON info.seg_id = bm.seg_id
            INNER JOIN motion.traj_info bi ON info.traj_id = bi.traj_id
            INNER JOIN motion.traj_setpoints bx ON info.seg_id = bx.seg_id
            WHERE info.{col} IS NOT NULL AND bm.max_vel IS NOT NULL
              AND bm.max_accel IS NOT NULL AND bx.stop_point IS NOT NULL
              AND bi.tag IS NOT NULL
            ORDER BY RANDOM() LIMIT 5000
        ) SELECT * FROM sampled""")

    return {"data": [{
        "metric_value": float(r["metric_value"]), "velocity": float(r["velocity"]),
        "acceleration": float(r["acceleration"]), "weight": float(r["weight"]),
        "stop_point": float(r["stop_point"]), "tag": r["tag"],
    } for r in rows]}


@router.get("/tag-info")
@cache(expire=3600)
async def get_tag_info(tag: list[str] = Query(None), conn=Depends(get_db)):
    if not tag:
        rows = await conn.fetch("SELECT * FROM motion.tag_info ORDER BY tag")
    else:
        rows = await conn.fetch("SELECT * FROM motion.tag_info WHERE tag = ANY($1::text[]) ORDER BY tag", tag)
    return {"tags": [{
        "tag": r["tag"], "robot": r["robot"], "type": r["type"], "plane": r["plane"],
        "vel_min": float(r["vel_min"]) if r["vel_min"] is not None else None,
        "vel_max": float(r["vel_max"]) if r["vel_max"] is not None else None,
        "stop_point": float(r["stop_point"]) if r["stop_point"] is not None else None,
        "reorientation_xy": r["reorientation_xy"], "reorientation_z": r["reorientation_z"],
        "min_distance": r["min_distance"],
        "ws_x_min": float(r["ws_x_min"]) if r["ws_x_min"] is not None else None,
        "ws_x_max": float(r["ws_x_max"]) if r["ws_x_max"] is not None else None,
        "ws_y_min": float(r["ws_y_min"]) if r["ws_y_min"] is not None else None,
        "ws_y_max": float(r["ws_y_max"]) if r["ws_y_max"] is not None else None,
        "ws_z_min": float(r["ws_z_min"]) if r["ws_z_min"] is not None else None,
        "ws_z_max": float(r["ws_z_max"]) if r["ws_z_max"] is not None else None,
        "comment": r["comment"],
    } for r in rows]}


@router.get("/workarea")
@cache(expire=3600)
async def get_dashboard_workarea(conn=Depends(get_db)):
    """Returns sampled workarea points with tag field. Client filters by tag."""
    rows = await conn.fetch("""
        WITH numbered AS (
            SELECT be.x_reached, be.y_reached, be.z_reached,
                   s.sidtw_average_distance, bi.tag,
                   ROW_NUMBER() OVER (PARTITION BY be.traj_id ORDER BY be.timestamp) as rn
            FROM motion.traj_setpoints be
            JOIN evaluation.sidtw_info s ON be.traj_id = s.traj_id
            JOIN motion.traj_info bi ON be.traj_id = bi.traj_id
            WHERE s.traj_id <> s.seg_id AND s.sidtw_average_distance IS NOT NULL
              AND be.x_reached IS NOT NULL AND be.y_reached IS NOT NULL
              AND be.z_reached IS NOT NULL AND bi.tag IS NOT NULL
        )
        SELECT x_reached, y_reached, z_reached, sidtw_average_distance, tag
        FROM numbered WHERE rn % 10 = 0 LIMIT 30000""")

    return {"points": [{
        "x": r["x_reached"], "y": r["y_reached"], "z": r["z_reached"],
        "sidtw": r["sidtw_average_distance"], "tag": r["tag"],
    } for r in rows]}
