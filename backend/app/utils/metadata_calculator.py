# backend/app/utils/metadata_calculator.py

import asyncio
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
        self.downsample_factor = 3  # Jeder 3. Punkt

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
        Holt ALLE benötigten Daten für eine Bahn
        NUR: Bahn Info, Position (für movement_type), Twist, Accel
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

        # Segmente mit Position (für movement_type + length + duration)
        segments_query = """
                         SELECT segment_id,
                                array_agg(x_soll ORDER BY timestamp) as x_data,
                                array_agg(y_soll ORDER BY timestamp) as y_data,
                                array_agg(z_soll ORDER BY timestamp) as z_data,
                                MIN(timestamp)                       as min_timestamp,
                                MAX(timestamp)                       as max_timestamp
                         FROM robotervermessung.bewegungsdaten.bahn_position_soll
                         WHERE bahn_id = $1
                         GROUP BY segment_id
                         ORDER BY segment_id \
                         """
        segments = await conn.fetch(segments_query, bahn_id)

        # Twist Stats mit Downsampling (jeder 3. Punkt)
        twist_query = f"""
            WITH numbered AS (
                SELECT segment_id,
                       tcp_speed_ist,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_twist_ist
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(tcp_speed_ist ORDER BY rn) FILTER (WHERE rn % {self.downsample_factor} = 1) as twist_values
            FROM numbered
            GROUP BY segment_id
        """
        twists = await conn.fetch(twist_query, bahn_id)

        # Acceleration Stats mit Downsampling (jeder 3. Punkt)
        accel_query = f"""
            WITH numbered AS (
                SELECT segment_id,
                       tcp_accel_ist,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM robotervermessung.bewegungsdaten.bahn_accel_ist
                WHERE bahn_id = $1
            )
            SELECT segment_id,
                   array_agg(tcp_accel_ist ORDER BY rn) FILTER (WHERE rn % {self.downsample_factor} = 1) as accel_values
            FROM numbered
            GROUP BY segment_id
        """
        accels = await conn.fetch(accel_query, bahn_id)

        return {
            'bahn_info': bahn_info,
            'segments': segments,
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

            # Twist Stats (von downsampled Daten)
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

            # Acceleration Stats (von downsampled Daten)
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

            # Segment Metadata Row (14 Spalten!)
            metadata_rows.append({
                'bahn_id': bahn_id,
                'segment_id': segment_id,
                'movement_type': movement_type,
                'duration': segment_duration,
                'weight': weight,
                'length': length,
                'min_twist_ist': min_twist,
                'max_twist_ist': max_twist,
                'mean_twist_ist': mean_twist,
                'median_twist_ist': median_twist,
                'std_twist_ist': std_twist,
                'min_acceleration_ist': min_accel,
                'max_acceleration_ist': max_accel,
                'mean_acceleration_ist': mean_accel,
                'median_acceleration_ist': median_accel,
                'std_acceleration_ist': std_accel
            })

        # Gesamtbahn-Zeile (Aggregation über alle Segmente)
        if metadata_rows:
            total_movement_string = ''.join([mt[0].lower() for mt in segment_movement_types])

            # Aggregiere Twist/Accel über alle Segmente
            all_twist = [row['min_twist_ist'] for row in metadata_rows]
            all_twist += [row['max_twist_ist'] for row in metadata_rows]
            all_twist += [row['mean_twist_ist'] for row in metadata_rows]
            all_twist += [row['median_twist_ist'] for row in metadata_rows]

            all_accel = [row['min_acceleration_ist'] for row in metadata_rows]
            all_accel += [row['max_acceleration_ist'] for row in metadata_rows]
            all_accel += [row['mean_acceleration_ist'] for row in metadata_rows]
            all_accel += [row['median_acceleration_ist'] for row in metadata_rows]

            total_metadata = {
                'bahn_id': bahn_id,
                'segment_id': bahn_id,  # Bahn-Level: segment_id = bahn_id
                'movement_type': total_movement_string,
                'duration': total_duration,
                'weight': weight,
                'length': total_length,
                'min_twist_ist': float(min(all_twist)) if all_twist else 0.0,
                'max_twist_ist': float(max(all_twist)) if all_twist else 0.0,
                'mean_twist_ist': float(np.mean(all_twist)) if all_twist else 0.0,
                'median_twist_ist': float(np.median(all_twist)) if all_twist else 0.0,
                'std_twist_ist': float(np.std(all_twist)) if all_twist else 0.0,
                'min_acceleration_ist': float(min(all_accel)) if all_accel else 0.0,
                'max_acceleration_ist': float(max(all_accel)) if all_accel else 0.0,
                'mean_acceleration_ist': float(np.mean(all_accel)) if all_accel else 0.0,
                'median_acceleration_ist': float(np.median(all_accel)) if all_accel else 0.0,
                'std_acceleration_ist': float(np.std(all_accel)) if all_accel else 0.0
            }

            metadata_rows.append(total_metadata)

        return metadata_rows

    async def batch_write_metadata(self, metadata_rows: List[Dict]):
        """
        Schreibt Metadaten in NEUE Tabelle: bahn_metadata
        """
        if not metadata_rows:
            return

        async with self.db_pool.acquire() as conn:
            columns = [
                'bahn_id', 'segment_id', 'movement_type',
                'duration', 'weight', 'length',
                'min_twist_ist', 'max_twist_ist', 'mean_twist_ist',
                'median_twist_ist', 'std_twist_ist',
                'min_acceleration_ist', 'max_acceleration_ist', 'mean_acceleration_ist',
                'median_acceleration_ist', 'std_acceleration_ist'
            ]

            records = [
                tuple(row[col] for col in columns)
                for row in metadata_rows
            ]

            await conn.copy_records_to_table(
                'bahn_metadata',  # NEUE Tabelle!
                records=records,
                columns=columns,
                schema_name='bewegungsdaten'
            )

            logger.info(f"Successfully wrote {len(records)} metadata rows to bahn_metadata")