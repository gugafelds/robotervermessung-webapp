# backend/app/utils/multimodal_framework/multi_modal_searcher.py

import asyncio
import asyncpg
from typing import Dict, List, Optional, Union
import logging
from .shape_searcher import ShapeSearcher, ShapeSearcherCandidate
from .rrf_ranker import RRFRanker
from .filter_searcher import FilterSearcher

logger = logging.getLogger(__name__)


class _SingleConnContext:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def __aenter__(self) -> asyncpg.Connection:
        return self._conn

    async def __aexit__(self, *_):
        pass


class MultiModalSearcher:

    def __init__(self, conn_or_pool: Union[asyncpg.Pool, asyncpg.Connection]):
        if isinstance(conn_or_pool, asyncpg.Pool):
            self._pool: Optional[asyncpg.Pool] = conn_or_pool
            self._conn: Optional[asyncpg.Connection] = None
        else:
            self._pool = None
            self._conn = conn_or_pool

        self.ranker = RRFRanker(k=60)

    def _acquire(self):
        if self._pool:
            return self._pool.acquire()
        return _SingleConnContext(self._conn)

    @staticmethod
    def _make_helpers(conn: asyncpg.Connection):
        return ShapeSearcher(conn), FilterSearcher(conn)

    # =========================================================================
    # PUBLIC
    # =========================================================================

    async def search_similar(
            self,
            target_id: str,
            modes: Optional[List[str]] = None,
            weights: Optional[Dict[str, float]] = None,
            prefilter_features: Optional[List[str]] = None,
            limit: int = 10,
            metric: str = 'sidtw',
            buffer_factor: int = 5,
            include_tags: Optional[List[str]] = None,
            exclude_tags: Optional[List[str]] = None,
            exclude_ids: Optional[List[str]] = None,
    ) -> Dict:
        try:
            if modes is None:
                modes = ['joint', 'position', 'orientation', 'velocity', 'metadata']
            if weights is None:
                weights = {mode: 1.0 / len(modes) for mode in modes}
            if prefilter_features is None:
                prefilter_features = []

            target_traj_id, target_traj_features = await asyncio.gather(
                self._get_traj_id(target_id),
                self._get_features(target_id, metric),
            )

            if not target_traj_id:
                return {
                    'error': f"Target {target_id} not found",
                    'traj_similarity': {},
                    'segment_similarity': []
                }

            result = {
                'target_id': target_id,
                'target_traj_id': target_traj_id,
                'target_traj_features': target_traj_features,
                'modes': modes,
                'weights': weights,
                'metric': metric,
                'traj_similarity': {},
                'segment_similarity': [],
                'metadata': {}
            }

            traj_results, target_segments = await asyncio.gather(
                self._search_trajs(
                    target_traj_id=target_traj_id,
                    modes=modes,
                    weights=weights,
                    limit=limit,
                    prefilter_features=prefilter_features,
                    metric=metric,
                    buffer_factor=buffer_factor,
                    include_tags=include_tags,
                    exclude_tags=exclude_tags,
                    exclude_ids=exclude_ids,
                ),
                self._get_traj_segments(target_traj_id),
            )

            result['traj_similarity'] = traj_results

            if not target_segments:
                result['metadata']['target_segments_count'] = 0
                return result

            result['metadata']['target_segments_count'] = len(target_segments)

            async def _search_one_segment(seg_id: str) -> Dict:
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
                        include_tags=include_tags,
                        exclude_tags=exclude_tags,
                        exclude_ids=exclude_ids,
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
            logger.error(f"Error in hierarchical search for {target_id}: {e}")
            return {
                'target_id': target_id,
                'error': str(e),
                'traj_similarity': {},
                'segment_similarity': []
            }

    # =========================================================================
    # PRIVATE — BAHN
    # =========================================================================

    async def _search_trajs(
            self,
            target_traj_id: str,
            modes: List[str],
            weights: Dict[str, float],
            limit: int,
            prefilter_features: List[str],
            metric: str = 'sidtw',
            buffer_factor: int = 5,
            include_tags: Optional[List[str]] = None,
            exclude_tags: Optional[List[str]] = None,
            exclude_ids: Optional[List[str]] = None,
    ) -> Dict:
        try:
            async with self._acquire() as conn:
                shape, _ = self._make_helpers(conn)
                embedding_status = await shape.check_embeddings_exist(target_traj_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            search_limit = max(limit, limit * buffer_factor)

            if not available_modes:
                return {
                    'error': f"No embeddings available for traj {target_traj_id}",
                    'results': []
                }

            candidate_ids = None
            need_prefilter = (
                prefilter_features
                or include_tags
                or exclude_tags
                or exclude_ids
            )

            if need_prefilter:
                async with self._acquire() as conn:
                    _, prefilter = self._make_helpers(conn)
                    candidate_ids = await prefilter.get_filtered_candidates(
                        target_traj_id,
                        features_to_use=prefilter_features,
                        include_tags=include_tags,
                        exclude_tags=exclude_tags,
                        exclude_ids=exclude_ids,
                    )
                    traj_candidates = await prefilter._filter_only_trajs(candidate_ids)
                    logger.info(f"[Pre-Filter Bahn] {len(traj_candidates)} candidates")
                    if not traj_candidates:
                        return {'error': 'No candidates after pre-filter', 'results': []}
                    candidate_ids = traj_candidates

            async def _one_mode(mode: str):
                async with self._acquire() as conn:
                    shape, _ = self._make_helpers(conn)
                    results = await shape.search_by_embedding(
                        target_id=target_traj_id,
                        mode=mode,
                        limit=search_limit,
                        candidate_ids=candidate_ids,
                        only_traj=True,
                    )
                return mode, results

            mode_tuples = await asyncio.gather(*[_one_mode(m) for m in available_modes])
            rankings = dict(mode_tuples)

            fused = self.ranker.fuse_rankings(rankings, weights)
            final = fused[:limit]

            async with self._acquire() as conn:
                enriched = await self._enrich_results(final, conn, metric)

            return {
                'target': target_traj_id,
                'results': enriched,
                'metadata': {'modes': available_modes, 'weights': weights},
            }

        except Exception as e:
            logger.error(f"Error searching trajs for {target_traj_id}: {e}")
            return {'error': str(e), 'results': []}

    # =========================================================================
    # PRIVATE — SEGMENT
    # =========================================================================

    async def _search_segments(
            self,
            target_seg_id: str,
            modes: List[str],
            weights: Dict[str, float],
            limit: int,
            prefilter_features: List[str],
            metric: str = 'sidtw',
            buffer_factor: int = 5,
            include_tags: Optional[List[str]] = None,
            exclude_tags: Optional[List[str]] = None,
            exclude_ids: Optional[List[str]] = None,
    ) -> Dict:
        try:
            async with self._acquire() as conn:
                shape, _ = self._make_helpers(conn)
                embedding_status = await shape.check_embeddings_exist(target_seg_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            search_limit = max(limit, limit * buffer_factor)

            if not available_modes:
                return {
                    'error': f"No embeddings for segment {target_seg_id}",
                    'results': []
                }

            candidate_ids = None
            need_prefilter = (
                prefilter_features
                or include_tags
                or exclude_tags
                or exclude_ids
            )

            if need_prefilter:
                async with self._acquire() as conn:
                    _, prefilter = self._make_helpers(conn)
                    candidate_ids = await prefilter.get_filtered_candidates(
                        target_seg_id,
                        features_to_use=prefilter_features,
                        include_tags=include_tags,
                        exclude_tags=exclude_tags,
                        exclude_ids=exclude_ids,
                    )
                    segment_candidates = await prefilter._filter_only_segments(candidate_ids)
                    logger.info(f"[Pre-Filter Segment] {len(segment_candidates)} candidates")
                    if not segment_candidates:
                        return {'error': 'No candidates after pre-filter', 'results': []}
                    candidate_ids = segment_candidates

            async def _one_mode(mode: str):
                async with self._acquire() as conn:
                    shape, _ = self._make_helpers(conn)
                    results = await shape.search_by_embedding(
                        target_id=target_seg_id,
                        mode=mode,
                        limit=search_limit,
                        candidate_ids=candidate_ids,
                        only_segments=True,
                    )
                return mode, results

            mode_tuples = await asyncio.gather(*[_one_mode(m) for m in available_modes])
            rankings = dict(mode_tuples)

            fused = self.ranker.fuse_rankings(rankings, weights)
            final = fused[:limit]

            async with self._acquire() as conn:
                enriched = await self._enrich_results(final, conn, metric)

            return {
                'target': target_seg_id,
                'results': enriched,
                'metadata': {'modes': available_modes, 'weights': weights},
            }

        except Exception as e:
            logger.error(f"Error searching segments for {target_seg_id}: {e}")
            return {'error': str(e), 'results': []}

    # =========================================================================
    # PRIVATE — HELPERS
    # =========================================================================

    async def _enrich_results(
            self,
            results: List[Dict],
            conn: asyncpg.Connection,
            metric: str = 'sidtw',
    ) -> List[Dict]:
        if not results:
            return []

        allowed_metrics = {'sidtw', 'qdtw'}
        if metric not in allowed_metrics:
            metric = 'sidtw'

        metric_table = f"evaluation.{metric}_info"
        seg_ids = [r['seg_id'] for r in results]

        try:
            query = f"""
                SELECT
                    bm.seg_id, bm.traj_id, bm.duration, bm.weight, bm.length,
                    bm.movement_type, bm.mean_vel, bm.max_vel, bm.std_vel,
                    bm.min_accel, bm.mean_accel, bm.max_accel, bm.std_accel,
                    bm.position_x, bm.position_y, bm.position_z,
                    mi.{metric}_min_distance,
                    mi.{metric}_average_distance,
                    mi.{metric}_max_distance
                FROM motion.traj_metadata bm
                LEFT JOIN {metric_table} mi ON bm.seg_id = mi.seg_id
                WHERE bm.seg_id = ANY($1)
            """
            metadata_rows = await conn.fetch(query, seg_ids)
            metadata_lookup = {row['seg_id']: dict(row) for row in metadata_rows}

            for row_dict in metadata_lookup.values():
                row_dict['min_distance']  = row_dict.pop(f'{metric}_min_distance', None)
                row_dict['mean_distance'] = row_dict.pop(f'{metric}_average_distance', None)
                row_dict['max_distance']  = row_dict.pop(f'{metric}_max_distance', None)

            enriched = []
            for result in results:
                seg_id = result['seg_id']
                if seg_id in metadata_lookup:
                    result['features'] = metadata_lookup[seg_id]
                enriched.append(result)

            return enriched

        except Exception as e:
            logger.error(f"Error enriching results: {e}")
            return results

    async def _get_traj_id(self, target_id: str) -> Optional[str]:
        try:
            async with self._acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT traj_id FROM motion.traj_metadata WHERE seg_id = $1",
                    target_id
                )
                return result['traj_id'] if result else None
        except Exception as e:
            logger.error(f"Error getting traj_id for {target_id}: {e}")
            return None

    async def _get_traj_segments(self, traj_id: str) -> List[str]:
        try:
            async with self._acquire() as conn:
                results = await conn.fetch(
                    """
                    SELECT seg_id FROM motion.traj_metadata
                    WHERE traj_id = $1 AND seg_id != traj_id
                    ORDER BY seg_id
                    """,
                    traj_id
                )
                return [row['seg_id'] for row in results]
        except Exception as e:
            logger.error(f"Error getting segments for traj {traj_id}: {e}")
            return []

    async def _get_features(self, seg_id: str, metric: str = 'sidtw') -> Optional[Dict]:
        allowed_metrics = {'sidtw', 'qdtw'}
        if metric not in allowed_metrics:
            metric = 'sidtw'

        metric_table = f"evaluation.{metric}_info"

        try:
            async with self._acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    SELECT
                        bm.seg_id, bm.traj_id, bm.duration, bm.weight, bm.length,
                        bm.movement_type, bm.mean_vel, bm.max_vel, bm.std_vel,
                        bm.min_accel, bm.mean_accel, bm.max_accel, bm.std_accel,
                        bm.position_x, bm.position_y, bm.position_z,
                        mi.{metric}_min_distance     AS min_distance,
                        mi.{metric}_average_distance AS mean_distance,
                        mi.{metric}_max_distance     AS max_distance
                    FROM motion.traj_metadata bm
                    LEFT JOIN {metric_table} mi ON bm.seg_id = mi.seg_id
                    WHERE bm.seg_id = $1
                    """,
                    seg_id,
                )
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting features for {seg_id}: {e}")
            return None


# ── Candidate (unsaved) variant ───────────────────────────────────────────

class MultiModalSearcherCandidate(MultiModalSearcher):
    """
    Variant of MultiModalSearcher for unsaved, simulated candidates.
    The QUERY-side embedding comes from an injected dict instead of a DB lookup.
    Only segment-level search runs — candidates have no whole-trajectory aggregate.

    Previously lived in multi_modal_ext.py as MultiModalSearcherExternal.
    """

    def __init__(
        self,
        conn_or_pool:         Union[asyncpg.Pool, asyncpg.Connection],
        candidate_embeddings: Dict[str, list],
        candidate_id:         str,
    ):
        super().__init__(conn_or_pool)
        self._candidate_embeddings = candidate_embeddings
        self._candidate_id         = candidate_id

    def _make_helpers(self, conn: asyncpg.Connection):
        return (
            ShapeSearcherCandidate(conn, self._candidate_embeddings, self._candidate_id),
            FilterSearcher(conn),
        )

    async def search_similar(
        self,
        target_id: str,
        modes: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        prefilter_features: Optional[List[str]] = None,
        limit: int = 10,
        metric: str = 'sidtw',
        buffer_factor: int = 5,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
    ) -> Dict:
        modes              = modes or ['joint', 'position', 'orientation', 'velocity', 'metadata']
        weights            = weights or {m: 1.0 for m in modes}
        prefilter_features = prefilter_features or []

        seg_result = await self._search_segments(
            target_seg_id=self._candidate_id,
            modes=modes, weights=weights, limit=limit,
            prefilter_features=prefilter_features, metric=metric,
            buffer_factor=buffer_factor, include_tags=include_tags,
            exclude_tags=exclude_tags, exclude_ids=exclude_ids,
        )

        return {
            'target_id':            target_id,
            'target_traj_id':       self._candidate_id,
            'target_traj_features': None,
            'modes':                modes,
            'weights':              weights,
            'metric':               metric,
            'traj_similarity':      {'results': []},
            'segment_similarity':   [{
                'target_segment':          self._candidate_id,
                'target_segment_features': None,
                'similar_segments':        seg_result,
            }],
            'metadata': {'target_segments_count': 1},
        }