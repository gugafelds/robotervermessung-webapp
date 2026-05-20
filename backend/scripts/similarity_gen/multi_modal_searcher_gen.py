import sys
import asyncpg
from typing import Dict, List, Optional, Union
import asyncio
import asyncpg
from typing import Dict, List, Optional, Union
import logging
import ast
import json
import numpy as np

logger = logging.getLogger(__name__)

sys.path.append(
    r"\robotervermessung-webapp\backend\app"
)

from utils.multimodal_framework.multi_modal_searcher import MultiModalSearcher
from shape_searcher_gen import ShapeSearcherGen
from utils.multimodal_framework.filter_searcher import FilterSearcher

class MultiModalSearcherGen(MultiModalSearcher):
    def __init__(self, conn_or_pool: Union[asyncpg.Pool, asyncpg.Connection]):
        super().__init__(conn_or_pool)

    @staticmethod
    def _make_helpers(conn: asyncpg.Connection):
        return ShapeSearcherGen(conn), FilterSearcher(conn)
    
    async def search_similar(
            self,
            target_id: str,
            modes: Optional[List[str]] = None,
            weights: Optional[Dict[str, float]] = None,
            prefilter_features: Optional[List[str]] = None,
            limit: int = 10,
            metric: str = 'sidtw',
            buffer_factor: int = 5,
    ) -> Dict:
        try:
            modes = ['position']
            weights = {'position': 1.0}

            if prefilter_features is None:
                prefilter_features = []

            result = {
                'target_id': target_id,
                'modes': modes,
                'weights': weights,
                'metric': metric,
                'traj_similarity': {},
                'segment_similarity': [],
                'metadata': {}
            }

            logger.info(f"[Search] target={target_id}")

            traj_results, target_segments = await asyncio.gather(
                self._search_trajs(
                    target_traj_id=target_id, 
                    modes=modes,
                    weights=weights,
                    limit=limit,
                    prefilter_features=prefilter_features,
                    metric=metric,
                    buffer_factor=buffer_factor,
                ),
                self._get_traj_segments(target_id),
            )

            result['traj_similarity'] = traj_results

            if not target_segments:
                result['metadata']['target_segments_count'] = 0
                return result

            result['metadata']['target_segments_count'] = len(target_segments)

            async def _search_one_segment(seg_id: str):
                features, seg_result = await asyncio.gather(
                    self._get_features(seg_id, metric),
                    self._search_segments(
                        target_seg_id=seg_id,
                        modes=modes,
                        weights=weights,
                        limit=limit,
                        prefilter_features=prefilter_features,
                        metric=metric,
                        buffer_factor=buffer_factor,
                    ),
                )
                return {
                    'target_segment': seg_id,
                    'target_segment_features': features,
                    'similar_segments': seg_result,
                }

            segment_results = await asyncio.gather(
                *[_search_one_segment(seg_id) for seg_id in target_segments]
            )

            result['segment_similarity'] = list(segment_results)
            result['metadata']['segments_processed'] = len(segment_results)

            return result

        except Exception as e:
            logger.error(f"Error in search_similar: {e}")
            return {
                'target_id': target_id,
                'error': str(e),
                'traj_similarity': {},
                'segment_similarity': []
            }
        
        
    async def _get_traj_segments(self, traj_id: str) -> List[str]:
        try:
            if isinstance(traj_id, (list, tuple)):
                data = list(traj_id)
            else:
                parsed = ast.literal_eval(traj_id)
                if isinstance(parsed, list):
                    data = parsed
                else:
                    return await super()._get_traj_segments(traj_id)
        except Exception:
            return await super()._get_traj_segments(traj_id)

        if len(data) < 2:
            return []

        segments = [json.dumps([data[i - 1], data[i]], separators=(',', ':')) for i in range(1, len(data))]
        return segments
        

    async def _get_features(self, seg_id: str, metric: str = 'sidtw') -> Optional[Dict]:
        try:
            if isinstance(seg_id, str) and seg_id.strip().startswith('['):
                pts = json.loads(seg_id)
                coords = np.array([[p['x_cmd'], p['y_cmd'], p['z_cmd']] for p in pts], dtype=float)
                length = float(np.sum(np.linalg.norm(np.diff(coords, axis=0), axis=1))) if len(coords) > 1 else 0.0
                centroid = coords.mean(axis=0).tolist() if len(coords) else [None, None, None]
                return {
                    'seg_id': seg_id,
                    'traj_id': seg_id,        
                    'duration': float(len(coords)),
                    'length': length,
                    'position_x': centroid[0],
                    'position_y': centroid[1],
                    'position_z': centroid[2],
                }
        except Exception:
            pass

        # fallback to DB-backed features for real DB seg_ids
        return await super()._get_features(seg_id, metric)
    
    def seg_id_to_traj_id(seg_id: str) -> str:
        if isinstance(seg_id, str) and seg_id.strip().startswith('['):
            return seg_id
        return seg_id.rsplit('_', 1)[0] if '_' in seg_id else seg_id