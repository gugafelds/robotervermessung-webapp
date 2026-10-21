import asyncio
import json
import math
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db, get_db_pool
import logging
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/refresh")
async def refresh_dashboard_cache():
    """Clears all cached dashboard responses so the next request recomputes
    fresh data. Called by the frontend's refresh button before re-fetching —
    without this, a refresh click hits the same cache key as the previous
    load and just gets the stale cached response back."""
    await FastAPICache.clear(namespace="dashboard")
    return {"status": "cleared"}

METRIC_MAP = {
    'sidtw': ('evaluation.sidtw_info', 'sidtw_average_distance'),
    'ed':    ('evaluation.ed_info',    'ed_average_distance'),
    'qdtw':  ('evaluation.qdtw_info',  'qdtw_average_distance'),
    'gd':    ('evaluation.gd_info',    'gd_average_distance'),
}

def _tf(tags, alias="bi", p=1, robot=None):
    """' AND ...' fragment + params for the tag and robot filters, parameters numbered from $p."""
    conds, params = [], []
    if tags:
        conds.append(f"{alias}.tag = ANY(${p + len(params)}::text[])")
        params.append(tags)
    if robot:
        conds.append(f"{alias}.robot_model = ${p + len(params)}")
        params.append(robot)
    return (" AND " + " AND ".join(conds) if conds else ""), params


@router.get("/robots")
@cache(expire=3600, namespace="dashboard")
async def get_robots(conn=Depends(get_db)):
    """Robots from motion.robot_info (filter options)."""
    rows = await conn.fetch("SELECT robot_model, description FROM motion.robot_info ORDER BY robot_model")
    return {"robots": [{"robot_model": r["robot_model"], "description": r["description"]} for r in rows]}


@router.get("/tags")
@cache(expire=3600, namespace="dashboard")
async def get_available_tags(robot: str = Query(None), conn=Depends(get_db)):
    """Tags (of the robot, if given) and the robots each tag contains."""
    tc, tp = _tf(None, robot=robot)
    rows = await conn.fetch(f"""
        SELECT tag, array_agg(DISTINCT robot_model) AS robots FROM motion.traj_info bi
        WHERE tag IS NOT NULL {tc} GROUP BY tag ORDER BY tag""", *tp)
    return {"tags": [r["tag"] for r in rows],
            "robots": {r["tag"]: [x for x in r["robots"] if x] for r in rows}}


@router.get("/data")
@cache(expire=1800, namespace="dashboard")
async def get_dashboard_data(tag: list[str] = Query(None), robot: str = Query(None), pool=Depends(get_db_pool)):
    try:
        tc, tp = _tf(tag or None, robot=robot)

        # All 10 queries below are independent of each other (none reads another's
        # result), so they run concurrently over separate pooled connections
        # instead of one-by-one on a single connection.
        (
            segments_count, trajs_count, median_sidtw, mean_sidtw,
            vrows, wrows, wprows, sidtw_p99, sprows, mtrows,
        ) = await asyncio.gather(
            pool.fetchval(
                f"SELECT SUM(number_setpoints) FROM motion.traj_info bi WHERE source_data_act = 'leica_at960' {tc}", *tp),
            pool.fetchval(
                f"SELECT COUNT(DISTINCT traj_id) FROM motion.traj_info bi WHERE source_data_act = 'leica_at960' {tc}", *tp),
            pool.fetchval(f"""
                SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sidtw_average_distance)
                FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
                WHERE i.traj_id = i.seg_id AND i.sidtw_average_distance IS NOT NULL
                AND bi.source_data_act = 'leica_at960' {tc}""", *tp),
            pool.fetchval(f"""
                SELECT AVG(sidtw_average_distance)
                FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
                WHERE i.traj_id = i.seg_id AND i.sidtw_average_distance IS NOT NULL
                AND bi.source_data_act = 'leica_at960' {tc}""", *tp),
            pool.fetch(f"""
                SELECT LEAST(FLOOR(sp.vel_set / 500)::int, 6) + 1 AS bucket, COUNT(*)
                FROM motion.traj_setpoints sp INNER JOIN motion.traj_info bi ON sp.traj_id = bi.traj_id
                WHERE sp.vel_set IS NOT NULL {tc}
                GROUP BY bucket ORDER BY bucket""", *tp),
            pool.fetch(f"""
                SELECT weight AS bucket, COUNT(*) FROM motion.traj_info bi
                WHERE source_data_act = 'leica_at960' {tc} GROUP BY bucket ORDER BY bucket""", *tp),
            pool.fetch(f"""
                SELECT number_setpoints AS bucket, COUNT(*) FROM motion.traj_info bi
                WHERE source_data_act = 'leica_at960' {tc} GROUP BY bucket ORDER BY bucket""", *tp),
            pool.fetchval(f"""
                SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY i.sidtw_average_distance)
                FROM evaluation.sidtw_info i
                INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
                WHERE i.traj_id != i.seg_id AND i.sidtw_average_distance IS NOT NULL {tc}""", *tp),
            pool.fetch(f"""
                SELECT sp.stop_point AS bucket, COUNT(*) FROM motion.traj_setpoints sp
                INNER JOIN motion.traj_info bi ON sp.traj_id = bi.traj_id
                WHERE sp.stop_point IS NOT NULL {tc}
                GROUP BY bucket ORDER BY bucket""", *tp),
            pool.fetch(f"""
                SELECT m.movement_type AS bucket, COUNT(*) FROM motion.traj_metadata m
                INNER JOIN motion.traj_info bi ON m.traj_id = bi.traj_id
                WHERE m.traj_id != m.seg_id AND m.movement_type IN ('linear', 'circular') {tc}
                GROUP BY bucket ORDER BY bucket""", *tp),
        )

        stats = {
            "velocityDistribution": {
                "data": [{"bucket": r["bucket"], "count": r["count"]} for r in vrows],
                "meta": {"useRanges": True, "min": 0, "max": 3500, "numBuckets": 7, "decimals": 0,
                         "unit": "mm/s", "label": "Programmed velocity", "countLabel": "Segments"}
            },
            "weightDistribution": {
                "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wrows],
                "meta": {"useRanges": False, "unit": "kg", "label": "Payload", "countLabel": "Trajectories"}
            },
            "waypointDistribution": {
                "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wprows],
                "meta": {"useRanges": False, "unit": "-", "label": "Setpoints per trajectory",
                         "countLabel": "Trajectories"}
            },
            "stopPointDistribution": {
                "data": [{"bucket": r["bucket"], "count": r["count"]} for r in sprows],
                "meta": {"useRanges": False, "unit": "%", "label": "Stop point", "countLabel": "Segments"}
            },
            "segmentTypeDistribution": {
                "data": [{"bucket": r["bucket"], "count": r["count"]} for r in mtrows],
                "meta": {"useRanges": False, "unit": "-", "label": "Type", "countLabel": "Segments"}
            },
        }

        # Classes of 0.1 mm (0.05 mm for small errors) up to the 99th percentile, one class ">= edge" above.
        # Depends on sidtw_p99, so it runs after the batch above.
        p99 = float(sidtw_p99 or 1.0)
        step = 0.1 if p99 > 0.6 else 0.05
        n_bins = max(1, math.ceil(p99 / step - 1e-9))
        edge = round(n_bins * step, 2)
        tc2, tp2 = _tf(tag or None, p=2, robot=robot)
        srows = await pool.fetch(f"""
            SELECT LEAST(width_bucket(i.sidtw_average_distance, 0, $1::float, {n_bins}), {n_bins + 1}) AS bucket,
                   COUNT(*)
            FROM evaluation.sidtw_info i INNER JOIN motion.traj_info bi ON i.traj_id = bi.traj_id
            WHERE i.traj_id != i.seg_id AND i.sidtw_average_distance IS NOT NULL {tc2}
            GROUP BY bucket ORDER BY bucket""", edge, *tp2)
        stats["performanceSIDTWDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in srows],
            "meta": {"useRanges": True, "min": 0, "max": edge, "numBuckets": n_bins, "decimals": 2,
                     "overflow": True, "unit": "mm", "label": "Accuracy (SIDTW)", "countLabel": "Segments"}
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
@cache(expire=1800, namespace="dashboard")
async def get_performers(
    metric: str = Query("sidtw"),
    with_trajectory: bool = Query(False),
    tag: list[str] = Query(None),
    robot: str = Query(None),
    conn=Depends(get_db)
):
    """Returns top performers. With tags: server-side filter, top 5. Without: top 100 for client-side use."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]
    tc, tp = _tf(tag or None, robot=robot)
    limit = 10 if with_trajectory else (5 if tag else 100)

    base = f"""
        SELECT i.traj_id, i.seg_id, i.{col} as metric_value,
               bi.weight, bi.number_setpoints as waypoints,
               (SELECT string_agg(DISTINCT s.stop_point::int::text, '/') FROM motion.traj_setpoints s
                WHERE s.traj_id = bi.traj_id) AS stop_point,
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
@cache(expire=3600, namespace="dashboard")
async def get_dashboard_timeline(metric: str = Query("sidtw"), conn=Depends(get_db)):
    """Returns per (hour, tag, robot) rows ('YYYY-MM-DD HH:00'). Client aggregates for the selected tags / robot."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]

    rows = await conn.fetch(f"""
        SELECT to_char(date_trunc('hour', bi.recording_date::timestamp), 'YYYY-MM-DD HH24:00') as date,
               bi.tag as tag,
               bi.robot_model as robot,
               AVG(info.{col}) as avg_val,
               MIN(info.{col}) as min_val,
               MAX(info.{col}) as max_val,
               COUNT(*) as count
        FROM motion.traj_info bi
        INNER JOIN {table} info ON bi.traj_id = info.traj_id AND bi.traj_id = info.seg_id
        WHERE bi.recording_date IS NOT NULL AND info.{col} IS NOT NULL
        GROUP BY 1, bi.tag, bi.robot_model
        ORDER BY date ASC, bi.tag""")

    return {"timeline": [{
        "date": str(r["date"]), "tag": r["tag"], "robot": r["robot"],  # tag may be None for untagged trajectories
        "avg_val": float(r["avg_val"]), "min_val": float(r["min_val"]),
        "max_val": float(r["max_val"]), "count": int(r["count"]),
    } for r in rows]}


@router.get("/influence")
@cache(expire=3600, namespace="dashboard")
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
            ORDER BY RANDOM() LIMIT 2000
        ) SELECT * FROM sampled""")

    return {"data": [{
        "metric_value": float(r["metric_value"]), "velocity": float(r["velocity"]),
        "acceleration": float(r["acceleration"]), "weight": float(r["weight"]),
        "stop_point": float(r["stop_point"]), "tag": r["tag"],
    } for r in rows]}


@router.get("/tag-info")
@cache(expire=3600, namespace="dashboard")
async def get_tag_info(tag: list[str] = Query(None), robot: str = Query(None), conn=Depends(get_db)):
    """One row per (tag, robot) -- the reference tags exist for every robot, with its own workspace."""
    rows = await conn.fetch(
        "SELECT * FROM motion.tag_info WHERE ($1::text[] IS NULL OR tag = ANY($1::text[])) "
        "AND ($2::text IS NULL OR robot = $2) ORDER BY tag, robot", tag or None, robot)
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


# From this many trajectories on, the work area shows a fixed 1 % sample of the setpoints (the plot stays fast).
WORKAREA_SAMPLE_FROM = 2000


@router.get("/workarea/data")
@cache(expire=1800, namespace="dashboard")
async def get_workarea_data(tag: list[str] = Query(None), robot: str = Query(None), conn=Depends(get_db)):
    """
    Setpoints of the selected robot (and tags), coloured by their segment's SIDTW. With >= WORKAREA_SAMPLE_FROM
    trajectories a fixed 1 % sample (abs(hashtext(seg_id)) % 100 = 0, the same points every time).
    With tags: workspace bounds from tag_info (rows of this robot).
    """
    tc, tp = _tf(tag or None, robot=robot)
    n_traj = await conn.fetchval(f"SELECT COUNT(*) FROM motion.traj_info bi WHERE TRUE {tc}", *tp)
    sampled = n_traj >= WORKAREA_SAMPLE_FROM
    rows = await conn.fetch(f"""
        SELECT be.x_reached, be.y_reached, be.z_reached, s.sidtw_average_distance, bi.tag
        FROM motion.traj_setpoints be
        JOIN evaluation.sidtw_info s ON s.seg_id = be.seg_id
        JOIN motion.traj_info bi ON be.traj_id = bi.traj_id
        WHERE be.x_reached IS NOT NULL AND be.y_reached IS NOT NULL AND be.z_reached IS NOT NULL
          AND s.sidtw_average_distance IS NOT NULL {tc}
          {"AND abs(hashtext(be.seg_id)) % 100 = 0" if sampled else ""}
    """, *tp)

    bounds = None
    if tag:
        tag_rows = await conn.fetch(
            "SELECT * FROM motion.tag_info WHERE tag = ANY($1::text[]) AND ($2::text IS NULL OR robot = $2) "
            "ORDER BY tag", tag, robot
        )
        if tag_rows:
            xs = [r["ws_x_min"] for r in tag_rows if r["ws_x_min"] is not None]
            xe = [r["ws_x_max"] for r in tag_rows if r["ws_x_max"] is not None]
            ys = [r["ws_y_min"] for r in tag_rows if r["ws_y_min"] is not None]
            ye = [r["ws_y_max"] for r in tag_rows if r["ws_y_max"] is not None]
            zs = [r["ws_z_min"] for r in tag_rows if r["ws_z_min"] is not None]
            ze = [r["ws_z_max"] for r in tag_rows if r["ws_z_max"] is not None]
            if xs and xe and ys and ye and zs and ze:
                bounds = {
                    "x_min": min(xs), "x_max": max(xe),
                    "y_min": min(ys), "y_max": max(ye),
                    "z_min": min(zs), "z_max": max(ze),
                }

    return {
        "points": [{"x": r["x_reached"], "y": r["y_reached"], "z": r["z_reached"],
                    "sidtw": r["sidtw_average_distance"], "tag": r["tag"]} for r in rows],
        "bounds": bounds,
        "trajectories": n_traj,
        "sampled": sampled,
    }

@router.get("/influence/binned")
@cache(expire=3600, namespace="dashboard")
async def get_influence_binned(
    metric: str = Query("sidtw"),
    tag: list[str] = Query(None),
    robot: str = Query(None),
    conn=Depends(get_db),
):
    """Returns box-plot bins per parameter, pre-computed in DB."""
    if metric not in METRIC_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    table, col = METRIC_MAP[metric]
    tc, tp = _tf(tag or None, alias="bi", p=1, robot=robot)
    sample = "ORDER BY RANDOM() LIMIT 5000" if not tag else ""

    rows = await conn.fetch(f"""
        WITH base AS (
            SELECT info.{col}   AS mv,
                   bm.max_vel   AS velocity,
                   bm.max_accel AS acceleration,
                   bm.weight    AS weight,
                   bx.stop_point AS stop_point
            FROM {table} info
            INNER JOIN motion.traj_metadata bm ON info.seg_id = bm.seg_id
            INNER JOIN motion.traj_info bi      ON info.traj_id = bi.traj_id
            INNER JOIN motion.traj_setpoints bx ON info.seg_id = bx.seg_id
            WHERE info.{col} IS NOT NULL AND bm.max_vel IS NOT NULL
              AND bm.max_accel IS NOT NULL AND bm.weight IS NOT NULL
              AND bx.stop_point IS NOT NULL {tc}
            {sample}
        ),
        vel_bins AS (
            SELECT 'velocity' AS param,
                   width_bucket(velocity, (SELECT MIN(velocity) FROM base),
                                          (SELECT MAX(velocity) FROM base) + 0.001, 6) AS bucket,
                   CONCAT(ROUND(MIN(velocity)::numeric), '–', ROUND(MAX(velocity)::numeric), ' mm/s') AS label,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mv) AS median,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY mv) AS q1,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY mv) AS q3,
                   MIN(mv) AS wlo, MAX(mv) AS whi, COUNT(*) AS cnt
            FROM base GROUP BY bucket
        ),
        accel_bins AS (
            SELECT 'acceleration' AS param,
                   width_bucket(acceleration, (SELECT MIN(acceleration) FROM base),
                                              (SELECT MAX(acceleration) FROM base) + 0.001, 6) AS bucket,
                   CONCAT(ROUND(MIN(acceleration)::numeric), '–', ROUND(MAX(acceleration)::numeric), ' mm/s²') AS label,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mv) AS median,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY mv) AS q1,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY mv) AS q3,
                   MIN(mv) AS wlo, MAX(mv) AS whi, COUNT(*) AS cnt
            FROM base GROUP BY bucket
        ),
        weight_bins AS (
            SELECT 'weight' AS param, weight AS bucket,
                   CONCAT(weight, ' kg') AS label,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mv) AS median,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY mv) AS q1,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY mv) AS q3,
                   MIN(mv) AS wlo, MAX(mv) AS whi, COUNT(*) AS cnt
            FROM base GROUP BY weight ORDER BY weight
        ),
        stop_bins AS (
            SELECT 'stop_point' AS param, stop_point AS bucket,
                   CONCAT(stop_point::int, '%') AS label,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mv) AS median,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY mv) AS q1,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY mv) AS q3,
                   MIN(mv) AS wlo, MAX(mv) AS whi, COUNT(*) AS cnt
            FROM base GROUP BY stop_point ORDER BY stop_point
        )
        SELECT * FROM vel_bins
        UNION ALL SELECT * FROM accel_bins
        UNION ALL SELECT * FROM weight_bins
        UNION ALL SELECT * FROM stop_bins
        ORDER BY param, bucket
    """, *tp)

    result: dict = {}
    for r in rows:
        result.setdefault(r["param"], []).append({
            "label":  r["label"],
            "median": float(r["median"]),
            "q1":     float(r["q1"]),
            "q3":     float(r["q3"]),
            "wlo":    float(r["wlo"]),
            "whi":    float(r["whi"]),
            "count":  int(r["cnt"]),
        })
    return result


_MODELS_DIR = os.path.join(os.path.dirname(__file__), "../../utils/robot_models")

def _parse_ascii_stl(path: str):
    """Parse ASCII STL → (x, y, z, i, j, k) lists for Plotly mesh3d."""
    with open(path) as f:
        content = f.read()
    verts = re.findall(r'vertex\s+([\-\d.eE+]+)\s+([\-\d.eE+]+)\s+([\-\d.eE+]+)', content)
    xs, ys, zs, ii, jj, kk = [], [], [], [], [], []
    for idx in range(0, len(verts) - 2, 3):
        base = len(xs)
        for v in verts[idx:idx + 3]:
            xs.append(float(v[0])); ys.append(float(v[1])); zs.append(float(v[2]))
        ii.append(base); jj.append(base + 1); kk.append(base + 2)
    return xs, ys, zs, ii, jj, kk


@router.get("/workarea/robot-mesh")
@cache(expire=86400, namespace="dashboard")
async def get_robot_mesh(robot: str = Query(...)):
    """Plotly mesh3d data for the robot: its workspace envelope ({robot}_workspace.stl: reach within the
    robot_info workspace, made by scripts/cut_workspace_envelopes.py) and, if present, the robot model in its
    calibration position ({robot}_model.json: list of parts {name, color, x, y, z, i, j, k})."""
    if not re.fullmatch(r"[a-z0-9_]+", robot):
        raise HTTPException(status_code=400, detail="Invalid robot model")
    stl_path = os.path.join(_MODELS_DIR, f"{robot}_workspace.stl")
    model_path = os.path.join(_MODELS_DIR, f"{robot}_model.json")
    mesh = None
    if os.path.isfile(stl_path):
        xs, ys, zs, ii, jj, kk = _parse_ascii_stl(stl_path)
        mesh = {"x": xs, "y": ys, "z": zs, "i": ii, "j": jj, "k": kk}
    model = None
    if os.path.isfile(model_path):
        with open(model_path) as f:
            model = json.load(f)
    return {"mesh": mesh, "model": model, "robot": robot}
