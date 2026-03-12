from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard_data")
async def get_dashboard_data(conn=Depends(get_db)):
    try:
        # Bahnen und Segmente zählen - diese sind wichtig genug für exakte Zählung
        segments_count = await conn.fetchval(
            "SELECT SUM(number_setpoints) FROM motion.traj_info WHERE source_data_act = 'leica_at960'"
        )

        trajen_count = await conn.fetchval(
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
            "trajenCount": trajen_count,
            "medianSIDTW": median_sidtw,
            "meanSIDTW": mean_sidtw,
            "bestPerformers": best_performers,
            "worstPerformers": worst_performers,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/dashboard_sidtw_timeline")
@cache(expire=24600)
async def get_dashboard_sidtw_timeline(conn=Depends(get_db)):
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


@router.get("/dashboard_sidtw_vs_parameters")
@cache(expire=24600)
async def get_dashboard_sidtw_vs_parameters(conn=Depends(get_db)):
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

@router.get("/dashboard_workarea")
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

########################## BEWEGUNGSDATEN #########################################

@router.get("/traj_info")
async def get_traj_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # Zähle die Gesamtanzahl der Einträge für die Metadaten
        count_query = "SELECT COUNT(*) FROM motion.traj_info"
        total_count = await conn.fetchval(count_query)

        # Abfrage mit LIMIT und OFFSET für Pagination
        query = "SELECT * FROM motion.traj_info ORDER BY recording_date DESC LIMIT $1 OFFSET $2"
        rows = await conn.fetch(query, page_size, offset)

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
        conn=Depends(get_db)
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
            base_query += f" AND (b.setted_velocity = ${param_index} OR b.velocity_picking = ${param_index})"
            params.append(setted_velocity)
            param_index += 1

        if recording_date is not None:
            # Jahr (4 Ziffern): 2024
            if recording_date.isdigit() and len(recording_date) == 4:
                base_query += f" AND b.recording_date LIKE ${param_index}"
                params.append(f"{recording_date}-%")
                param_index += 1

            # DD.MM.YYYY Format: 09.07.2024
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

            # DD.MM.YYYY HH:MM Format: 09.07.2024 17:52
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
        
        if sidtw_distance is not None:
            tolerance = sidtw_distance * 0.1  # 10% Toleranz
            base_query += f" AND i.sidtw_average_distance IS NOT NULL AND i.sidtw_average_distance BETWEEN ${param_index} AND ${param_index + 1}"
            params.extend([sidtw_distance - tolerance, sidtw_distance + tolerance])
            param_index += 2

        # Zähle Gesamtanzahl für Pagination
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS filtered_data"
        total_count = await conn.fetchval(count_query, *params)

        # Füge Sortierung und Pagination hinzu
        query = base_query + f" ORDER BY b.recording_date DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([page_size, (page - 1) * page_size])

        rows = await conn.fetch(query, *params)
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

@router.get("/check_transformed_data/{traj_id}")
@cache(expire=24000)
async def check_transformed_data(traj_id: str, conn = Depends(get_db)):
    try:
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM motion.traj_pose_act_raw 
                WHERE traj_id = $1
                LIMIT 1
            )
        """, traj_id)
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking transformed data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/traj_pose_act/{traj_id}")
@cache(expire=2400)
async def get_traj_pose_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_pose_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_pose_act_raw/{traj_id}")
@cache(expire=2400)
async def get_traj_pose_trans_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_pose_act_raw WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]


@router.get("/traj_vel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_twist_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_vel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_act/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_ist_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_accel_act WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_accel_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_accel_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_accel_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_position_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_position_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_position_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/seg_position_cmd/{segment_id}")
@cache(expire=2400)
async def get_segment_position_soll_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_position_cmd WHERE seg_id = $1 ORDER BY timestamp ASC",
        segment_id
    )
    return [dict(row) for row in rows]


@router.get("/traj_orientation_cmd/{traj_id}")
@cache(expire=2400)
async def get_traj_orientation_soll_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_orientation_cmd WHERE traj_id = $1 ORDER BY timestamp ASC",
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
        "SELECT * FROM motion.traj_joint_states WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_setpoints/{traj_id}")
@cache(expire=2400)
async def get_traj_events_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_setpoints WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]

@router.get("/seg_setpoints/{segment_id}")
@cache(expire=2400)
async def get_segment_events_by_id(segment_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_setpoints WHERE seg_id = $1 ORDER BY timestamp ASC",
        segment_id
    )
    return [dict(row) for row in rows]

@router.get("/traj_imu/{traj_id}")
@cache(expire=2400)
async def get_traj_imu_by_id(traj_id: str, conn = Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM motion.traj_imu WHERE traj_id = $1 ORDER BY timestamp ASC",
        traj_id
    )
    return [dict(row) for row in rows]


