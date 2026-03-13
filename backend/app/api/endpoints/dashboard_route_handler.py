from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/data")
async def get_dashboard_data(conn=Depends(get_db)):
    try:
        # Bahnen und Segmente zählen - diese sind wichtig genug für exakte Zählung
        segments_count = await conn.fetchval(
            "SELECT SUM(number_setpoints) FROM motion.traj_info WHERE source_data_act = 'leica_at960'"
        )

        trajs_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT traj_id) FROM motion.traj_info WHERE source_data_act = 'leica_at960'"
        )

        median_sidtw = await conn.fetchval("""
                                           SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sidtw_average_distance)
                                           FROM evaluation.sidtw_info i
                                               INNER JOIN motion.traj_info b
                                           ON i.traj_id = b.traj_id
                                           WHERE i.traj_id = i.seg_id
                                             AND i.sidtw_average_distance IS NOT NULL
                                             AND b.source_data_act = 'leica_at960'
                                           """)

        mean_sidtw = await conn.fetchval("""
                                         SELECT AVG(sidtw_average_distance)
                                         FROM evaluation.sidtw_info i
                                               INNER JOIN motion.traj_info b
                                           ON i.traj_id = b.traj_id
                                           WHERE i.traj_id = i.seg_id
                                             AND i.sidtw_average_distance IS NOT NULL
                                             AND b.source_data_act = 'leica_at960'
                                         """)

        # Top 5 Best Performers
        best_performers_raw = await conn.fetch("""
                                                SELECT i.traj_id,
                                                    i.seg_id,
                                                    i.sidtw_average_distance,
                                                    b.weight,
                                                    b.number_setpoints as waypoints,
                                                    b.stop_point,
                                                    b.wait_time,
                                                    m.max_vel_act as max_velocity,
                                                    m.max_accel_act as max_acceleration
                                                FROM evaluation.sidtw_info i
                                                INNER JOIN motion.traj_info b ON i.traj_id = b.traj_id
                                                LEFT JOIN motion.traj_metadata m ON i.seg_id = m.seg_id
                                                WHERE i.traj_id = i.seg_id
                                                AND i.sidtw_average_distance IS NOT NULL
                                                AND b.source_data_act = 'leica_at960'
                                                ORDER BY i.sidtw_average_distance ASC 
                                                LIMIT 5
                                            """)

        # Top 5 Worst Performers
        worst_performers_raw = await conn.fetch("""
                                                SELECT i.traj_id,
                                                    i.seg_id,
                                                    i.sidtw_average_distance,
                                                    b.weight,
                                                    b.number_setpoints as waypoints,
                                                    b.stop_point,
                                                    b.wait_time,
                                                    m.max_vel_act as max_velocity,
                                                    m.max_accel_act as max_acceleration
                                                FROM evaluation.sidtw_info i
                                                INNER JOIN motion.traj_info b ON i.traj_id = b.traj_id
                                                LEFT JOIN motion.traj_metadata m ON i.seg_id = m.seg_id
                                                WHERE i.traj_id = i.seg_id
                                                AND i.sidtw_average_distance IS NOT NULL
                                                AND b.source_data_act = 'leica_at960'
                                                ORDER BY i.sidtw_average_distance DESC 
                                                LIMIT 5
                                            """)

        # Für jeden Performer: Hole alle Segment-Punkte (Trajektorie)
        best_performers = []
        for perf in best_performers_raw:
            trajectory = await conn.fetch("""
                                            SELECT x_cmd, y_cmd, z_cmd
                                            FROM motion.traj_position_cmd
                                            WHERE traj_id = $1 AND seg_id = $2
                                            ORDER BY timestamp  
                                        """, perf["traj_id"], perf["seg_id"])

            best_performers.append({
                "traj_id": perf["traj_id"],
                "seg_id": perf["seg_id"],
                "sidtw_average_distance": perf["sidtw_average_distance"],
                "weight": perf["weight"],
                "waypoints": perf["waypoints"],
                "stop_point": perf["stop_point"],
                "wait_time": perf["wait_time"],
                "max_velocity": perf["max_velocity"],
                "max_acceleration": perf["max_acceleration"],
                "trajectory": [{"x": p["x_cmd"], "y": p["y_cmd"], "z": p["z_cmd"]} for p in trajectory]
            })

        worst_performers = []
        for perf in worst_performers_raw:
            trajectory = await conn.fetch("""
                                            SELECT x_cmd, y_cmd, z_cmd
                                            FROM motion.traj_position_cmd
                                            WHERE traj_id = $1 AND seg_id = $2
                                            ORDER BY timestamp  
                                        """, perf["traj_id"], perf["seg_id"])

            worst_performers.append({
                "traj_id": perf["traj_id"],
                "seg_id": perf["seg_id"],
                "sidtw_average_distance": perf["sidtw_average_distance"],
                "weight": perf["weight"],
                "waypoints": perf["waypoints"],
                "stop_point": perf["stop_point"],
                "wait_time": perf["wait_time"],
                "max_velocity": perf["max_velocity"],
                "max_acceleration": perf["max_acceleration"],
                "trajectory": [{"x": p["x_cmd"], "y": p["y_cmd"], "z": p["z_cmd"]} for p in trajectory]
            })

        stats = {}

        # Velocity Distribution - mit festen Buckets
        velocity_query = """
                         SELECT CASE \
                                    WHEN max_vel_act < 500 THEN 1 \
                                    WHEN max_vel_act >= 500 AND max_vel_act < 1000 THEN 2 \
                                    WHEN max_vel_act >= 1000 AND max_vel_act < 1500 THEN 3 \
                                    WHEN max_vel_act >= 1500 AND max_vel_act < 2000 THEN 4 \
                                    WHEN max_vel_act >= 2000 AND max_vel_act < 2500 THEN 5 \
                                    WHEN max_vel_act >= 2500 AND max_vel_act < 3000 THEN 6 \
                                    WHEN max_vel_act >= 3000 THEN 7 \
                                    END AS bucket, \
                                COUNT(*)
                         FROM motion.traj_metadata
                         WHERE traj_id != seg_id
                           AND max_vel_act IS NOT NULL
                         GROUP BY bucket
                         ORDER BY bucket \
                         """
        velocity_rows = await conn.fetch(velocity_query)
        stats["velocityDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in velocity_rows],
            "meta": {
                "useRanges": True,
                "min": 0,
                "max": 3500,
                "numBuckets": 7,
                "unit": "mm/s",
                "label": "Geschwindigkeit"
            }
        }

        # Weight Distribution
        weight_query = """
            SELECT weight AS bucket, COUNT(*)
            FROM motion.traj_info
                WHERE source_data_act = 'leica_at960'
            GROUP BY bucket
            ORDER BY bucket
        """
        weight_rows = await conn.fetch(weight_query)
        stats["weightDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in weight_rows],
            "meta": {
                "useRanges": False,
                "unit": "kg",
                "label": "Last"
            }
        }

        # Waypoint Distribution
        waypoints_query = """
            SELECT number_setpoints AS bucket, COUNT(*)
            FROM motion.traj_info
                WHERE source_data_act = 'leica_at960'
            GROUP BY bucket
            ORDER BY bucket
        """
        waypoint_rows = await conn.fetch(waypoints_query)
        stats["waypointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in waypoint_rows],
            "meta": {
                "useRanges": False,
                "unit": "-",
                "label": "Zielpunkte"
            }
        }

        # Performance SIDTW Distribution
        sidtw_query = """
            WITH sidtw_stats AS (
                SELECT MAX(i.sidtw_average_distance) as max_val
                FROM evaluation.sidtw_info i
                INNER JOIN motion.traj_info b ON i.traj_id = b.traj_id
                WHERE i.traj_id != i.seg_id
                  AND i.sidtw_average_distance IS NOT NULL
                  AND b.source_data_act = 'leica_at960'
            )
            SELECT 
                width_bucket(i.sidtw_average_distance, 
                    0, 
                    (SELECT max_val FROM sidtw_stats), 
                    8
                ) AS bucket, 
                COUNT(*)
            FROM evaluation.sidtw_info i
            INNER JOIN motion.traj_info b ON i.traj_id = b.traj_id
            WHERE i.traj_id != i.seg_id
              AND i.sidtw_average_distance IS NOT NULL
              AND b.source_data_act = 'leica_at960'
            GROUP BY bucket
            ORDER BY bucket
        """
        sidtw_rows = await conn.fetch(sidtw_query)
        sidtw_max = await conn.fetchval("""
            SELECT MAX(sidtw_average_distance) 
            FROM evaluation.sidtw_info i
            INNER JOIN motion.traj_info b ON i.traj_id = b.traj_id
            WHERE i.traj_id != i.seg_id 
              AND i.sidtw_average_distance IS NOT NULL
              AND b.source_data_act = 'leica_at960'
        """)
        stats["performanceSIDTWDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in sidtw_rows],
            "meta": {
                "useRanges": True,
                "min": 0,
                "max": sidtw_max,
                "numBuckets": 9,
                "unit": "mm",
                "label": "Genauigkeit"
            }
        }

        # Stop Point Distribution
        stop_query = """
            SELECT stop_point AS bucket, COUNT(*)
            FROM motion.traj_info
            WHERE stop_point IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        stop_rows = await conn.fetch(stop_query)
        stats["stopPointDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in stop_rows],
            "meta": {
                "useRanges": False,
                "unit": "%",
                "label": "Stopp-Punkte"
            }
        }

        # Wait Time Distribution
        wait_query = """
            SELECT wait_time AS bucket, COUNT(*)
            FROM motion.traj_info
            WHERE wait_time IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """
        wait_rows = await conn.fetch(wait_query)
        stats["waitTimeDistribution"] = {
            "data": [{"bucket": r["bucket"], "count": r["count"]} for r in wait_rows],
            "meta": {
                "useRanges": False,
                "unit": "s",
                "label": "Wartezeit"
            }
        }

        return {
            "segmentsCount": segments_count,
            "trajsCount": trajs_count,
            "medianSIDTW": median_sidtw,
            "meanSIDTW": mean_sidtw,
            "bestPerformers": best_performers,
            "worstPerformers": worst_performers,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/timeline")
@cache(expire=24600)
async def get_dashboard_timeline(conn=Depends(get_db)):
    """
    Endpoint für SIDTW-Werte über Zeit
    Gibt durchschnittliche SIDTW-Werte pro Aufnahmedatum zurück
    """
    try:
        query = """
                SELECT
                    DATE (bi.recording_date) as date, AVG (info.sidtw_average_distance) as avg_sidtw, MIN (info.sidtw_average_distance) as min_sidtw, MAX (info.sidtw_average_distance) as max_sidtw, COUNT (*) as count
                FROM motion.traj_info bi
                    INNER JOIN evaluation.sidtw_info info
                ON bi.traj_id = info.traj_id
                    AND bi.traj_id = info.seg_id
                WHERE
                    bi.recording_date IS NOT NULL
                  AND info.sidtw_average_distance IS NOT NULL
                GROUP BY DATE (bi.recording_date)
                ORDER BY date ASC \
                """

        rows = await conn.fetch(query)

        return {
            "timeline": [
                {
                    "date": str(row['date']),
                    "avg_sidtw": float(row['avg_sidtw']),
                    "min_sidtw": float(row['min_sidtw']),
                    "max_sidtw": float(row['max_sidtw']),
                    "count": int(row['count'])
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/influence")
@cache(expire=24600)
async def get_dashboard_influence(conn=Depends(get_db)):
    """
    Endpoint für SIDTW vs. verschiedene Bewegungsparameter als Box Plot Daten
    Gruppiert Parameter in Bins und gibt alle SIDTW-Werte pro Bin zurück
    """
    try:
        query = """
                WITH sampled_data AS (SELECT info.sidtw_average_distance as sidtw, \
                                             bm.max_vel_act           as velocity, \
                                             bm.max_accel_act     as acceleration, \
                                             bi.weight                   as weight, \
                                             bi.stop_point               as stop_point, \
                                             bi.wait_time                as wait_time \
                                      FROM evaluation.sidtw_info info \
                                               INNER JOIN motion.traj_metadata bm \
                                                          ON info.traj_id = bm.traj_id \
                                                              AND info.traj_id = bm.seg_id \
                                                              AND bm.traj_id = bm.seg_id \
                                               INNER JOIN motion.traj_info bi \
                                                          ON info.traj_id = bi.traj_id \
                                      WHERE info.traj_id = info.seg_id \
                                        AND info.sidtw_average_distance IS NOT NULL \
                                        AND bi.source_data_act = 'leica_at960' \
                                        AND bm.max_vel_act IS NOT NULL \
                                        AND bm.max_accel_act IS NOT NULL \
                                        AND bi.weight IS NOT NULL \
                                        AND bi.stop_point IS NOT NULL \
                                        AND bi.wait_time IS NOT NULL \
                                      ORDER BY RANDOM()
                    LIMIT 5000
                    )
                SELECT * \
                FROM sampled_data \
                """

        rows = await conn.fetch(query)

        # Gib Rohdaten zurück - Binning wird im Frontend gemacht
        return {
            "data": [
                {
                    "sidtw": float(row['sidtw']),
                    "velocity": float(row['velocity']),
                    "acceleration": float(row['acceleration']),
                    "weight": float(row['weight']),
                    "stop_point": float(row['stop_point']),
                    "wait_time": float(row['wait_time'])
                }
                for row in rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW vs parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/workarea")
@cache(expire=24600)
async def get_dashboard_workarea(conn=Depends(get_db)):
    try:
        workarea_query = """
                         WITH numbered_events AS (SELECT be.x_reached, \
                                                         be.y_reached, \
                                                         be.z_reached, \
                                                         s.sidtw_average_distance, \
                                                         ROW_NUMBER() OVER (PARTITION BY be.traj_id ORDER BY be.timestamp) as rn \
                                                  FROM motion.traj_setpoints be \
                                                           JOIN evaluation.sidtw_info s ON be.traj_id = s.traj_id \
                                                           JOIN motion.traj_info bi ON be.traj_id = bi.traj_id \
                                                  WHERE s.traj_id <> s.seg_id \
                                                    AND s.sidtw_average_distance IS NOT NULL \
                                                    AND be.x_reached IS NOT NULL \
                                                    AND be.y_reached IS NOT NULL \
                                                    AND be.z_reached IS NOT NULL \
                                                    AND bi.recording_date >= '2025-03-01'
                         )
                         SELECT x_reached, y_reached, z_reached, sidtw_average_distance
                         FROM numbered_events
                         WHERE rn % 9 = 0 \
                         """

        workarea_rows = await conn.fetch(workarea_query)

        return {
            "points": [
                {
                    "x": r["x_reached"],
                    "y": r["y_reached"],
                    "z": r["z_reached"],
                    "sidtw": r["sidtw_average_distance"]
                }
                for r in workarea_rows
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching workarea data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")