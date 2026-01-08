# backend/app/utils/trajectory_loader.py

import asyncpg
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TrajectoryLoader:
    """
    Loads trajectory data from PostgreSQL for DTW computation
    Supports both trajectory-level and segment-level data
    """

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection

    async def load_trajectory_data(
        self,
        bahn_id: str,
        mode: str
    ) -> Optional[Dict]:
        """
        Load trajectory data - returns BOTH levels at once
        
        Args:
            bahn_id: Bahn ID (e.g., "1765989370")
            mode: 'position' or 'joint'
        
        Returns:
            {
                'trajectory': np.ndarray (n_total, dims),
                'segments': {
                    'segment_id': np.ndarray (n_points, dims),
                    ...
                }
            }
            Returns None if bahn_id not found
        """
        try:
            # Determine table and columns based on mode
            if mode == 'position':
                table = 'bahn_position_soll'
                cols = ['x_soll', 'y_soll', 'z_soll']
            elif mode == 'joint':
                table = 'bahn_joint_states'
                cols = ['joint_1', 'joint_2', 'joint_3', 
                        'joint_4', 'joint_5', 'joint_6']
            else:
                raise ValueError(f"Invalid mode: {mode}. Must be 'position' or 'joint'")

            # Query with segment_id for automatic segmentation
            query = f"""
                SELECT segment_id, {', '.join(cols)}
                FROM bewegungsdaten.{table}
                WHERE bahn_id = $1
                ORDER BY timestamp
            """

            rows = await self.connection.fetch(query, bahn_id)

            if not rows:
                logger.warning(f"No data found for bahn_id: {bahn_id}, mode: {mode}")
                return None

            # Build BOTH levels from same data
            all_points = []
            segments = {}
            current_segment = None
            current_data = []

            for row in rows:
                seg_id = row['segment_id']
                point = [row[col] for col in cols]

                # For trajectory level: collect all
                all_points.append(point)

                # For segment level: group by segment_id
                if seg_id != current_segment:
                    if current_segment:
                        segments[current_segment] = np.array(current_data, dtype=np.float32)
                    current_segment = seg_id
                    current_data = []

                current_data.append(point)

            # Last segment
            if current_segment:
                segments[current_segment] = np.array(current_data, dtype=np.float32)

            result = {
                'trajectory': np.array(all_points, dtype=np.float32),
                'segments': segments
            }

            logger.info(
                f"Loaded {mode} data for {bahn_id}: "
                f"{len(all_points)} total points, {len(segments)} segments"
            )

            return result

        except Exception as e:
            logger.error(f"Error loading trajectory data for {bahn_id}: {e}")
            return None

    async def load_trajectories_batch(
        self,
        bahn_ids: List[str],
        mode: str
    ) -> Dict[str, Dict]:
        """
        Load multiple trajectories - returns BOTH levels for each
        
        Args:
            bahn_ids: List of Bahn IDs
            mode: 'position' or 'joint'
        
        Returns:
            {
                'bahn_id_1': {
                    'trajectory': np.ndarray,
                    'segments': {...}
                },
                ...
            }
        """
        try:
            if not bahn_ids:
                return {}

            # Determine table and columns
            if mode == 'position':
                table = 'bahn_position_soll'
                cols = ['x_soll', 'y_soll', 'z_soll']
            elif mode == 'joint':
                table = 'bahn_joint_states'
                cols = ['joint_1', 'joint_2', 'joint_3', 
                        'joint_4', 'joint_5', 'joint_6']
            else:
                raise ValueError(f"Invalid mode: {mode}")

            # Batch query
            query = f"""
                SELECT bahn_id, segment_id, {', '.join(cols)}
                FROM bewegungsdaten.{table}
                WHERE bahn_id = ANY($1)
                ORDER BY bahn_id, timestamp
            """

            rows = await self.connection.fetch(query, bahn_ids)

            if not rows:
                logger.warning(f"No data found for bahn_ids: {bahn_ids}")
                return {}

            # Build results
            results = {}
            current_bahn = None
            current_segment = None
            bahn_points = []
            segment_points = []
            segments_dict = {}

            for row in rows:
                bahn_id = row['bahn_id']
                seg_id = row['segment_id']
                point = [row[col] for col in cols]

                # New bahn?
                if bahn_id != current_bahn:
                    # Save previous bahn
                    if current_bahn:
                        if current_segment:
                            segments_dict[current_segment] = np.array(
                                segment_points, dtype=np.float32
                            )

                        results[current_bahn] = {
                            'trajectory': np.array(bahn_points, dtype=np.float32),
                            'segments': segments_dict
                        }

                    # Reset for new bahn
                    current_bahn = bahn_id
                    current_segment = seg_id
                    bahn_points = []
                    segment_points = []
                    segments_dict = {}

                # New segment within same bahn?
                elif seg_id != current_segment:
                    # Save previous segment
                    if current_segment:
                        segments_dict[current_segment] = np.array(
                            segment_points, dtype=np.float32
                        )

                    current_segment = seg_id
                    segment_points = []

                # Add point to both
                bahn_points.append(point)
                segment_points.append(point)

            # Save last bahn
            if current_bahn:
                if current_segment:
                    segments_dict[current_segment] = np.array(
                        segment_points, dtype=np.float32
                    )

                results[current_bahn] = {
                    'trajectory': np.array(bahn_points, dtype=np.float32),
                    'segments': segments_dict
                }

            logger.info(
                f"Batch loaded {mode} data for {len(results)} bahnen: "
                f"{len(rows)} total points"
            )

            return results

        except Exception as e:
            logger.error(f"Error in batch loading: {e}")
            return {}