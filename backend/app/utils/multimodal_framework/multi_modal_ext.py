# backend/app/utils/multimodal_framework/multi_modal_searcher_external.py
from typing import Dict, List, Optional
import asyncpg
from .multi_modal_searcher import MultiModalSearcher
from .filter_searcher import FilterSearcher
from .shape_searcher_ext import ShapeSearcherExternal


class MultiModalSearcherExternal(MultiModalSearcher):
    """
    Same as MultiModalSearcher, except the QUERY-side embedding comes
    from an injected dict (external_embeddings) instead of a DB lookup,
    and search_similar() skips the DB target-id resolution entirely
    (there is no traj_id to resolve — the candidate isn't saved).

    Since one request = one segment (see external_embedding_builder.py),
    only segment-level search runs; traj_similarity (direct-level) stays
    empty — external candidates don't have a 'whole trajectory' aggregate.
    """
    def __init__(self, conn_or_pool, external_embeddings: Dict[str, list], external_id: str):
        super().__init__(conn_or_pool)
        self._external_embeddings = external_embeddings
        self._external_id         = external_id

    def _make_helpers(self, conn: asyncpg.Connection):
        return (
            ShapeSearcherExternal(conn, self._external_embeddings, self._external_id),
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
        modes    = modes or ['joint', 'position', 'orientation', 'velocity', 'metadata']
        weights  = weights or {m: 1.0 for m in modes}
        prefilter_features = prefilter_features or []

        seg_result = await self._search_segments(
            target_seg_id=self._external_id,
            modes=modes,
            weights=weights,
            limit=limit,
            prefilter_features=prefilter_features,
            metric=metric,
            buffer_factor=buffer_factor,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            exclude_ids=exclude_ids,
        )

        return {
            'target_id':             target_id,
            'target_traj_id':        self._external_id,
            'target_traj_features':  None,   # keine Evaluationsdaten — Kandidat wurde nie gemessen
            'modes':                 modes,
            'weights':                weights,
            'metric':                 metric,
            'traj_similarity':        {'results': []},   # kein direct-Level für externe Kandidaten
            'segment_similarity':     [{
                'target_segment':          self._external_id,
                'target_segment_features': None,
                'similar_segments':        seg_result,
            }],
            'metadata': {'target_segments_count': 1},
        }