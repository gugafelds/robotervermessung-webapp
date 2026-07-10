# backend/app/utils/trajectory_loader.py

import asyncpg
import numpy as np
from typing import Dict, List, Optional, Any
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
        traj_id: str,
        mode: str
    ) -> Optional[Dict]:
        """
        Load trajectory data - returns BOTH levels at once
        
        Args:
            traj_id: Bahn ID (e.g., "1765989370")
            mode: 'position' or 'joint'
        
        Returns:
            {
                'trajectory': np.ndarray (n_total, dims),
                'segments': {
                    'seg_id': np.ndarray (n_points, dims),
                    ...
                }
            }
            Returns None if traj_id not found
        """
        try:
            # Determine table and columns based on mode
            if mode == 'position':
                table = 'traj_position_cmd'
                cols = ['x_cmd', 'y_cmd', 'z_cmd']
            elif mode == 'joint':
                table = 'traj_joint_states'
                cols = ['joint_1', 'joint_2', 'joint_3', 
                        'joint_4', 'joint_5', 'joint_6']
            else:
                raise ValueError(f"Invalid mode: {mode}. Must be 'position' or 'joint'")

            # Query with seg_id for automatic segmentation
            query = f"""
                SELECT seg_id, {', '.join(cols)}
                FROM motion.{table}
                WHERE traj_id = $1
                ORDER BY timestamp
            """

            rows = await self.connection.fetch(query, traj_id)

            if not rows:
                logger.warning(f"No data found for traj_id: {traj_id}, mode: {mode}")
                return None

            # Build BOTH levels from same data
            all_points = []
            segments = {}
            current_segment = None
            current_data = []

            for row in rows:
                seg_id = row['seg_id']
                point = [row[col] for col in cols]

                # For trajectory level: collect all
                all_points.append(point)

                # For segment level: group by seg_id
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
                f"Loaded {mode} data for {traj_id}: "
                f"{len(all_points)} total points, {len(segments)} segments"
            )

            return result

        except Exception as e:
            logger.error(f"Error loading trajectory data for {traj_id}: {e}")
            return None

    async def load_trajectories_batch(
        self,
        traj_ids: List[str],
        mode: str
    ) -> Dict[str, Dict]:
        """
        Load multiple trajectories - returns BOTH levels for each
        
        Args:
            traj_ids: List of Bahn IDs
            mode: 'position' or 'joint'
        
        Returns:
            {
                'traj_id_1': {
                    'trajectory': np.ndarray,
                    'segments': {...}
                },
                ...
            }
        """
        try:
            if not traj_ids:
                return {}

            # Determine table and columns
            if mode == 'position':
                table = 'traj_position_cmd'
                cols = ['x_cmd', 'y_cmd', 'z_cmd']
            elif mode == 'joint':
                table = 'traj_joint_states'
                cols = ['joint_1', 'joint_2', 'joint_3', 
                        'joint_4', 'joint_5', 'joint_6']
            else:
                raise ValueError(f"Invalid mode: {mode}")

            # Batch query
            query = f"""
                SELECT traj_id, seg_id, {', '.join(cols)}
                FROM motion.{table}
                WHERE traj_id = ANY($1)
                ORDER BY traj_id, timestamp
            """

            rows = await self.connection.fetch(query, traj_ids)

            if not rows:
                logger.warning(f"No data found for traj_ids: {traj_ids}")
                return {}

            # Build results
            results = {}
            current_bahn = None
            current_segment = None
            bahn_points = []
            segment_points = []
            segments_dict = {}

            for row in rows:
                traj_id = row['traj_id']
                seg_id = row['seg_id']
                point = [row[col] for col in cols]

                # New bahn?
                if traj_id != current_bahn:
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
                    current_bahn = traj_id
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
        
# ── Candidate (unsaved) variant ───────────────────────────────────────────
 
class TrajectoryLoaderCandidate:
    """
    Drop-in replacement for TrajectoryLoader when the QUERY side is an
    unsaved, simulated candidate (no traj_id in the DB).

    Returns the same shape as TrajectoryLoader.load_trajectory_data() so
    the rest of the pipeline (rerank(), predict_performance()) is unaffected.

    A payload always represents exactly ONE segment — 'trajectory' and
    'segments' are therefore identical, mirroring how a single-segment
    DB trajectory has seg_id == traj_id.

    Previously lived in trajectory_loader_ext.py as TrajectoryLoaderExternal.
    """

    def __init__(self, payload: Dict[str, Any], candidate_seg_id: str = None):  
        self._payload          = payload
        self._candidate_seg_id = candidate_seg_id

    async def load_trajectory_data(self, traj_id: str, mode: str) -> Optional[Dict]:
        """
        traj_id is ignored — kept only to match TrajectoryLoader's call signature.
        """
        from .embedding_calculator import CANDIDATE_SEG_ID

        seg_id     = self._candidate_seg_id or CANDIDATE_SEG_ID  
        trajectory = self._payload.get('trajectory') or {}

        if mode == 'position':
            points = trajectory.get('positions')
        elif mode == 'joint':
            points = trajectory.get('joints')
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'position' or 'joint'")

        if not points:
            logger.warning(f"TrajectoryLoaderCandidate: no '{mode}' data in payload")
            return None

        arr = np.array(points, dtype=np.float32)

        return {
            'trajectory': arr,
            'segments':   {seg_id: arr},
        }