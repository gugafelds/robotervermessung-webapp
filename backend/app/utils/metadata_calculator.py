import asyncio

import asyncpg
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

SEGMENT_CONNECTION_SEMAPHORE = asyncio.Semaphore(50)


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

    @staticmethod
    def safe_float(value, default=0.0):
        """Konvertiert zu float, gibt default zurück wenn None"""
        return float(value) if value is not None else default

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

    def detect_movement_type(self, x_data, y_data, z_data) -> str:
        """Erkennt Movement-Type - VEKTORISIERT"""
        try:
            if len(x_data) < 3:
                return "linear"

            # Alle Punkte als Matrix
            points = np.column_stack([x_data, y_data, z_data])

            # Vektorisierte Distanz-Berechnung
            deltas = np.diff(points, axis=0)
            distances = np.linalg.norm(deltas, axis=1)
            path_length = float(np.sum(distances))

            if path_length < 1e-6:
                return "linear"

            # Direkte Distanz
            direct_distance = float(np.linalg.norm(points[-1] - points[0]))
            ratio = direct_distance / path_length

            # Geschlossene Form Check
            if ratio < 0.1:
                # Mittelpunkt
                center = np.mean(points, axis=0)
                # Radien (vektorisiert!)
                radii = np.linalg.norm(points - center, axis=1)
                mean_radius = np.mean(radii)

                if mean_radius > 0:
                    radius_variance = np.std(radii) / mean_radius
                    if radius_variance < 0.3:
                        return "circular"
                return "spline"

            # Offene Form
            if ratio > 0.95:
                return "linear"
            elif ratio > 0.3:
                return "circular"
            else:
                return "spline"

        except Exception as e:
            logger.warning(f"Fehler bei Movement-Type-Erkennung: {e}")
            return "linear"

    async def process_single_bahn_in_memory(self, bahn_id: str) -> Dict:
        """
        Verarbeitet eine einzelne Bahn komplett in-memory
        Gibt Liste von Metadaten zurück (keine DB-Writes hier!)
        """
        result = {
            'bahn_id': bahn_id,
            'metadata': [],  # Liste aller Metadaten-Rows
            'segments_processed': 0,
            'error': None
        }

        async with self.db_pool.acquire() as conn:
            try:
                # 1. Hole ALLE Daten für diese Bahn in EINEM Durchgang
                bahn_data = await self._fetch_all_bahn_data(conn, bahn_id)

                if not bahn_data:
                    result['error'] = 'Keine Daten gefunden'
                    return result

                # 2. Verarbeite alles IN MEMORY (keine DB mehr!)
                metadata_rows = self._calculate_all_metadata_in_memory(bahn_id, bahn_data)

                result['metadata'] = metadata_rows
                result['segments_processed'] = len(metadata_rows) - 1  # -1 für Gesamtbahn-Zeile

            except Exception as e:
                logger.error(f"Fehler bei Verarbeitung bahn_id {bahn_id}: {e}")
                result['error'] = str(e)

        return result

    async def _fetch_all_bahn_data(self, conn: asyncpg.Connection, bahn_id: str) -> Dict:
        """
        Holt ALLE benötigten Daten für eine Bahn in EINEM Durchgang
        """
        # Bahn Info
        bahn_info_query = """
                          SELECT weight, start_time, end_time
                          FROM robotervermessung.bewegungsdaten.bahn_info
                          WHERE bahn_id = $1 \
                          """
        bahn_info = await conn.fetchrow(bahn_info_query, bahn_id)

        if not bahn_info:
            return None

        # Alle Segmente mit Position-Daten
        segments_query = """
                         SELECT segment_id, \
                                array_agg(x_soll ORDER BY timestamp) as x_data, \
                                array_agg(y_soll ORDER BY timestamp) as y_data, \
                                array_agg(z_soll ORDER BY timestamp) as z_data, \
                                MIN(timestamp)                       as min_timestamp, \
                                MAX(timestamp)                       as max_timestamp, \
                                MIN(x_soll)                          as min_x, \
                                MAX(x_soll)                          as max_x, \
                                MIN(y_soll)                          as min_y, \
                                MAX(y_soll)                          as max_y, \
                                MIN(z_soll)                          as min_z, \
                                MAX(z_soll)                          as max_z
                         FROM robotervermessung.bewegungsdaten.bahn_position_soll
                         WHERE bahn_id = $1
                         GROUP BY segment_id
                         ORDER BY segment_id \
                         """
        segments = await conn.fetch(segments_query, bahn_id)

        # Orientation Stats pro Segment
        orientation_query = """
                            SELECT segment_id, \
                                   MIN(qw_soll) as min_qw, \
                                   MAX(qw_soll) as max_qw, \
                                   MIN(qx_soll) as min_qx, \
                                   MAX(qx_soll) as max_qx, \
                                   MIN(qy_soll) as min_qy, \
                                   MAX(qy_soll) as max_qy, \
                                   MIN(qz_soll) as min_qz, \
                                   MAX(qz_soll) as max_qz
                            FROM robotervermessung.bewegungsdaten.bahn_orientation_soll
                            WHERE bahn_id = $1
                            GROUP BY segment_id \
                            """
        orientations = await conn.fetch(orientation_query, bahn_id)

        # Twist Stats pro Segment
        twist_query = """
                      SELECT segment_id, \
                             MIN(tcp_speed_ist) as min_twist, \
                             MAX(tcp_speed_ist) as max_twist, \
                             PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY tcp_speed_ist) as median_twist,
                STDDEV(tcp_speed_ist) as std_twist
                      FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                      WHERE bahn_id = $1
                      GROUP BY segment_id \
                      """
        twists = await conn.fetch(twist_query, bahn_id)

        # Acceleration Stats pro Segment
        accel_query = """
                      SELECT segment_id, \
                             MIN(tcp_accel_ist) as min_accel, \
                             MAX(tcp_accel_ist) as max_accel, \
                             PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY tcp_accel_ist) as median_accel,
                STDDEV(tcp_accel_ist) as std_accel
                      FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                      WHERE bahn_id = $1
                      GROUP BY segment_id \
                      """
        accels = await conn.fetch(accel_query, bahn_id)

        # Joint Stats pro Segment
        joint_query = """
                      SELECT segment_id, \
                             MIN(joint_1) as min_joint_1, \
                             MAX(joint_1) as max_joint_1, \
                             MIN(joint_2) as min_joint_2, \
                             MAX(joint_2) as max_joint_2, \
                             MIN(joint_3) as min_joint_3, \
                             MAX(joint_3) as max_joint_3, \
                             MIN(joint_4) as min_joint_4, \
                             MAX(joint_4) as max_joint_4, \
                             MIN(joint_5) as min_joint_5, \
                             MAX(joint_5) as max_joint_5, \
                             MIN(joint_6) as min_joint_6, \
                             MAX(joint_6) as max_joint_6
                      FROM robotervermessung.bewegungsdaten.bahn_joint_states
                      WHERE bahn_id = $1
                      GROUP BY segment_id \
                      """
        joints = await conn.fetch(joint_query, bahn_id)

        return {
            'bahn_info': bahn_info,
            'segments': segments,
            'orientations': {row['segment_id']: row for row in orientations},
            'twists': {row['segment_id']: row for row in twists},
            'accels': {row['segment_id']: row for row in accels},
            'joints': {row['segment_id']: row for row in joints}
        }

    def _calculate_all_metadata_in_memory(self, bahn_id: str, bahn_data: Dict) -> List[Dict]:
        """
        Berechnet alle Metadaten komplett in Python (keine DB!)
        OPTIMIERT: Vektorisierte Aggregationen
        """
        metadata_rows = []
        weight = bahn_data['bahn_info']['weight']

        # Berechne Gesamtdauer
        total_duration = 0.0
        if bahn_data['bahn_info']['start_time'] and bahn_data['bahn_info']['end_time']:
            try:
                start_time = bahn_data['bahn_info']['start_time']
                end_time = bahn_data['bahn_info']['end_time']
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                total_duration = (end_time - start_time).total_seconds()
            except Exception as e:
                logger.warning(f"Fehler bei Duration-Berechnung: {e}")

        # Verarbeite jedes Segment
        segment_movement_types = []
        total_length = 0.0

        for segment in bahn_data['segments']:
            segment_id = segment['segment_id']

            # Movement Type Detection (pure Python!)
            x_data = np.array(segment['x_data'])
            y_data = np.array(segment['y_data'])
            z_data = np.array(segment['z_data'])

            # Sample für Movement Type (direkt slicen - schneller!)
            step = max(1, len(x_data) // 20)
            x_sample = x_data[::step]
            y_sample = y_data[::step]
            z_sample = z_data[::step]

            movement_type = self.detect_movement_type(x_sample, y_sample, z_sample)
            segment_movement_types.append(movement_type)

            # Duration
            segment_duration = 0.0
            try:
                if segment['min_timestamp'] and segment['max_timestamp']:
                    min_ts = int(float(segment['min_timestamp']))
                    max_ts = int(float(segment['max_timestamp']))
                    segment_duration = max((max_ts - min_ts) / 1_000_000_000.0, 0.0)
            except:
                pass

            # Length und Direction (vektorisiert!)
            delta = np.array([x_data[-1] - x_data[0],
                              y_data[-1] - y_data[0],
                              z_data[-1] - z_data[0]])
            length = float(np.linalg.norm(delta))
            total_length += length

            direction = delta / length if length > 0 else np.zeros(3)
            direction_x, direction_y, direction_z = direction.tolist()

            # Hole Zusatzdaten
            orient = bahn_data['orientations'].get(segment_id, {})
            twist = bahn_data['twists'].get(segment_id, {})
            accel = bahn_data['accels'].get(segment_id, {})
            joint = bahn_data['joints'].get(segment_id, {})

            # Erstelle Metadaten-Row (mit safe_float!)
            metadata_rows.append({
                'bahn_id': bahn_id,
                'segment_id': segment_id,
                'movement_type': movement_type,
                'duration': segment_duration,
                'weight': weight,
                'length': length,
                'direction_x': direction_x,
                'direction_y': direction_y,
                'direction_z': direction_z,
                'min_position_x_soll': float(segment['min_x']),
                'min_position_y_soll': float(segment['min_y']),
                'min_position_z_soll': float(segment['min_z']),
                'max_position_x_soll': float(segment['max_x']),
                'max_position_y_soll': float(segment['max_y']),
                'max_position_z_soll': float(segment['max_z']),
                'min_orientation_qw_soll': self.safe_float(orient.get('min_qw')),
                'min_orientation_qx_soll': self.safe_float(orient.get('min_qx')),
                'min_orientation_qy_soll': self.safe_float(orient.get('min_qy')),
                'min_orientation_qz_soll': self.safe_float(orient.get('min_qz')),
                'max_orientation_qw_soll': self.safe_float(orient.get('max_qw')),
                'max_orientation_qx_soll': self.safe_float(orient.get('max_qx')),
                'max_orientation_qy_soll': self.safe_float(orient.get('max_qy')),
                'max_orientation_qz_soll': self.safe_float(orient.get('max_qz')),
                'min_twist_ist': self.safe_float(twist.get('min_twist')),
                'max_twist_ist': self.safe_float(twist.get('max_twist')),
                'median_twist_ist': self.safe_float(twist.get('median_twist')),
                'std_twist_ist': self.safe_float(twist.get('std_twist')),
                'min_acceleration_ist': self.safe_float(accel.get('min_accel')),
                'max_acceleration_ist': self.safe_float(accel.get('max_accel')),
                'median_acceleration_ist': self.safe_float(accel.get('median_accel')),
                'std_acceleration_ist': self.safe_float(accel.get('std_accel')),
                'min_states_joint_1': self.safe_float(joint.get('min_joint_1')),
                'min_states_joint_2': self.safe_float(joint.get('min_joint_2')),
                'min_states_joint_3': self.safe_float(joint.get('min_joint_3')),
                'min_states_joint_4': self.safe_float(joint.get('min_joint_4')),
                'min_states_joint_5': self.safe_float(joint.get('min_joint_5')),
                'min_states_joint_6': self.safe_float(joint.get('min_joint_6')),
                'max_states_joint_1': self.safe_float(joint.get('max_joint_1')),
                'max_states_joint_2': self.safe_float(joint.get('max_joint_2')),
                'max_states_joint_3': self.safe_float(joint.get('max_joint_3')),
                'max_states_joint_4': self.safe_float(joint.get('max_joint_4')),
                'max_states_joint_5': self.safe_float(joint.get('max_joint_5')),
                'max_states_joint_6': self.safe_float(joint.get('max_joint_6'))
            })

        # Gesamtbahn-Zeile erstellen
        if metadata_rows:
            total_movement_string = ''.join([mt[0].lower() for mt in segment_movement_types])

            # Aggregiere Min/Max über alle Segmente
            all_min_x = min(row['min_position_x_soll'] for row in metadata_rows)
            all_max_x = max(row['max_position_x_soll'] for row in metadata_rows)
            all_min_y = min(row['min_position_y_soll'] for row in metadata_rows)
            all_max_y = max(row['max_position_y_soll'] for row in metadata_rows)
            all_min_z = min(row['min_position_z_soll'] for row in metadata_rows)
            all_max_z = max(row['max_position_z_soll'] for row in metadata_rows)

            # Gesamtrichtung (erste Segment Start → letzte Segment Ende)
            first_seg = bahn_data['segments'][0]
            last_seg = bahn_data['segments'][-1]

            total_delta = np.array([
                last_seg['x_data'][-1] - first_seg['x_data'][0],
                last_seg['y_data'][-1] - first_seg['y_data'][0],
                last_seg['z_data'][-1] - first_seg['z_data'][0]
            ])
            total_dir_length = float(np.linalg.norm(total_delta))

            total_direction = total_delta / total_dir_length if total_dir_length > 0 else np.zeros(3)
            total_dir_x, total_dir_y, total_dir_z = total_direction.tolist()

            # OPTIMIERUNG 4: Vektorisierte Aggregation mit numpy
            orientation_data = np.array([
                [row['min_orientation_qw_soll'], row['min_orientation_qx_soll'],
                 row['min_orientation_qy_soll'], row['min_orientation_qz_soll'],
                 row['max_orientation_qw_soll'], row['max_orientation_qx_soll'],
                 row['max_orientation_qy_soll'], row['max_orientation_qz_soll']]
                for row in metadata_rows
            ])

            twist_data = np.array([
                [row['min_twist_ist'], row['max_twist_ist'],
                 row['median_twist_ist'], row['std_twist_ist']]
                for row in metadata_rows
            ])

            accel_data = np.array([
                [row['min_acceleration_ist'], row['max_acceleration_ist'],
                 row['median_acceleration_ist'], row['std_acceleration_ist']]
                for row in metadata_rows
            ])

            joint_data = np.array([
                [row['min_states_joint_1'], row['min_states_joint_2'], row['min_states_joint_3'],
                 row['min_states_joint_4'], row['min_states_joint_5'], row['min_states_joint_6'],
                 row['max_states_joint_1'], row['max_states_joint_2'], row['max_states_joint_3'],
                 row['max_states_joint_4'], row['max_states_joint_5'], row['max_states_joint_6']]
                for row in metadata_rows
            ])

            # Aggregiere Stats über alle Segmente (vektorisiert!)
            total_metadata = {
                'bahn_id': bahn_id,
                'segment_id': bahn_id,
                'movement_type': total_movement_string,
                'duration': total_duration,
                'weight': weight,
                'length': total_length,
                'direction_x': total_dir_x,
                'direction_y': total_dir_y,
                'direction_z': total_dir_z,
                'min_position_x_soll': all_min_x,
                'min_position_y_soll': all_min_y,
                'min_position_z_soll': all_min_z,
                'max_position_x_soll': all_max_x,
                'max_position_y_soll': all_max_y,
                'max_position_z_soll': all_max_z,
                # Vektorisierte Orientation Aggregation
                'min_orientation_qw_soll': float(np.min(orientation_data[:, 0])),
                'min_orientation_qx_soll': float(np.min(orientation_data[:, 1])),
                'min_orientation_qy_soll': float(np.min(orientation_data[:, 2])),
                'min_orientation_qz_soll': float(np.min(orientation_data[:, 3])),
                'max_orientation_qw_soll': float(np.max(orientation_data[:, 4])),
                'max_orientation_qx_soll': float(np.max(orientation_data[:, 5])),
                'max_orientation_qy_soll': float(np.max(orientation_data[:, 6])),
                'max_orientation_qz_soll': float(np.max(orientation_data[:, 7])),
                # Vektorisierte Twist Aggregation
                'min_twist_ist': float(np.min(twist_data[:, 0])),
                'max_twist_ist': float(np.max(twist_data[:, 1])),
                'median_twist_ist': float(np.median(twist_data[:, 2])),
                'std_twist_ist': float(np.mean(twist_data[:, 3])),
                # Vektorisierte Acceleration Aggregation
                'min_acceleration_ist': float(np.min(accel_data[:, 0])),
                'max_acceleration_ist': float(np.max(accel_data[:, 1])),
                'median_acceleration_ist': float(np.median(accel_data[:, 2])),
                'std_acceleration_ist': float(np.mean(accel_data[:, 3])),
                # Vektorisierte Joint Aggregation
                'min_states_joint_1': float(np.min(joint_data[:, 0])),
                'min_states_joint_2': float(np.min(joint_data[:, 1])),
                'min_states_joint_3': float(np.min(joint_data[:, 2])),
                'min_states_joint_4': float(np.min(joint_data[:, 3])),
                'min_states_joint_5': float(np.min(joint_data[:, 4])),
                'min_states_joint_6': float(np.min(joint_data[:, 5])),
                'max_states_joint_1': float(np.max(joint_data[:, 6])),
                'max_states_joint_2': float(np.max(joint_data[:, 7])),
                'max_states_joint_3': float(np.max(joint_data[:, 8])),
                'max_states_joint_4': float(np.max(joint_data[:, 9])),
                'max_states_joint_5': float(np.max(joint_data[:, 10])),
                'max_states_joint_6': float(np.max(joint_data[:, 11]))
            }

            metadata_rows.append(total_metadata)

        return metadata_rows

    async def batch_write_metadata(self, metadata_rows: List[Dict]):
        """
        Schreibt alle Metadaten in EINEM Batch mit COPY
        """
        if not metadata_rows:
            return

        async with self.db_pool.acquire() as conn:
            # Konvertiere zu Tupeln für COPY
            columns = [
                'bahn_id', 'segment_id', 'movement_type',
                'duration', 'weight', 'length',
                'direction_x', 'direction_y', 'direction_z',
                'min_position_x_soll', 'min_position_y_soll', 'min_position_z_soll',
                'max_position_x_soll', 'max_position_y_soll', 'max_position_z_soll',
                'min_orientation_qw_soll', 'min_orientation_qx_soll',
                'min_orientation_qy_soll', 'min_orientation_qz_soll',
                'max_orientation_qw_soll', 'max_orientation_qx_soll',
                'max_orientation_qy_soll', 'max_orientation_qz_soll',
                'min_twist_ist', 'max_twist_ist', 'median_twist_ist', 'std_twist_ist',
                'min_acceleration_ist', 'max_acceleration_ist',
                'median_acceleration_ist', 'std_acceleration_ist',
                'min_states_joint_1', 'min_states_joint_2', 'min_states_joint_3',
                'min_states_joint_4', 'min_states_joint_5', 'min_states_joint_6',
                'max_states_joint_1', 'max_states_joint_2', 'max_states_joint_3',
                'max_states_joint_4', 'max_states_joint_5', 'max_states_joint_6'
            ]

            records = [
                tuple(row[col] for col in columns)
                for row in metadata_rows
            ]

            await conn.copy_records_to_table(
                'bahn_meta',
                records=records,
                columns=columns,
                schema_name='bewegungsdaten'
            )

            logger.info(f"Successfully wrote {len(records)} metadata rows using COPY")