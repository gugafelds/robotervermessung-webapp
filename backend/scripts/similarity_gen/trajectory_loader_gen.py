import sys
import asyncpg
import logging
import ast
import json
import numpy as np
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

sys.path.append(
    r"\robotervermessung-webapp\backend\app"
)

from utils.metadata_embeddings.trajectory_loader import TrajectoryLoader

class TrajectoryLoaderGen(TrajectoryLoader):
    def __init__(self, connection: asyncpg.Connection):
        super().__init__(connection)

    def _safe_parse(self, value):
        if isinstance(value, (list, tuple, np.ndarray)):
            return value

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(('[' , '(', '{')):
                try:
                    return ast.literal_eval(value)
                except Exception:
                    return None
            return value

        return value

    def _to_array(self, points):
        if isinstance(points, np.ndarray):
            return points.astype(np.float64)

        if not points:
            return np.empty((0, 3), dtype=np.float64)

        first = points[0]
        if isinstance(first, dict):
            keys = ['x_cmd', 'y_cmd', 'z_cmd']
            return np.array([[point[key] for key in keys] for point in points], dtype=np.float64)

        return np.asarray(points, dtype=np.float64)

    async def load_trajectory_data(
        self,
        traj_id: str,
        mode: str = "position"
    ) -> Optional[Dict]:

        try:
            parsed = self._safe_parse(traj_id)
            if parsed is None:
                raise ValueError('Unable to parse provided trajectory data')

            if isinstance(parsed, str) or isinstance(parsed, (int, float)):
                return await super().load_trajectory_data(traj_id, mode)

            trajectory = self._to_array(parsed)
            segments = {}
            for i in range(1, len(trajectory)):
                seg_points = [parsed[i - 1], parsed[i]]
                seg_id = json.dumps(seg_points, separators=(',', ':'))
                segments[seg_id] = np.stack([trajectory[i - 1], trajectory[i]])

            result = {
                'trajectory': trajectory,
                'segments': segments
            }

            return result

        except Exception as e:

            logger.error(f"TrajectoryLoaderGen error: {e}")

            return {
                'trajectory': np.empty((0, 3), dtype=np.float32),
                'segments': {}
            }

    async def load_trajectories_batch(
        self,
        traj_ids: List[str],
        mode: str = "position"
    ) -> Dict[str, Dict]:

        try:
            if not traj_ids:
                return {}

            # Build results
            results = {}

            for id in traj_ids:
                results[id] = await(self.load_trajectory_data(id))

            return results

        except Exception as e:
            logger.error(f"Error in batch loading: {e}")
            return {}