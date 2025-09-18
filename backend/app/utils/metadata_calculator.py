import asyncpg
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class MetadataCalculatorService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def validate_datetime_input(self, date_string: str) -> Optional[int]:
        """
        Validiert und konvertiert Datetime-String in Unix-Timestamp (10 Stellen)
        Format: YYYY-MM-DD HH:MM:SS oder DD.MM.YYYY HH:MM:SS
        """
        try:
            # Prüfe ISO-Format (YYYY-MM-DD HH:MM:SS)
            iso_pattern = r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'
            if re.match(iso_pattern, date_string.strip()):
                dt = datetime.strptime(date_string.strip(), '%Y-%m-%d %H:%M:%S')
                return int(dt.timestamp())

            # Prüfe deutsches Format (DD.MM.YYYY HH:MM:SS)
            german_pattern = r'^\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}:\d{2}$'
            if re.match(german_pattern, date_string.strip()):
                dt = datetime.strptime(date_string.strip(), '%d.%m.%Y %H:%M:%S')
                return int(dt.timestamp())

            return None

        except ValueError:
            return None

    async def get_bahn_ids_for_timerange(self, start_unix: int, end_unix: int) -> List[str]:
        """Ermittelt alle bahn_ids im angegebenen Zeitraum basierend auf recording_date"""
        async with self.db_pool.acquire() as conn:
            # Konvertiere Unix-Timestamps zu Datum-Strings
            start_date = datetime.fromtimestamp(start_unix).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(end_unix).strftime('%Y-%m-%d')

            query = """
                    SELECT bahn_id
                    FROM robotervermessung.bewegungsdaten.bahn_info
                    WHERE LEFT (recording_date \
                        , 10) BETWEEN $1 \
                      AND $2
                    GROUP BY bahn_id
                    ORDER BY bahn_id::text \
                    """
            rows = await conn.fetch(query, start_date, end_date)
            return [row['bahn_id'] for row in rows]

    async def get_all_missing_bahn_ids(self) -> List[str]:
        """Ermittelt alle bahn_ids die noch keine Metadaten haben"""
        async with self.db_pool.acquire() as conn:
            query = """
            SELECT DISTINCT bi.bahn_id
            FROM robotervermessung.bewegungsdaten.bahn_info bi
            LEFT JOIN robotervermessung.bewegungsdaten.bahn_meta bm
            ON bi.bahn_id = bm.bahn_id AND bm.segment_id = bm.bahn_id
            WHERE bm.bahn_id IS NULL
            ORDER BY bi.bahn_id
            """
            rows = await conn.fetch(query)
            return [row['bahn_id'] for row in rows]

    async def check_existing_bahns(self, bahn_ids: List[str]) -> List[str]:
        """Prüft welche bahn_ids bereits Metadaten haben"""
        if not bahn_ids:
            return []

        async with self.db_pool.acquire() as conn:
            query = """
                    SELECT DISTINCT bahn_id
                    FROM robotervermessung.bewegungsdaten.bahn_meta
                    WHERE bahn_id = ANY ($1::text[]) \
                    """
            rows = await conn.fetch(query, bahn_ids)
            return [row['bahn_id'] for row in rows]

    async def delete_existing_metadata(self, bahn_ids: List[str]) -> int:
        """Löscht vorhandene Metadaten für gegebene bahn_ids"""
        if not bahn_ids:
            return 0

        async with self.db_pool.acquire() as conn:
            query = """
                    DELETE \
                    FROM robotervermessung.bewegungsdaten.bahn_meta
                    WHERE bahn_id = ANY ($1::text[]) \
                    """
            result = await conn.execute(query, bahn_ids)
            return int(result.split()[-1]) if result.startswith("DELETE") else 0

    async def calculate_segment_metadata(self, conn: asyncpg.Connection, bahn_id: str, segment_id: str) -> Optional[
        Dict]:
        """Berechnet Metadaten für ein einzelnes Segment - OPTIMIERT"""
        try:
            # OPTIMIERUNG 1 & 3: Kombinierte Query mit Sampling für Movement Type
            # Separate Queries für bessere SQL-Kompatibilität
            # 1. Sample Daten für Movement Type
            sample_query = """
                           WITH pos_sample \
                                    AS (SELECT x_soll, y_soll, z_soll, timestamp, ROW_NUMBER() OVER (ORDER BY timestamp) as rn, COUNT (*) OVER() as total_count
                           FROM robotervermessung.bewegungsdaten.bahn_position_soll
                           WHERE bahn_id = $1 \
                             AND segment_id = $2
                               )
                           SELECT x_soll, y_soll, z_soll
                           FROM pos_sample
                           WHERE rn % GREATEST(1, total_count / 20) = 1
                           ORDER BY timestamp \
                           """

            # 2. Kombinierte Statistiken-Query
            stats_query = """
                          WITH pos_stats AS (SELECT MIN(x_soll)    as min_pos_x, \
                                                    MAX(x_soll)    as max_pos_x, \
                                                    MIN(y_soll)    as min_pos_y, \
                                                    MAX(y_soll)    as max_pos_y, \
                                                    MIN(z_soll)    as min_pos_z, \
                                                    MAX(z_soll)    as max_pos_z, \
                                                    MIN(timestamp) as min_timestamp, \
                                                    MAX(timestamp) as max_timestamp \
                                             FROM robotervermessung.bewegungsdaten.bahn_position_soll \
                                             WHERE bahn_id = $1 \
                                               AND segment_id = $2),
                               pos_first_last \
                                   AS (SELECT FIRST_VALUE(x_soll) OVER (ORDER BY timestamp) as first_x, FIRST_VALUE(y_soll) OVER (ORDER BY timestamp) as first_y, FIRST_VALUE(z_soll) OVER (ORDER BY timestamp) as first_z, LAST_VALUE(x_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_x, LAST_VALUE(y_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_y, LAST_VALUE(z_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_z \
                                       FROM robotervermessung.bewegungsdaten.bahn_position_soll \
                                       WHERE bahn_id = $1 \
                                         AND segment_id = $2
                              LIMIT 1
                              ), orient_stats AS (
                          SELECT MIN (qw_soll) as min_qw, MAX (qw_soll) as max_qw, MIN (qx_soll) as min_qx, MAX (qx_soll) as max_qx, MIN (qy_soll) as min_qy, MAX (qy_soll) as max_qy, MIN (qz_soll) as min_qz, MAX (qz_soll) as max_qz
                          FROM robotervermessung.bewegungsdaten.bahn_orientation_soll
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , twist_stats AS (
                          SELECT ROUND(MIN (tcp_speed_ist):: numeric, 3) as min_twist, ROUND(MAX (tcp_speed_ist):: numeric, 3) as max_twist, ROUND(AVG (tcp_speed_ist):: numeric, 3) as median_twist, ROUND(STDDEV(tcp_speed_ist):: numeric, 3) as std_twist
                          FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , accel_stats AS (
                          SELECT MIN (tcp_accel_ist) as min_accel, MAX (tcp_accel_ist) as max_accel, AVG (tcp_accel_ist) as median_accel, STDDEV(tcp_accel_ist) as std_accel
                          FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , joint_stats AS (
                          SELECT MIN (joint_1) as min_joint_1, MAX (joint_1) as max_joint_1, MIN (joint_2) as min_joint_2, MAX (joint_2) as max_joint_2, MIN (joint_3) as min_joint_3, MAX (joint_3) as max_joint_3, MIN (joint_4) as min_joint_4, MAX (joint_4) as max_joint_4, MIN (joint_5) as min_joint_5, MAX (joint_5) as max_joint_5, MIN (joint_6) as min_joint_6, MAX (joint_6) as max_joint_6
                          FROM robotervermessung.bewegungsdaten.bahn_joint_states
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              )
                          SELECT ps.*, pfl.*, os.*, ts.*, acs.*, js.*
                          FROM pos_stats ps
                                   CROSS JOIN pos_first_last pfl
                                   LEFT JOIN orient_stats os ON true
                                   LEFT JOIN twist_stats ts ON true
                                   LEFT JOIN accel_stats acs ON true
                                   LEFT JOIN joint_stats js ON true \
                          """

            # Führe beide Queries aus
            sample_rows = await conn.fetch(sample_query, bahn_id, segment_id)
            stats_result = await conn.fetchrow(stats_query, bahn_id, segment_id)

            if not stats_result:
                return None

            # OPTIMIERUNG 2: Vereinfachte Movement Type Detection
            if sample_rows:
                x_data = np.array([row['x_soll'] for row in sample_rows])
                y_data = np.array([row['y_soll'] for row in sample_rows])
                z_data = np.array([row['z_soll'] for row in sample_rows])
            else:
                x_data = y_data = z_data = np.array([])

            movement_type = self.detect_movement_type_optimized(x_data, y_data, z_data)

            # Duration berechnen
            segment_duration = 0.0
            try:
                if stats_result['min_timestamp'] and stats_result['max_timestamp']:
                    min_ts_int = int(float(stats_result['min_timestamp']))
                    max_ts_int = int(float(stats_result['max_timestamp']))
                    diff_ns = max_ts_int - min_ts_int
                    segment_duration = max(diff_ns / 1_000_000_000.0, 0.0)
            except Exception as e:
                logger.warning(f"Fehler bei Duration-Berechnung Segment {segment_id}: {e}")

            # Richtung und Länge aus DB-Daten berechnen
            dx = stats_result['last_x'] - stats_result['first_x']
            dy = stats_result['last_y'] - stats_result['first_y']
            dz = stats_result['last_z'] - stats_result['first_z']
            length = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

            if length > 0:
                direction_x = dx / length
                direction_y = dy / length
                direction_z = dz / length
            else:
                direction_x = direction_y = direction_z = 0.0

            def safe_round(value, decimals=3):
                return round(float(value), decimals) if value is not None else None

            return {
                'bahn_id': bahn_id,
                'segment_id': segment_id,
                'movement_type': movement_type,
                'duration': round(segment_duration, 3),
                'length': round(length, 3),
                'direction_x': round(direction_x, 3),
                'direction_y': round(direction_y, 3),
                'direction_z': round(direction_z, 3),
                'min_position_x_soll': safe_round(stats_result['min_pos_x']),
                'min_position_y_soll': safe_round(stats_result['min_pos_y']),
                'min_position_z_soll': safe_round(stats_result['min_pos_z']),
                'max_position_x_soll': safe_round(stats_result['max_pos_x']),
                'max_position_y_soll': safe_round(stats_result['max_pos_y']),
                'max_position_z_soll': safe_round(stats_result['max_pos_z']),
                'min_orientation_qw_soll': safe_round(stats_result['min_qw']),
                'min_orientation_qx_soll': safe_round(stats_result['min_qx']),
                'min_orientation_qy_soll': safe_round(stats_result['min_qy']),
                'min_orientation_qz_soll': safe_round(stats_result['min_qz']),
                'max_orientation_qw_soll': safe_round(stats_result['max_qw']),
                'max_orientation_qx_soll': safe_round(stats_result['max_qx']),
                'max_orientation_qy_soll': safe_round(stats_result['max_qy']),
                'max_orientation_qz_soll': safe_round(stats_result['max_qz']),
                'min_twist_ist': safe_round(stats_result['min_twist']),
                'max_twist_ist': safe_round(stats_result['max_twist']),
                'median_twist_ist': safe_round(stats_result['median_twist']),
                'std_twist_ist': safe_round(stats_result['std_twist']),
                'min_acceleration_ist': safe_round(stats_result['min_accel']),
                'max_acceleration_ist': safe_round(stats_result['max_accel']),
                'median_acceleration_ist': safe_round(stats_result['median_accel']),
                'std_acceleration_ist': safe_round(stats_result['std_accel']),
                'min_states_joint_1': safe_round(stats_result['min_joint_1']),
                'min_states_joint_2': safe_round(stats_result['min_joint_2']),
                'min_states_joint_3': safe_round(stats_result['min_joint_3']),
                'min_states_joint_4': safe_round(stats_result['min_joint_4']),
                'min_states_joint_5': safe_round(stats_result['min_joint_5']),
                'min_states_joint_6': safe_round(stats_result['min_joint_6']),
                'max_states_joint_1': safe_round(stats_result['max_joint_1']),
                'max_states_joint_2': safe_round(stats_result['max_joint_2']),
                'max_states_joint_3': safe_round(stats_result['max_joint_3']),
                'max_states_joint_4': safe_round(stats_result['max_joint_4']),
                'max_states_joint_5': safe_round(stats_result['max_joint_5']),
                'max_states_joint_6': safe_round(stats_result['max_joint_6'])
            }

        except Exception as e:
            logger.error(f"Fehler bei Segment {segment_id} in bahn_id {bahn_id}: {e}")
            return None

    def detect_movement_type(self, x_data: np.ndarray, y_data: np.ndarray, z_data: np.ndarray) -> str:
        if len(x_data) < 4:
            return "linear"

        try:
            positions = np.column_stack([x_data, y_data, z_data])
            n_points = len(positions)

            # Start- und Endpunkt für Linear-Test
            start_point = positions[0]
            end_point = positions[-1]
            main_direction = end_point - start_point
            main_distance = np.linalg.norm(main_direction)

            if main_distance < 1e-6:
                return "linear"

            # VEKTORISIERTER LINEAR TEST
            main_direction_norm = main_direction / main_distance

            # Sampling für Performance (max 10 Punkte)
            n_check = min(10, n_points - 2)
            indices = np.linspace(1, n_points - 2, n_check, dtype=int)

            # Alle Zwischenpunkte auf einmal
            sample_points = positions[indices]
            point_vectors = sample_points - start_point

            # Vektorisierte Projektion
            projection_lengths = np.dot(point_vectors, main_direction_norm)
            projection_points = start_point + projection_lengths[:, np.newaxis] * main_direction_norm

            # Vektorisierte Distanzberechnung
            deviations = np.linalg.norm(sample_points - projection_points, axis=1)
            max_deviation = np.max(deviations)
            relative_deviation = max_deviation / main_distance

            # Sehr gerade Linie = linear
            if relative_deviation < 0.03:
                return "linear"

            # VEKTORISIERTER CIRCULAR TEST
            # Sampling für Krümmung (max 8 Tripel)
            step = max(1, n_points // 8)
            tripel_indices = np.arange(0, n_points - 2 * step, step)
            n_tripel = len(tripel_indices)

            if n_tripel < 2:
                # Fallback für sehr kurze Segmente
                return "circular" if 0.08 < relative_deviation < 0.2 else "spline"

            # Alle Punkt-Tripel auf einmal
            p1_indices = tripel_indices
            p2_indices = tripel_indices + step
            p3_indices = tripel_indices + 2 * step

            # Begrenze auf verfügbare Indices
            valid_mask = p3_indices < n_points
            p1_indices = p1_indices[valid_mask]
            p2_indices = p2_indices[valid_mask]
            p3_indices = p3_indices[valid_mask]

            if len(p1_indices) < 2:
                return "circular" if 0.08 < relative_deviation < 0.2 else "spline"

            p1s = positions[p1_indices]
            p2s = positions[p2_indices]
            p3s = positions[p3_indices]

            # Vektorisierte Vektor-Berechnung
            v1s = p2s - p1s
            v2s = p3s - p2s

            # Vektorisierte Längen
            d1s = np.linalg.norm(v1s, axis=1)
            d2s = np.linalg.norm(v2s, axis=1)

            # Filtere zu kurze Segmente
            valid_lengths = (d1s > 1e-6) & (d2s > 1e-6)
            if np.sum(valid_lengths) < 2:
                return "circular" if 0.08 < relative_deviation < 0.2 else "spline"

            v1s = v1s[valid_lengths]
            v2s = v2s[valid_lengths]
            d1s = d1s[valid_lengths]
            d2s = d2s[valid_lengths]
            p1s = p1s[valid_lengths]
            p3s = p3s[valid_lengths]

            # Vektorisierte Winkel-Berechnung
            dot_products = np.sum(v1s * v2s, axis=1)
            cos_angles = np.clip(dot_products / (d1s * d2s), -1.0, 1.0)
            angles = np.arccos(cos_angles)

            # Gesamtwinkel
            total_angle = np.sum(angles)

            # Vektorisierte Krümmungsradius-Berechnung
            chord_lengths = np.linalg.norm(p3s - p1s, axis=1)
            sin_half_angles = np.sin(angles / 2)

            # Filtere sehr kleine Winkel
            valid_angles = sin_half_angles > 1e-6
            if np.sum(valid_angles) < 2:
                return "circular" if 0.08 < relative_deviation < 0.2 else "spline"

            valid_chord_lengths = chord_lengths[valid_angles]
            valid_sin_half_angles = sin_half_angles[valid_angles]

            # Radien berechnen
            radii = valid_chord_lengths / (2 * valid_sin_half_angles)

            # Filtere unrealistische Radien
            realistic_radii = radii[radii < 1000]

            # CIRCULAR: Konstanter Krümmungsradius + ausreichend Krümmung
            if len(realistic_radii) >= 2:
                mean_radius = np.mean(realistic_radii)
                radius_std = np.std(realistic_radii)

                # Konstanter Radius + min. 20° Gesamtwinkel
                if (mean_radius > 0 and
                        radius_std / mean_radius < 0.4 and
                        total_angle > np.pi / 9):  # 20 Grad
                    return "circular"

            # Fallback basierend auf Abweichung
            if relative_deviation > 0.9:
                return "spline"
            elif relative_deviation > 0.08:
                return "circular"
            else:
                return "linear"

        except Exception as e:
            logger.warning(f"Fehler bei Movement-Type-Erkennung: {e}")
            return "linear"

    async def calculate_segment_metadata(self, conn: asyncpg.Connection, bahn_id: str, segment_id: str) -> Optional[
        Dict]:
        try:
            sample_query = """
                           WITH pos_sample \
                                    AS (SELECT x_soll, y_soll, z_soll, timestamp, ROW_NUMBER() OVER (ORDER BY timestamp) as rn, COUNT (*) OVER() as total_count
                           FROM robotervermessung.bewegungsdaten.bahn_position_soll
                           WHERE bahn_id = $1 \
                             AND segment_id = $2
                               )
                           SELECT x_soll, y_soll, z_soll
                           FROM pos_sample
                           WHERE rn % GREATEST(1, total_count / 20) = 1
                           ORDER BY timestamp \
                           """

            # 2. Kombinierte Statistiken-Query
            stats_query = """
                          WITH pos_stats AS (SELECT MIN(x_soll)    as min_pos_x, \
                                                    MAX(x_soll)    as max_pos_x, \
                                                    MIN(y_soll)    as min_pos_y, \
                                                    MAX(y_soll)    as max_pos_y, \
                                                    MIN(z_soll)    as min_pos_z, \
                                                    MAX(z_soll)    as max_pos_z, \
                                                    MIN(timestamp) as min_timestamp, \
                                                    MAX(timestamp) as max_timestamp \
                                             FROM robotervermessung.bewegungsdaten.bahn_position_soll \
                                             WHERE bahn_id = $1 \
                                               AND segment_id = $2),
                               pos_first_last \
                                   AS (SELECT FIRST_VALUE(x_soll) OVER (ORDER BY timestamp) as first_x, FIRST_VALUE(y_soll) OVER (ORDER BY timestamp) as first_y, FIRST_VALUE(z_soll) OVER (ORDER BY timestamp) as first_z, LAST_VALUE(x_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_x, LAST_VALUE(y_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_y, LAST_VALUE(z_soll) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_z \
                                       FROM robotervermessung.bewegungsdaten.bahn_position_soll \
                                       WHERE bahn_id = $1 \
                                         AND segment_id = $2
                              LIMIT 1
                              ), orient_stats AS (
                          SELECT MIN (qw_soll) as min_qw, MAX (qw_soll) as max_qw, MIN (qx_soll) as min_qx, MAX (qx_soll) as max_qx, MIN (qy_soll) as min_qy, MAX (qy_soll) as max_qy, MIN (qz_soll) as min_qz, MAX (qz_soll) as max_qz
                          FROM robotervermessung.bewegungsdaten.bahn_orientation_soll
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , twist_stats AS (
                          SELECT ROUND(MIN (tcp_speed_ist):: numeric, 3) as min_twist, ROUND(MAX (tcp_speed_ist):: numeric, 3) as max_twist, ROUND(AVG (tcp_speed_ist):: numeric, 3) as median_twist, ROUND(STDDEV(tcp_speed_ist):: numeric, 3) as std_twist
                          FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , accel_stats AS (
                          SELECT MIN (tcp_accel_ist) as min_accel, MAX (tcp_accel_ist) as max_accel, AVG (tcp_accel_ist) as median_accel, STDDEV(tcp_accel_ist) as std_accel
                          FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              ) \
                              , joint_stats AS (
                          SELECT MIN (joint_1) as min_joint_1, MAX (joint_1) as max_joint_1, MIN (joint_2) as min_joint_2, MAX (joint_2) as max_joint_2, MIN (joint_3) as min_joint_3, MAX (joint_3) as max_joint_3, MIN (joint_4) as min_joint_4, MAX (joint_4) as max_joint_4, MIN (joint_5) as min_joint_5, MAX (joint_5) as max_joint_5, MIN (joint_6) as min_joint_6, MAX (joint_6) as max_joint_6
                          FROM robotervermessung.bewegungsdaten.bahn_joint_states
                          WHERE bahn_id = $1 \
                            AND segment_id = $2
                              )
                          SELECT ps.*, pfl.*, os.*, ts.*, acs.*, js.*
                          FROM pos_stats ps
                                   CROSS JOIN pos_first_last pfl
                                   LEFT JOIN orient_stats os ON true
                                   LEFT JOIN twist_stats ts ON true
                                   LEFT JOIN accel_stats acs ON true
                                   LEFT JOIN joint_stats js ON true \
                          """

            # Führe beide Queries aus
            sample_rows = await conn.fetch(sample_query, bahn_id, segment_id)
            stats_result = await conn.fetchrow(stats_query, bahn_id, segment_id)

            if not stats_result:
                return None

            # OPTIMIERUNG 2: Vereinfachte Movement Type Detection
            if sample_rows:
                x_data = np.array([row['x_soll'] for row in sample_rows])
                y_data = np.array([row['y_soll'] for row in sample_rows])
                z_data = np.array([row['z_soll'] for row in sample_rows])
            else:
                x_data = y_data = z_data = np.array([])

            movement_type = self.detect_movement_type(x_data, y_data, z_data)

            # Duration berechnen
            segment_duration = 0.0
            try:
                if stats_result['min_timestamp'] and stats_result['max_timestamp']:
                    min_ts_int = int(float(stats_result['min_timestamp']))
                    max_ts_int = int(float(stats_result['max_timestamp']))
                    diff_ns = max_ts_int - min_ts_int
                    segment_duration = max(diff_ns / 1_000_000_000.0, 0.0)
            except Exception as e:
                logger.warning(f"Fehler bei Duration-Berechnung Segment {segment_id}: {e}")

            # Richtung und Länge aus DB-Daten berechnen
            dx = stats_result['last_x'] - stats_result['first_x']
            dy = stats_result['last_y'] - stats_result['first_y']
            dz = stats_result['last_z'] - stats_result['first_z']
            length = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

            if length > 0:
                direction_x = dx / length
                direction_y = dy / length
                direction_z = dz / length
            else:
                direction_x = direction_y = direction_z = 0.0

            def safe_round(value, decimals=3):
                return round(float(value), decimals) if value is not None else None

            return {
                'bahn_id': bahn_id,
                'segment_id': segment_id,
                'movement_type': movement_type,
                'duration': round(segment_duration, 3),
                'length': round(length, 3),
                'direction_x': round(direction_x, 3),
                'direction_y': round(direction_y, 3),
                'direction_z': round(direction_z, 3),
                'min_position_x_soll': safe_round(stats_result['min_pos_x']),
                'min_position_y_soll': safe_round(stats_result['min_pos_y']),
                'min_position_z_soll': safe_round(stats_result['min_pos_z']),
                'max_position_x_soll': safe_round(stats_result['max_pos_x']),
                'max_position_y_soll': safe_round(stats_result['max_pos_y']),
                'max_position_z_soll': safe_round(stats_result['max_pos_z']),
                'min_orientation_qw_soll': safe_round(stats_result['min_qw']),
                'min_orientation_qx_soll': safe_round(stats_result['min_qx']),
                'min_orientation_qy_soll': safe_round(stats_result['min_qy']),
                'min_orientation_qz_soll': safe_round(stats_result['min_qz']),
                'max_orientation_qw_soll': safe_round(stats_result['max_qw']),
                'max_orientation_qx_soll': safe_round(stats_result['max_qx']),
                'max_orientation_qy_soll': safe_round(stats_result['max_qy']),
                'max_orientation_qz_soll': safe_round(stats_result['max_qz']),
                'min_twist_ist': safe_round(stats_result['min_twist']),
                'max_twist_ist': safe_round(stats_result['max_twist']),
                'median_twist_ist': safe_round(stats_result['median_twist']),
                'std_twist_ist': safe_round(stats_result['std_twist']),
                'min_acceleration_ist': safe_round(stats_result['min_accel']),
                'max_acceleration_ist': safe_round(stats_result['max_accel']),
                'median_acceleration_ist': safe_round(stats_result['median_accel']),
                'std_acceleration_ist': safe_round(stats_result['std_accel']),
                'min_states_joint_1': safe_round(stats_result['min_joint_1']),
                'min_states_joint_2': safe_round(stats_result['min_joint_2']),
                'min_states_joint_3': safe_round(stats_result['min_joint_3']),
                'min_states_joint_4': safe_round(stats_result['min_joint_4']),
                'min_states_joint_5': safe_round(stats_result['min_joint_5']),
                'min_states_joint_6': safe_round(stats_result['min_joint_6']),
                'max_states_joint_1': safe_round(stats_result['max_joint_1']),
                'max_states_joint_2': safe_round(stats_result['max_joint_2']),
                'max_states_joint_3': safe_round(stats_result['max_joint_3']),
                'max_states_joint_4': safe_round(stats_result['max_joint_4']),
                'max_states_joint_5': safe_round(stats_result['max_joint_5']),
                'max_states_joint_6': safe_round(stats_result['max_joint_6'])
            }

        except Exception as e:
            logger.error(f"Fehler bei Segment {segment_id} in bahn_id {bahn_id}: {e}")
            return None

    async def process_single_bahn(self, bahn_id: str) -> Dict:
        """Verarbeitet eine einzelne Bahn und gibt Statistiken zurück"""
        result = {
            'bahn_id': bahn_id,
            'segments_processed': 0,
            'total_row_added': False,
            'success': False,
            'error': None
        }

        async with self.db_pool.acquire() as conn:
            try:
                # Bahn-Info laden (für Weight und Duration)
                bahn_info_query = """
                                  SELECT weight, start_time, end_time
                                  FROM robotervermessung.bewegungsdaten.bahn_info
                                  WHERE bahn_id = $1 \
                                  """
                bahn_info_rows = await conn.fetch(bahn_info_query, bahn_id)

                if not bahn_info_rows:
                    result['error'] = 'Bahn nicht gefunden in bahn_info'
                    return result

                bahn_info = bahn_info_rows[0]
                weight = bahn_info['weight']

                # Gesamtdauer berechnen
                total_duration = 0.0
                if bahn_info['start_time'] and bahn_info['end_time']:
                    try:
                        start_time = bahn_info['start_time']
                        end_time = bahn_info['end_time']
                        if isinstance(start_time, str):
                            start_time = datetime.fromisoformat(start_time)
                        if isinstance(end_time, str):
                            end_time = datetime.fromisoformat(end_time)
                        total_duration = (end_time - start_time).total_seconds()
                    except Exception as e:
                        logger.warning(f"Fehler bei Duration-Berechnung für bahn_id {bahn_id}: {e}")

                # Segment-IDs ermitteln
                segments_query = """
                                 SELECT DISTINCT segment_id
                                 FROM robotervermessung.bewegungsdaten.bahn_position_soll
                                 WHERE bahn_id = $1
                                 ORDER BY segment_id \
                                 """
                segment_rows = await conn.fetch(segments_query, bahn_id)

                if not segment_rows:
                    result['error'] = 'Keine Segmente gefunden'
                    return result

                segment_ids = [row['segment_id'] for row in segment_rows]
                batch_data = []
                segment_movement_types = []

                # Jedes Segment verarbeiten
                for segment_id in segment_ids:
                    segment_metadata = await self.calculate_segment_metadata(conn, bahn_id, segment_id)
                    if segment_metadata:
                        segment_metadata['weight'] = weight
                        batch_data.append(segment_metadata)
                        segment_movement_types.append(segment_metadata['movement_type'])
                        result['segments_processed'] += 1

                # Gesamtbahn-Zeile erstellen
                if segment_movement_types and batch_data:
                    total_movement_string = ''.join([mt[0].lower() for mt in segment_movement_types])
                    total_length = sum([row['length'] for row in batch_data])

                    # Gesamtstatistiken für Position berechnen
                    total_pos_query = """
                                      SELECT MIN(x_soll) as min_pos_x,
                                             MAX(x_soll) as max_pos_x,
                                             MIN(y_soll) as min_pos_y,
                                             MAX(y_soll) as max_pos_y,
                                             MIN(z_soll) as min_pos_z,
                                             MAX(z_soll) as max_pos_z
                                      FROM robotervermessung.bewegungsdaten.bahn_position_soll
                                      WHERE bahn_id = $1 \
                                      """
                    total_pos_rows = await conn.fetch(total_pos_query, bahn_id)

                    if total_pos_rows:
                        total_pos = total_pos_rows[0]

                        # Gesamtrichtung berechnen (erste zu letzter Position)
                        first_pos_query = """
                                          SELECT x_soll, y_soll, z_soll
                                          FROM robotervermessung.bewegungsdaten.bahn_position_soll
                                          WHERE bahn_id = $1
                                          ORDER BY segment_id, timestamp
                                              LIMIT 1 \
                                          """
                        last_pos_query = """
                                         SELECT x_soll, y_soll, z_soll
                                         FROM robotervermessung.bewegungsdaten.bahn_position_soll
                                         WHERE bahn_id = $1
                                         ORDER BY segment_id DESC, timestamp DESC
                                             LIMIT 1 \
                                         """

                        first_pos_rows = await conn.fetch(first_pos_query, bahn_id)
                        last_pos_rows = await conn.fetch(last_pos_query, bahn_id)

                        if first_pos_rows and last_pos_rows:
                            first_pos = first_pos_rows[0]
                            last_pos = last_pos_rows[0]

                            dx = last_pos['x_soll'] - first_pos['x_soll']
                            dy = last_pos['y_soll'] - first_pos['y_soll']
                            dz = last_pos['z_soll'] - first_pos['z_soll']

                            total_dir_length = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
                            if total_dir_length > 0:
                                total_dir_x = dx / total_dir_length
                                total_dir_y = dy / total_dir_length
                                total_dir_z = dz / total_dir_length
                            else:
                                total_dir_x = total_dir_y = total_dir_z = 0.0

                            # Orientation Gesamtstatistiken
                            orient_total_query = """
                                                 SELECT MIN(qw_soll) as min_qw, \
                                                        MAX(qw_soll) as max_qw,
                                                        MIN(qx_soll) as min_qx, \
                                                        MAX(qx_soll) as max_qx,
                                                        MIN(qy_soll) as min_qy, \
                                                        MAX(qy_soll) as max_qy,
                                                        MIN(qz_soll) as min_qz, \
                                                        MAX(qz_soll) as max_qz
                                                 FROM robotervermessung.bewegungsdaten.bahn_orientation_soll
                                                 WHERE bahn_id = $1 \
                                                 """
                            orient_total_rows = await conn.fetch(orient_total_query, bahn_id)
                            orient_total = dict(orient_total_rows[0]) if orient_total_rows else {}

                            # Twist Gesamtstatistiken
                            twist_total_query = """
                                                SELECT MIN(tcp_speed_ist)    as min_twist, \
                                                       MAX(tcp_speed_ist)    as max_twist,
                                                       AVG(tcp_speed_ist)    as median_twist, \
                                                       STDDEV(tcp_speed_ist) as std_twist
                                                FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                                                WHERE bahn_id = $1 \
                                                """
                            twist_total_rows = await conn.fetch(twist_total_query, bahn_id)
                            twist_total = dict(twist_total_rows[0]) if twist_total_rows else {}

                            # Acceleration Gesamtstatistiken
                            accel_total_query = """
                                                SELECT MIN(tcp_accel_ist)    as min_accel, \
                                                       MAX(tcp_accel_ist)    as max_accel,
                                                       AVG(tcp_accel_ist)    as median_accel, \
                                                       STDDEV(tcp_accel_ist) as std_accel
                                                FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                                                WHERE bahn_id = $1 \
                                                """
                            accel_total_rows = await conn.fetch(accel_total_query, bahn_id)
                            accel_total = dict(accel_total_rows[0]) if accel_total_rows else {}

                            # Joint States Gesamtstatistiken
                            joint_total_query = """
                                                SELECT MIN(joint_1) as min_joint_1, \
                                                       MAX(joint_1) as max_joint_1,
                                                       MIN(joint_2) as min_joint_2, \
                                                       MAX(joint_2) as max_joint_2,
                                                       MIN(joint_3) as min_joint_3, \
                                                       MAX(joint_3) as max_joint_3,
                                                       MIN(joint_4) as min_joint_4, \
                                                       MAX(joint_4) as max_joint_4,
                                                       MIN(joint_5) as min_joint_5, \
                                                       MAX(joint_5) as max_joint_5,
                                                       MIN(joint_6) as min_joint_6, \
                                                       MAX(joint_6) as max_joint_6
                                                FROM robotervermessung.bewegungsdaten.bahn_joint_states
                                                WHERE bahn_id = $1 \
                                                """
                            joint_total_rows = await conn.fetch(joint_total_query, bahn_id)
                            joint_total = dict(joint_total_rows[0]) if joint_total_rows else {}

                            def safe_round(value, decimals=2):
                                return round(float(value), decimals) if value is not None else None

                            # Gesamtbahn-Metadaten erstellen
                            total_metadata = {
                                'bahn_id': bahn_id,
                                'segment_id': bahn_id,  # Gesamtbahn hat segment_id = bahn_id
                                'movement_type': total_movement_string,
                                'duration': round(total_duration, 2),
                                'weight': weight,
                                'length': round(total_length, 2),
                                'direction_x': round(total_dir_x, 2),
                                'direction_y': round(total_dir_y, 2),
                                'direction_z': round(total_dir_z, 2),
                                'min_position_x_soll': safe_round(total_pos['min_pos_x']),
                                'min_position_y_soll': safe_round(total_pos['min_pos_y']),
                                'min_position_z_soll': safe_round(total_pos['min_pos_z']),
                                'max_position_x_soll': safe_round(total_pos['max_pos_x']),
                                'max_position_y_soll': safe_round(total_pos['max_pos_y']),
                                'max_position_z_soll': safe_round(total_pos['max_pos_z']),
                                'min_orientation_qw_soll': safe_round(orient_total.get('min_qw')),
                                'min_orientation_qx_soll': safe_round(orient_total.get('min_qx')),
                                'min_orientation_qy_soll': safe_round(orient_total.get('min_qy')),
                                'min_orientation_qz_soll': safe_round(orient_total.get('min_qz')),
                                'max_orientation_qw_soll': safe_round(orient_total.get('max_qw')),
                                'max_orientation_qx_soll': safe_round(orient_total.get('max_qx')),
                                'max_orientation_qy_soll': safe_round(orient_total.get('max_qy')),
                                'max_orientation_qz_soll': safe_round(orient_total.get('max_qz')),
                                'min_twist_ist': safe_round(twist_total.get('min_twist')),
                                'max_twist_ist': safe_round(twist_total.get('max_twist')),
                                'median_twist_ist': safe_round(twist_total.get('median_twist')),
                                'std_twist_ist': safe_round(twist_total.get('std_twist')),
                                'min_acceleration_ist': safe_round(accel_total.get('min_accel')),
                                'max_acceleration_ist': safe_round(accel_total.get('max_accel')),
                                'median_acceleration_ist': safe_round(accel_total.get('median_accel')),
                                'std_acceleration_ist': safe_round(accel_total.get('std_accel')),
                                'min_states_joint_1': safe_round(joint_total.get('min_joint_1')),
                                'min_states_joint_2': safe_round(joint_total.get('min_joint_2')),
                                'min_states_joint_3': safe_round(joint_total.get('min_joint_3')),
                                'min_states_joint_4': safe_round(joint_total.get('min_joint_4')),
                                'min_states_joint_5': safe_round(joint_total.get('min_joint_5')),
                                'min_states_joint_6': safe_round(joint_total.get('min_joint_6')),
                                'max_states_joint_1': safe_round(joint_total.get('max_joint_1')),
                                'max_states_joint_2': safe_round(joint_total.get('max_joint_2')),
                                'max_states_joint_3': safe_round(joint_total.get('max_joint_3')),
                                'max_states_joint_4': safe_round(joint_total.get('max_joint_4')),
                                'max_states_joint_5': safe_round(joint_total.get('max_joint_5')),
                                'max_states_joint_6': safe_round(joint_total.get('max_joint_6'))
                            }

                            batch_data.append(total_metadata)
                            result['total_row_added'] = True

                # Batch Insert durchführen
                if batch_data:
                    await self.insert_metadata_batch(conn, batch_data)
                    result['success'] = True

            except Exception as e:
                logger.error(f"Fehler bei Verarbeitung bahn_id {bahn_id}: {e}")
                result['error'] = str(e)

        return result

    async def insert_metadata_batch(self, conn: asyncpg.Connection, batch_data: List[Dict]):
        """Führt Batch Insert für Metadaten durch"""
        if not batch_data:
            return

        # Prepare INSERT statement mit CAST für numerische Präzision
        insert_sql = """
                     INSERT INTO robotervermessung.bewegungsdaten.bahn_meta (bahn_id, segment_id, movement_type, \
                                                                             duration, weight, length, \
                                                                             direction_x, direction_y, direction_z, \
                                                                             min_position_x_soll, min_position_y_soll, \
                                                                             min_position_z_soll, \
                                                                             max_position_x_soll, max_position_y_soll, \
                                                                             max_position_z_soll, \
                                                                             min_orientation_qw_soll, \
                                                                             min_orientation_qx_soll, \
                                                                             min_orientation_qy_soll, \
                                                                             min_orientation_qz_soll, \
                                                                             max_orientation_qw_soll, \
                                                                             max_orientation_qx_soll, \
                                                                             max_orientation_qy_soll, \
                                                                             max_orientation_qz_soll, \
                                                                             min_twist_ist, max_twist_ist, \
                                                                             median_twist_ist, std_twist_ist, \
                                                                             min_acceleration_ist, max_acceleration_ist, \
                                                                             median_acceleration_ist, \
                                                                             std_acceleration_ist, \
                                                                             min_states_joint_1, min_states_joint_2, \
                                                                             min_states_joint_3, min_states_joint_4, \
                                                                             min_states_joint_5, min_states_joint_6, \
                                                                             max_states_joint_1, max_states_joint_2, \
                                                                             max_states_joint_3, max_states_joint_4, \
                                                                             max_states_joint_5, max_states_joint_6) \
                     VALUES ($1, $2, $3, \
                             CAST($4 AS NUMERIC(10, 3)), CAST($5 AS NUMERIC(10, 3)), CAST($6 AS NUMERIC(10, 3)), \
                             CAST($7 AS NUMERIC(10, 3)), CAST($8 AS NUMERIC(10, 3)), CAST($9 AS NUMERIC(10, 3)), \
                             CAST($10 AS NUMERIC(10, 3)), CAST($11 AS NUMERIC(10, 3)), CAST($12 AS NUMERIC(10, 3)), \
                             CAST($13 AS NUMERIC(10, 3)), CAST($14 AS NUMERIC(10, 3)), CAST($15 AS NUMERIC(10, 3)), \
                             CAST($16 AS NUMERIC(10, 3)), CAST($17 AS NUMERIC(10, 3)), CAST($18 AS NUMERIC(10, 3)), \
                             CAST($19 AS NUMERIC(10, 3)), \
                             CAST($20 AS NUMERIC(10, 3)), CAST($21 AS NUMERIC(10, 3)), CAST($22 AS NUMERIC(10, 3)), \
                             CAST($23 AS NUMERIC(10, 3)), \
                             CAST($24 AS NUMERIC(10, 3)), CAST($25 AS NUMERIC(10, 3)), CAST($26 AS NUMERIC(10, 3)), \
                             CAST($27 AS NUMERIC(10, 3)), \
                             CAST($28 AS NUMERIC(10, 3)), CAST($29 AS NUMERIC(10, 3)), CAST($30 AS NUMERIC(10, 3)), \
                             CAST($31 AS NUMERIC(10, 3)), \
                             CAST($32 AS NUMERIC(10, 3)), CAST($33 AS NUMERIC(10, 3)), CAST($34 AS NUMERIC(10, 3)), \
                             CAST($35 AS NUMERIC(10, 3)), CAST($36 AS NUMERIC(10, 3)), CAST($37 AS NUMERIC(10, 3)), \
                             CAST($38 AS NUMERIC(10, 3)), CAST($39 AS NUMERIC(10, 3)), CAST($40 AS NUMERIC(10, 3)), \
                             CAST($41 AS NUMERIC(10, 3)), CAST($42 AS NUMERIC(10, 3)), CAST($43 AS NUMERIC(10, 3)))
                     """

        # Konvertiere zu Liste von Tupeln (ohne zusätzliche Rundung)
        rows = []
        for metadata in batch_data:
            row = (
                metadata['bahn_id'], metadata['segment_id'], metadata['movement_type'],
                metadata['duration'], metadata['weight'], metadata['length'],
                metadata['direction_x'], metadata['direction_y'], metadata['direction_z'],
                metadata['min_position_x_soll'], metadata['min_position_y_soll'], metadata['min_position_z_soll'],
                metadata['max_position_x_soll'], metadata['max_position_y_soll'], metadata['max_position_z_soll'],
                metadata['min_orientation_qw_soll'], metadata['min_orientation_qx_soll'],
                metadata['min_orientation_qy_soll'], metadata['min_orientation_qz_soll'],
                metadata['max_orientation_qw_soll'], metadata['max_orientation_qx_soll'],
                metadata['max_orientation_qy_soll'], metadata['max_orientation_qz_soll'],
                metadata['min_twist_ist'], metadata['max_twist_ist'], metadata['median_twist_ist'],
                metadata['std_twist_ist'],
                metadata['min_acceleration_ist'], metadata['max_acceleration_ist'], metadata['median_acceleration_ist'],
                metadata['std_acceleration_ist'],
                metadata['min_states_joint_1'], metadata['min_states_joint_2'], metadata['min_states_joint_3'],
                metadata['min_states_joint_4'], metadata['min_states_joint_5'], metadata['min_states_joint_6'],
                metadata['max_states_joint_1'], metadata['max_states_joint_2'], metadata['max_states_joint_3'],
                metadata['max_states_joint_4'], metadata['max_states_joint_5'], metadata['max_states_joint_6']
            )
            rows.append(row)

        # Batch Insert ausführen
        await conn.executemany(insert_sql, rows)