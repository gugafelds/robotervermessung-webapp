# backend/app/utils/metadata_embeddings/trajectory_loader_external.py
"""
trajectory_loader_external.py
===============================
Loads trajectory data from an in-memory payload (RoboDK-simulated
candidate from the recorder) instead of a database traj_id. Returns
the same shape as TrajectoryLoader.load_trajectory_data(), so the rest
of the pipeline (rerank(), predict_performance()) needs no changes.

A payload always represents exactly ONE segment (one PointGenerator
candidate / move) — 'trajectory' and 'segments' are therefore
identical, mirroring how a single-segment DB trajectory has
seg_id == traj_id (see get_all_segments_for_trajectories()).
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

EXTERNAL_SEG_ID = 'externalcandidate'


class TrajectoryLoaderExternal:
    """
    Drop-in replacement for TrajectoryLoader when the query side comes
    from an unsaved, simulated candidate rather than the database.
    Only the QUERY side uses this — candidate retrieval from the DB
    (Stage 1 embeddings, Stage 2 DTW against neighbors) is unaffected.
    """

    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    async def load_trajectory_data(self, traj_id: str, mode: str) -> Optional[Dict]:
        """
        traj_id is ignored — kept only so this matches TrajectoryLoader's
        call signature (run_similarity_pipeline calls it positionally).
        """
        trajectory = self._payload.get('trajectory') or {}

        if mode == 'position':
            points = trajectory.get('positions')
        elif mode == 'joint':
            points = trajectory.get('joints')
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'position' or 'joint'")

        if not points:
            logger.warning(f"TrajectoryLoaderExternal: no '{mode}' data in payload")
            return None

        arr = np.array(points, dtype=np.float32)

        return {
            'trajectory': arr,
            'segments': {EXTERNAL_SEG_ID: arr},
        }