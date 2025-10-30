# backend/app/utils/metadata_calculator.py

import asyncpg
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import logging
import re
import sys
from pathlib import Path

# Import EmbeddingCalculator
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ..utils.embedding_calculator import EmbeddingCalculator

logger = logging.getLogger(__name__)


class MetadataCalculatorService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.downsample_factor = 1

        # ✅ GEÄNDERT: EmbeddingCalculator mit velocity/acceleration
        self.embedding_calculator = EmbeddingCalculator(
            joint_samples=50,         # 50 × 6 = 300
            position_samples=100,     # 100 × 3 = 300
            orientation_samples=50,   # 50 × 4 = 200
            velocity_samples=100,     # 100 × 1 = 100
            acceleration_samples=50   # 50 × 3 = 150
        )

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
                             LEFT JOIN robotervermessung.bewegungsdaten.bahn_metadata bm
                                       ON bi.bahn_id = bm.bahn_id AND bi.bahn_id = bm.segment_id
                    WHERE bm.segment_id IS NULL
                    ORDER BY bi.bahn_id \
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
                    FROM robotervermessung.bewegungsdaten.bahn_metadata
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
                    FROM robotervermessung.bewegungsdaten.bahn_metadata
                    WHERE bahn_id = ANY ($1::text[]) \
                    """
            result = await conn.execute(query, bahn_ids)
            return int(result.split()[-1]) if result.startswith("DELETE") else 0

    async def delete_existing_embeddings(self, bahn_ids: List[str]) -> int:
        """Löscht vorhandene Embeddings für gegebene bahn_ids"""
        if not bahn_ids:
            return 0

        async with self.db_pool.acquire() as conn:
            query = """
                    DELETE \
                    FROM robotervermessung.bewegungsdaten.bahn_embeddings
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

            # Offene Form
            if ratio > 0.9:
                return "linear"
            elif ratio > 0.3:
                return "circular"
            else:
                return "linear"

        except Exception as e:
            logger.warning(f"Fehler bei Movement-Type-Erkennung: {e}")
            return "linear"

    async def _fetch_all_bahn_data(self, conn: asyncpg.Connection, bahn_id: str) -> Dict:
        """
        Holt ALLE benötigten Daten für eine Bahn
        Inkl. Joint States und Orientation für Embeddings!
        """
        bahn_info_query = """
                          SELECT weight, start_time, end_time
                          FROM robotervermessung.bewegungsdaten.bahn_info
                          WHERE bahn_id = $1 \
                          """
        bahn_info = await conn.fetchrow(bahn_info_query, bahn_id)

        if not bahn_info:
            return None

        segments_query = """
            SELECT segment_id,
                array_agg(x_soll ORDER BY timestamp) as x_data,
                array_agg(y_soll ORDER BY timestamp) as y_data,
                array_agg(z_soll ORDER BY timestamp) as z_data,
                array_agg(timestamp ORDER BY timestamp) as timestamps,  -- ✅ NEU
                MIN(timestamp) as min_timestamp,
                MAX(timestamp) as max_timestamp
            FROM robotervermessung.bewegungsdaten.bahn_position_soll
            WHERE bahn_id = $1
            GROUP BY segment_id
            ORDER BY segment_id
        """
        segments = await conn.fetch(segments_query, bahn_id)

        joint_query = f"""
            WITH numbered AS (
                SELECT segment_id,
                       joint_1, joint_2, joint_3, joint_4, joint_5, joint_6,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_joint_states
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(joint_1 ORDER BY rn) as j1,
                   array_agg(joint_2 ORDER BY rn) as j2,
                   array_agg(joint_3 ORDER BY rn) as j3,
                   array_agg(joint_4 ORDER BY rn) as j4,
                   array_agg(joint_5 ORDER BY rn) as j5,
                   array_agg(joint_6 ORDER BY rn) as j6
            FROM numbered
            GROUP BY segment_id
        """
        joints = await conn.fetch(joint_query, bahn_id)

        orientation_query = f"""
            WITH numbered AS (
                SELECT segment_id, qw_soll, qx_soll, qy_soll, qz_soll,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_orientation_soll
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(qw_soll ORDER BY rn) as qw,
                   array_agg(qx_soll ORDER BY rn) as qx,
                   array_agg(qy_soll ORDER BY rn) as qy,
                   array_agg(qz_soll ORDER BY rn) as qz
            FROM numbered
            GROUP BY segment_id
        """
        orientations = await conn.fetch(orientation_query, bahn_id)

        # Twist Stats mit Downsampling
        twist_query = f"""
            WITH numbered AS (
                SELECT segment_id,
                       tcp_speed_ist,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(tcp_speed_ist ORDER BY rn) as twist_values
            FROM numbered
            GROUP BY segment_id
        """
        twists = await conn.fetch(twist_query, bahn_id)

        # Acceleration Stats mit Downsampling
        accel_query = f"""
            WITH numbered AS (
                SELECT segment_id,
                       tcp_accel_soll,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_accel_soll
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(tcp_accel_soll ORDER BY rn) as accel_values
            FROM numbered
            GROUP BY segment_id
        """
        accels = await conn.fetch(accel_query, bahn_id)

        return {
            'bahn_info': bahn_info,
            'segments': segments,
            'joints': {row['segment_id']: row for row in joints},  
            'orientations': {row['segment_id']: row for row in orientations},  
            'twists': {row['segment_id']: row['twist_values'] for row in twists},
            'accels': {row['segment_id']: row['accel_values'] for row in accels}
        }

    def _calculate_all_metadata_in_memory(self, bahn_id: str, bahn_data: Dict) -> List[Dict]:
        """
        Berechnet SIMPLIFIED Metadaten (nur 14 Spalten!)
        """
        metadata_rows = []
        weight = bahn_data['bahn_info']['weight']

        # Berechne Gesamtdauer
        total_duration = 0.0
        if bahn_data['segments'][0]['min_timestamp'] and bahn_data['segments'][-1]['max_timestamp']:
            try:
                start_time = bahn_data['segments'][0]['min_timestamp']
                end_time = bahn_data['segments'][-1]['max_timestamp']
                min_ts = int(float(start_time))
                max_ts = int(float(end_time))
                total_duration = max((max_ts - min_ts) / 1_000_000_000.0, 0.0)
                
            except:
                pass

        # Verarbeite jedes Segment
        segment_movement_types = []
        total_length = 0.0

        for segment in bahn_data['segments']:
            segment_id = segment['segment_id']

            # Movement Type Detection
            x_data = np.array(segment['x_data'])
            y_data = np.array(segment['y_data'])
            z_data = np.array(segment['z_data'])

            centroid = self._calculate_3d_centroid(x_data, y_data, z_data)

            step = max(1, len(x_data) // 20)
            movement_type = self.detect_movement_type(
                x_data[::step], y_data[::step], z_data[::step]
            )
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

            # Length (Euclidean distance)
            delta = np.array([
                x_data[-1] - x_data[0],
                y_data[-1] - y_data[0],
                z_data[-1] - z_data[0]
            ])
            length = float(np.linalg.norm(delta))
            total_length += length

            # Twist Stats
            twist_values = bahn_data['twists'].get(segment_id, [])
            if twist_values and len(twist_values) > 0:
                twist_arr = np.array(twist_values, dtype=np.float32)
                min_twist = float(np.min(twist_arr))
                max_twist = float(np.max(twist_arr))
                mean_twist = float(np.mean(twist_arr))
                median_twist = float(np.median(twist_arr))
                std_twist = float(np.std(twist_arr))
            else:
                min_twist = max_twist = mean_twist = median_twist = std_twist = 0.0

            # Acceleration Stats
            accel_values = bahn_data['accels'].get(segment_id, [])
            if accel_values and len(accel_values) > 0:
                accel_arr = np.array(accel_values, dtype=np.float32)
                min_accel = float(np.min(accel_arr))
                max_accel = float(np.max(accel_arr))
                mean_accel = float(np.mean(accel_arr))
                median_accel = float(np.median(accel_arr))
                std_accel = float(np.std(accel_arr))
            else:
                min_accel = max_accel = mean_accel = median_accel = std_accel = 0.0

            # Segment Metadata Row
            metadata_rows.append({
                'bahn_id': bahn_id,
                'segment_id': segment_id,
                'movement_type': movement_type,
                'duration': round(segment_duration, 3),
                'weight': round(weight, 3),
                'length': round(length, 3),
                'min_twist_ist': round(min_twist, 3),
                'max_twist_ist': round(max_twist, 3),
                'mean_twist_ist': round(mean_twist, 3),
                'median_twist_ist': round(median_twist, 3),
                'std_twist_ist': round(std_twist, 3),
                'min_acceleration_ist': round(min_accel, 3),
                'max_acceleration_ist': round(max_accel, 3),
                'mean_acceleration_ist': round(mean_accel, 3),
                'median_acceleration_ist': round(median_accel, 3),
                'std_acceleration_ist': round(std_accel, 3),
                'position_x': centroid['position_x'],
                'position_y': centroid['position_y'],
                'position_z': centroid['position_z']
            })

        # Gesamtbahn-Zeile (Aggregation über alle Segmente)
        if metadata_rows:
            total_movement_string = ''.join([mt[0].lower() for mt in segment_movement_types])

            all_x = np.concatenate([np.array(seg['x_data']) for seg in bahn_data['segments']])
            all_y = np.concatenate([np.array(seg['y_data']) for seg in bahn_data['segments']])
            all_z = np.concatenate([np.array(seg['z_data']) for seg in bahn_data['segments']])
            
            total_centroid = self._calculate_3d_centroid(all_x, all_y, all_z)

            # Aggregiere Twist/Accel über alle Segmente
            all_twist = []
            all_accel = []
            for row in metadata_rows:
                all_twist.extend([
                    row['min_twist_ist'], row['max_twist_ist'],
                    row['mean_twist_ist'], row['median_twist_ist']
                ])
                all_accel.extend([
                    row['min_acceleration_ist'], row['max_acceleration_ist'],
                    row['mean_acceleration_ist'], row['median_acceleration_ist']
                ])

            total_metadata = {
                'bahn_id': bahn_id,
                'segment_id': bahn_id,  # Bahn-Level: segment_id = bahn_id
                'movement_type': total_movement_string,
                'duration': round(total_duration, 3),
                'weight': round(weight, 3),
                'length': round(total_length, 3),
                'min_twist_ist': round(float(min(all_twist)), 3) if all_twist else 0.0,
                'max_twist_ist': round(float(max(all_twist)), 3) if all_twist else 0.0,
                'mean_twist_ist': round(float(np.mean(all_twist)), 3) if all_twist else 0.0,
                'median_twist_ist': round(float(np.median(all_twist)), 3) if all_twist else 0.0,
                'std_twist_ist': round(float(np.std(all_twist)), 3) if all_twist else 0.0,
                'min_acceleration_ist': round(float(min(all_accel)), 3) if all_accel else 0.0,
                'max_acceleration_ist': round(float(max(all_accel)), 3) if all_accel else 0.0,
                'mean_acceleration_ist': round(float(np.mean(all_accel)), 3) if all_accel else 0.0,
                'median_acceleration_ist': round(float(np.median(all_accel)), 3) if all_accel else 0.0,
                'std_acceleration_ist': round(float(np.std(all_accel)), 3) if all_accel else 0.0,
                'position_x': round(float(total_centroid['position_x']), 3),
                'position_y': round(float(total_centroid['position_y']), 3),
                'position_z': round(float(total_centroid['position_z']), 3)
            }

            metadata_rows.append(total_metadata)

        return metadata_rows

    def _calculate_all_embeddings_in_memory(self, bahn_id: str, bahn_data: Dict) -> List[Dict]:
        """
        ✅ NEU: Berechnet Embeddings für alle Segmente UND die Gesamtbahn

        Returns:
            List[Dict] mit segment_id, bahn_id, joint_embedding, position_embedding, orientation_embedding
        """
        embedding_rows = []

        # 1. Segmente (segment_id != bahn_id)
        for segment in bahn_data['segments']:
            segment_id = segment['segment_id']

            # Joint Embedding
            joint_emb = None
            joint_data_raw = bahn_data['joints'].get(segment_id)
            if joint_data_raw and joint_data_raw['j1']:
                joint_data = [
                    {
                        'joint_1': joint_data_raw['j1'][i],
                        'joint_2': joint_data_raw['j2'][i],
                        'joint_3': joint_data_raw['j3'][i],
                        'joint_4': joint_data_raw['j4'][i],
                        'joint_5': joint_data_raw['j5'][i],
                        'joint_6': joint_data_raw['j6'][i]
                    }
                    for i in range(len(joint_data_raw['j1']))
                ]
                joint_emb = self.embedding_calculator.compute_joint_embedding(joint_data)

            # Position Embedding
            pos_emb = None
            if segment['x_data'] and len(segment['x_data']) > 0:
                pos_data = [
                    {
                        'x_soll': segment['x_data'][i],
                        'y_soll': segment['y_data'][i],
                        'z_soll': segment['z_data'][i]
                    }
                    for i in range(len(segment['x_data']))
                ]
                pos_emb = self.embedding_calculator.compute_position_embedding(pos_data)

            # Orientation Embedding
            ori_emb = None
            ori_data_raw = bahn_data['orientations'].get(segment_id)
            if ori_data_raw and ori_data_raw['qw']:
                ori_data = [
                    {
                        'qw_soll': ori_data_raw['qw'][i],
                        'qx_soll': ori_data_raw['qx'][i],
                        'qy_soll': ori_data_raw['qy'][i],
                        'qz_soll': ori_data_raw['qz'][i]
                    }
                    for i in range(len(ori_data_raw['qw']))
                ]
                ori_emb = self.embedding_calculator.compute_orientation_embedding(ori_data)

            # Skip wenn keine Embeddings berechnet wurden
            if joint_emb is None and pos_emb is None and ori_emb is None:
                continue

            vel_emb = None
            acc_emb = None

            if segment['x_data'] and len(segment['x_data']) > 2:
                # Timestamps zu Sekunden konvertieren
                timestamps = [float(t) / 1_000_000_000.0 for t in segment['timestamps']]
                
                vel_acc_data = [
                    {
                        'x_soll': segment['x_data'][i],
                        'y_soll': segment['y_data'][i],
                        'z_soll': segment['z_data'][i],
                        'timestamp': timestamps[i]
                    }
                    for i in range(len(segment['x_data']))
                ]
                
                # ✅ Ein Call für beide!
                vel_emb, acc_emb = self.embedding_calculator.compute_velocity_and_acceleration_embeddings(vel_acc_data)

            # Skip wenn keine Embeddings berechnet wurden
            if all(x is None for x in [joint_emb, pos_emb, ori_emb, vel_emb, acc_emb]):
                continue

            embedding_rows.append({
                'segment_id': segment_id,
                'bahn_id': bahn_id,
                'joint_embedding': self._array_to_str(joint_emb) if joint_emb is not None else None,
                'position_embedding': self._array_to_str(pos_emb) if pos_emb is not None else None,
                'orientation_embedding': self._array_to_str(ori_emb) if ori_emb is not None else None,
                'velocity_embedding': self._array_to_str(vel_emb) if vel_emb is not None else None,  # ✅ NEU
                'acceleration_embedding': self._array_to_str(acc_emb) if acc_emb is not None else None,  # ✅ NEU
            })

        # 2. Gesamtbahn (segment_id = bahn_id)
        # Für Bahn: Kombiniere ALLE Daten über alle Segmente
        all_joint_data = []
        all_pos_data = []
        all_ori_data = []
        all_vel_acc_data = []

        for segment in bahn_data['segments']:
            segment_id = segment['segment_id']

            # Joint
            joint_raw = bahn_data['joints'].get(segment_id)
            if joint_raw and joint_raw['j1']:
                for i in range(len(joint_raw['j1'])):
                    all_joint_data.append({
                        'joint_1': joint_raw['j1'][i],
                        'joint_2': joint_raw['j2'][i],
                        'joint_3': joint_raw['j3'][i],
                        'joint_4': joint_raw['j4'][i],
                        'joint_5': joint_raw['j5'][i],
                        'joint_6': joint_raw['j6'][i]
                    })

            # Position
            if segment['x_data']:
                for i in range(len(segment['x_data'])):
                    all_pos_data.append({
                        'x_soll': segment['x_data'][i],
                        'y_soll': segment['y_data'][i],
                        'z_soll': segment['z_data'][i]
                    })

            # Orientation
            ori_raw = bahn_data['orientations'].get(segment_id)
            if ori_raw and ori_raw['qw']:
                for i in range(len(ori_raw['qw'])):
                    all_ori_data.append({
                        'qw_soll': ori_raw['qw'][i],
                        'qx_soll': ori_raw['qx'][i],
                        'qy_soll': ori_raw['qy'][i],
                        'qz_soll': ori_raw['qz'][i]
                    })
            
        all_vel_acc_data = []

        for segment in bahn_data['segments']:
            if segment['x_data'] and len(segment['x_data']) > 2:
                timestamps = [float(t) / 1_000_000_000.0 for t in segment['timestamps']]
                
                for i in range(len(segment['x_data'])):
                    all_vel_acc_data.append({
                        'x_soll': segment['x_data'][i],
                        'y_soll': segment['y_data'][i],
                        'z_soll': segment['z_data'][i],
                        'timestamp': timestamps[i]
                    })

        # Berechne Bahn-Level Embeddings
        bahn_joint_emb = self.embedding_calculator.compute_joint_embedding(all_joint_data) if all_joint_data else None
        bahn_pos_emb = self.embedding_calculator.compute_position_embedding(all_pos_data) if all_pos_data else None
        bahn_ori_emb = self.embedding_calculator.compute_orientation_embedding(all_ori_data) if all_ori_data else None
        bahn_vel_emb, bahn_acc_emb = self.embedding_calculator.compute_velocity_and_acceleration_embeddings(
            all_vel_acc_data
        ) if len(all_vel_acc_data) > 2 else (None, None)

        if bahn_joint_emb is not None or bahn_pos_emb is not None or bahn_ori_emb is not None:
            embedding_rows.append({
                'segment_id': bahn_id,  # ✅ Bahn-Level: segment_id = bahn_id
                'bahn_id': bahn_id,
                'joint_embedding': self._array_to_str(bahn_joint_emb) if bahn_joint_emb is not None else None,
                'position_embedding': self._array_to_str(bahn_pos_emb) if bahn_pos_emb is not None else None,
                'orientation_embedding': self._array_to_str(bahn_ori_emb) if bahn_ori_emb is not None else None,
                'velocity_embedding': self._array_to_str(bahn_vel_emb) if bahn_vel_emb is not None else None,
                'acceleration_embedding': self._array_to_str(bahn_acc_emb) if bahn_acc_emb is not None else None,
            })

        return embedding_rows

    @staticmethod
    def _array_to_str(arr: np.ndarray) -> str:
        """Convert numpy array to PostgreSQL vector string"""
        return '[' + ','.join(str(x) for x in arr.tolist()) + ']'

    async def process_single_bahn(
            self,
            conn: asyncpg.Connection,
            bahn_id: str
    ) -> Dict:
        """
        ✅ NEU: Wie process_single_bahn_in_memory, aber mit expliziter Connection
        Für Background Tasks
        """
        result = {
            'bahn_id': bahn_id,
            'metadata': [],
            'embeddings': [],
            'segments_processed': 0,
            'error': None
        }

        try:
            # 1. Hole ALLE Daten für diese Bahn
            bahn_data = await self._fetch_all_bahn_data(conn, bahn_id)

            if not bahn_data:
                result['error'] = 'Keine Daten gefunden'
                return result

            # 2. Verarbeite Metadaten IN MEMORY
            metadata_rows = self._calculate_all_metadata_in_memory(bahn_id, bahn_data)
            result['metadata'] = metadata_rows

            # 3. Berechne Embeddings IN MEMORY
            embedding_rows = self._calculate_all_embeddings_in_memory(bahn_id, bahn_data)
            result['embeddings'] = embedding_rows

            result['segments_processed'] = len(metadata_rows) - 1

            #logger.info(
            #    f"Bahn {bahn_id}: {len(metadata_rows)} metadata rows, "
            #    f"{len(embedding_rows)} embedding rows"
            #)

        except Exception as e:
            logger.error(f"Fehler bei Verarbeitung bahn_id {bahn_id}: {e}")
            result['error'] = str(e)

        return result
    
    @staticmethod
    def _calculate_3d_centroid(x_data, y_data, z_data) -> Dict[str, float]:
        """
        Berechnet den 3D-Schwerpunkt (Centroid) der Bahn
        
        Returns:
            Dict mit position_x, position_y, position_z
        """
        return {
            'position_x': round(float(np.mean(x_data)), 3),
            'position_y': round(float(np.mean(y_data)), 3),
            'position_z': round(float(np.mean(z_data)), 3)
        }


    async def batch_write_metadata(
            self,
            conn: asyncpg.Connection,
            metadata_rows: List[Dict]
    ):
        """
        ✅ NEU: Schreibt Metadaten mit expliziter Connection
        """
        if not metadata_rows:
            return

        columns = [
            'bahn_id', 'segment_id', 'movement_type',
            'duration', 'weight', 'length',
            'min_twist_ist', 'max_twist_ist', 'mean_twist_ist',
            'median_twist_ist', 'std_twist_ist',
            'min_acceleration_ist', 'max_acceleration_ist', 'mean_acceleration_ist',
            'median_acceleration_ist', 'std_acceleration_ist',
            'position_x', 'position_y', 'position_z'
        ]

        records = [
            tuple(row[col] for col in columns)
            for row in metadata_rows
        ]

        await conn.copy_records_to_table(
            'bahn_metadata',
            records=records,
            columns=columns,
            schema_name='bewegungsdaten'
        )

        logger.info(f"✓ Wrote {len(records)} metadata rows to bahn_metadata")

    async def batch_write_embeddings(
            self,
            conn: asyncpg.Connection,
            embedding_rows: List[Dict]
    ):
        """
        ✅ NEU: Schreibt Embeddings mit expliziter Connection
        """
        if not embedding_rows:
            return

        # Temp table
        await conn.execute("""
                           DROP TABLE IF EXISTS temp_embeddings;

                           CREATE
                           TEMP TABLE temp_embeddings (
                segment_id TEXT,
                bahn_id TEXT,
                joint_embedding TEXT,
                position_embedding TEXT,
                orientation_embedding TEXT,
                velocity_embedding TEXT,
                acceleration_embedding TEXT
            )
                           """)

        # COPY
        records = [
            (
                row['segment_id'],
                row['bahn_id'],
                row['joint_embedding'],
                row['position_embedding'],
                row['orientation_embedding'],
                row['velocity_embedding'],
                row['acceleration_embedding']
            )
            for row in embedding_rows
        ]

        await conn.copy_records_to_table(
            'temp_embeddings',
            records=records,
            columns=[
                'segment_id', 'bahn_id', 'joint_embedding', 'position_embedding',
                'orientation_embedding', 'velocity_embedding', 'acceleration_embedding'
            ]
        )

        # INSERT with conflict handling
        await conn.execute("""
                           INSERT INTO bewegungsdaten.bahn_embeddings
                           (segment_id, bahn_id, joint_embedding, position_embedding, orientation_embedding,
                            velocity_embedding, acceleration_embedding)
                           SELECT segment_id,
                                  bahn_id,
                                  joint_embedding::vector, position_embedding::vector, orientation_embedding::vector, velocity_embedding::vector, acceleration_embedding::vector
                           FROM temp_embeddings ON CONFLICT (segment_id) DO
                           UPDATE SET
                               joint_embedding = EXCLUDED.joint_embedding,
                               position_embedding = EXCLUDED.position_embedding,
                               orientation_embedding = EXCLUDED.orientation_embedding,
                               velocity_embedding = EXCLUDED.velocity_embedding,
                               acceleration_embedding = EXCLUDED.acceleration_embedding
                           """)

        logger.info(f"✓ Wrote {len(records)} embedding rows to bahn_embeddings")

    async def batch_write_everything(
            self,
            conn: asyncpg.Connection,
            metadata_rows: List[Dict],
            embedding_rows: List[Dict]
    ):
        """
        ✅ NEU: Schreibt SOWOHL Metadaten ALS AUCH Embeddings mit expliziter Connection
        """
        await self.batch_write_metadata(conn, metadata_rows)
        await self.batch_write_embeddings(conn, embedding_rows)