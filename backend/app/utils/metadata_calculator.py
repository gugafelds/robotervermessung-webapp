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
                    ORDER BY bi.bahn_id::text \
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

    def detect_movement_type(self, x_data: np.ndarray, y_data: np.ndarray, z_data: np.ndarray,
                             timestamps: np.ndarray) -> str:
        """
        Erkennt den Bewegungstyp (linear, circular, spline) basierend auf 3D-Positionsdaten
        """
        if len(x_data) < 3:
            return "linear"

        try:
            positions = np.column_stack([x_data, y_data, z_data])
            n_points = len(positions)

            if n_points < 4:
                return "linear"

            # LINEAR TEST - Prüfe ob alle Punkte auf einer Geraden liegen
            start_point = positions[0]
            end_point = positions[-1]
            main_direction = end_point - start_point
            main_distance = np.linalg.norm(main_direction)

            if main_distance < 1e-6:
                return "linear"

            main_direction_norm = main_direction / main_distance

            # Prüfe Abstand aller Zwischenpunkte zur Hauptgeraden
            max_deviation = 0.0
            for i in range(1, n_points - 1):
                point_vector = positions[i] - start_point
                projection_length = np.dot(point_vector, main_direction_norm)
                projection_point = start_point + projection_length * main_direction_norm
                deviation = np.linalg.norm(positions[i] - projection_point)
                max_deviation = max(max_deviation, deviation)

            relative_deviation = max_deviation / main_distance

            # CIRCULAR TEST - Prüfe Kreisbogen
            curvature_radii = []
            for i in range(n_points - 2):
                p1, p2, p3 = positions[i], positions[i + 1], positions[i + 2]
                v1 = p2 - p1
                v2 = p3 - p2
                d1 = np.linalg.norm(v1)
                d2 = np.linalg.norm(v2)

                if d1 < 1e-6 or d2 < 1e-6:
                    continue

                cos_angle = np.dot(v1, v2) / (d1 * d2)
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.arccos(cos_angle)

                if angle > 1e-6:
                    chord_length = np.linalg.norm(p3 - p1)
                    radius = chord_length / (2 * np.sin(angle / 2))
                    curvature_radii.append(radius)

            # ENTSCHEIDUNGSLOGIK
            if relative_deviation < 0.02:  # 2% der Gesamtlänge
                return "linear"

            # Circular: Konstanter Krümmungsradius
            if curvature_radii:
                radii_array = np.array(curvature_radii)
                mean_radius = np.mean(radii_array)
                radius_std = np.std(radii_array)

                if mean_radius > 0 and radius_std / mean_radius < 0.3:
                    total_angle = 0
                    for i in range(n_points - 2):
                        p1, p2, p3 = positions[i], positions[i + 1], positions[i + 2]
                        v1 = p2 - p1
                        v2 = p3 - p2
                        d1, d2 = np.linalg.norm(v1), np.linalg.norm(v2)
                        if d1 > 1e-6 and d2 > 1e-6:
                            cos_angle = np.clip(np.dot(v1, v2) / (d1 * d2), -1, 1)
                            total_angle += np.arccos(cos_angle)

                    if total_angle > np.pi / 6:  # 30 Grad
                        return "circular"

            # Fallback basierend auf Abweichung
            if relative_deviation > 0.1:
                return "spline"
            elif relative_deviation > 0.05:
                return "circular"
            else:
                return "linear"

        except Exception as e:
            logger.warning(f"Fehler bei Movement-Type-Erkennung: {e}")
            return "linear"

    async def calculate_segment_metadata(self, conn: asyncpg.Connection, bahn_id: str, segment_id: str) -> Optional[
        Dict]:
        """Berechnet Metadaten für ein einzelnes Segment"""
        try:
            # Position-Daten für Segment laden
            pos_query = """
                        SELECT x_soll, \
                               y_soll, \
                               z_soll, timestamp, MIN (x_soll) OVER() as min_pos_x, MAX (x_soll) OVER() as max_pos_x, MIN (y_soll) OVER() as min_pos_y, MAX (y_soll) OVER() as max_pos_y, MIN (z_soll) OVER() as min_pos_z, MAX (z_soll) OVER() as max_pos_z, MIN (timestamp) OVER() as min_timestamp, MAX (timestamp) OVER() as max_timestamp
                        FROM robotervermessung.bewegungsdaten.bahn_position_soll
                        WHERE bahn_id = $1 \
                          AND segment_id = $2
                        ORDER BY timestamp \
                        """
            pos_rows = await conn.fetch(pos_query, bahn_id, segment_id)

            if not pos_rows:
                return None

            # Konvertiere zu numpy arrays für Movement-Type-Erkennung
            x_data = np.array([row['x_soll'] for row in pos_rows])
            y_data = np.array([row['y_soll'] for row in pos_rows])
            z_data = np.array([row['z_soll'] for row in pos_rows])
            timestamps = np.array([row['timestamp'] for row in pos_rows])

            movement_type = self.detect_movement_type(x_data, y_data, z_data, timestamps)

            # Statistiken aus erster Zeile (wegen OVER())
            first_row = pos_rows[0]
            last_row = pos_rows[-1]

            # Segment Duration berechnen
            segment_duration = 0.0
            try:
                min_timestamp = first_row['min_timestamp']
                max_timestamp = first_row['max_timestamp']

                if min_timestamp and max_timestamp:
                    min_ts_int = int(float(min_timestamp))
                    max_ts_int = int(float(max_timestamp))
                    diff_ns = max_ts_int - min_ts_int
                    segment_duration = max(diff_ns / 1_000_000_000.0, 0.0)
            except Exception as e:
                logger.warning(f"Fehler bei Duration-Berechnung Segment {segment_id}: {e}")

            # Richtung und Länge berechnen
            first_x, first_y, first_z = first_row['x_soll'], first_row['y_soll'], first_row['z_soll']
            last_x, last_y, last_z = last_row['x_soll'], last_row['y_soll'], last_row['z_soll']

            dx = last_x - first_x
            dy = last_y - first_y
            dz = last_z - first_z
            length = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

            if length > 0:
                direction_x = dx / length
                direction_y = dy / length
                direction_z = dz / length
            else:
                direction_x = direction_y = direction_z = 0.0

            # Orientation-Daten laden
            orient_query = """
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
                             AND segment_id = $2 \
                           """
            orient_rows = await conn.fetch(orient_query, bahn_id, segment_id)
            orient_data = dict(orient_rows[0]) if orient_rows else {}

            # Twist-Daten laden
            twist_query = """
                          SELECT ROUND(MIN(tcp_speed_ist)::numeric, 3)    as min_twist,
                                 ROUND(MAX(tcp_speed_ist)::numeric, 3)    as max_twist,
                                 ROUND(AVG(tcp_speed_ist)::numeric, 3)    as median_twist,
                                 ROUND(STDDEV(tcp_speed_ist)::numeric, 3) as std_twist
                          FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2 \
                          """
            twist_rows = await conn.fetch(twist_query, bahn_id, segment_id)
            twist_data = dict(twist_rows[0]) if twist_rows else {}

            # Acceleration-Daten laden
            accel_query = """
                          SELECT MIN(tcp_accel_ist)    as min_accel, \
                                 MAX(tcp_accel_ist)    as max_accel,
                                 AVG(tcp_accel_ist)    as median_accel, \
                                 STDDEV(tcp_accel_ist) as std_accel
                          FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                          WHERE bahn_id = $1 \
                            AND segment_id = $2 \
                          """
            accel_rows = await conn.fetch(accel_query, bahn_id, segment_id)
            accel_data = dict(accel_rows[0]) if accel_rows else {}

            # Joint States laden
            joint_query = """
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
                            AND segment_id = $2 \
                          """
            joint_rows = await conn.fetch(joint_query, bahn_id, segment_id)
            joint_data = dict(joint_rows[0]) if joint_rows else {}

            def safe_round(value, decimals):
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
                'min_position_x_soll': safe_round(first_row['min_pos_x'], 3),
                'min_position_y_soll': safe_round(first_row['min_pos_y'], 3),
                'min_position_z_soll': safe_round(first_row['min_pos_z'], 3),
                'max_position_x_soll': safe_round(first_row['max_pos_x'], 3),
                'max_position_y_soll': safe_round(first_row['max_pos_y'], 3),
                'max_position_z_soll': safe_round(first_row['max_pos_z'], 3),
                'min_orientation_qw_soll': safe_round(orient_data.get('min_qw'), 3),
                'min_orientation_qx_soll': safe_round(orient_data.get('min_qx'), 3),
                'min_orientation_qy_soll': safe_round(orient_data.get('min_qy'), 3),
                'min_orientation_qz_soll': safe_round(orient_data.get('min_qz'), 3),
                'max_orientation_qw_soll': safe_round(orient_data.get('max_qw'), 3),
                'max_orientation_qx_soll': safe_round(orient_data.get('max_qx'), 3),
                'max_orientation_qy_soll': safe_round(orient_data.get('max_qy'), 3),
                'max_orientation_qz_soll': safe_round(orient_data.get('max_qz'), 3),
                'min_twist_ist': safe_round(twist_data.get('min_twist'), 3),
                'max_twist_ist': safe_round(twist_data.get('max_twist'), 3),
                'median_twist_ist': safe_round(twist_data.get('median_twist'), 3),
                'std_twist_ist': safe_round(twist_data.get('std_twist'), 3),
                'min_acceleration_ist': safe_round(accel_data.get('min_accel'), 3),
                'max_acceleration_ist': safe_round(accel_data.get('max_accel'), 3),
                'median_acceleration_ist': safe_round(accel_data.get('median_accel'), 3),
                'std_acceleration_ist': safe_round(accel_data.get('std_accel'), 3),
                'min_states_joint_1': safe_round(joint_data.get('min_joint_1'), 3),
                'min_states_joint_2': safe_round(joint_data.get('min_joint_2'), 3),
                'min_states_joint_3': safe_round(joint_data.get('min_joint_3'), 3),
                'min_states_joint_4': safe_round(joint_data.get('min_joint_4'), 3),
                'min_states_joint_5': safe_round(joint_data.get('min_joint_5'), 3),
                'min_states_joint_6': safe_round(joint_data.get('min_joint_6'), 3),
                'max_states_joint_1': safe_round(joint_data.get('max_joint_1'), 3),
                'max_states_joint_2': safe_round(joint_data.get('max_joint_2'), 3),
                'max_states_joint_3': safe_round(joint_data.get('max_joint_3'), 3),
                'max_states_joint_4': safe_round(joint_data.get('max_joint_4'), 3),
                'max_states_joint_5': safe_round(joint_data.get('max_joint_5'), 3),
                'max_states_joint_6': safe_round(joint_data.get('max_joint_6'), 3)
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