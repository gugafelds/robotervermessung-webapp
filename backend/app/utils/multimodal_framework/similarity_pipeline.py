# backend/app/utils/similarity_pipeline.py

from __future__ import annotations

import inspect
import logging
import time
from typing import Any, Dict, List, Optional, Literal

import asyncpg

from .multi_modal_searcher import MultiModalSearcher
from ..metadata_embeddings.trajectory_loader import TrajectoryLoader
from ..feature_prediction.predictor import predict_performance
from .dtw_reranker import rerank

logger = logging.getLogger(__name__)


def _seg_id_to_traj_id(seg_id: str) -> str:
    return seg_id.rsplit('_', 1)[0]


def _normalize_stage1_ranks(result: Dict[str, Any]) -> None:
    """
    Convert generic `rank` from Stage 1 into `rank_stage1`.

    This keeps Stage 1 ranks stable after Stage 2 adds `rank_stage2`.
    """
    for r in result.get('traj_similarity', {}).get('results', []):
        if 'rank' in r and 'rank_stage1' not in r:
            r['rank_stage1'] = r.pop('rank')

    for group in result.get('segment_similarity', []):
        for r in group.get('similar_segments', {}).get('results', []):
            if 'rank' in r and 'rank_stage1' not in r:
                r['rank_stage1'] = r.pop('rank')


async def _run_prediction(
    *,
    result: Dict[str, Any],
    seg_batch: Dict[str, Any],
    conn: asyncpg.Connection,
    traj_batch: Optional[Dict[str, Any]],
    metric: str,
    coverage: float,
    conformal_active: bool,
) -> Dict[str, Any]:
    """
    Small compatibility wrapper.

    If predictor.py already supports `conformal_active`, pass it.
    If not, call the current signature.
    """
    kwargs = {
        'result': result,
        'seg_batch': seg_batch,
        'conn': conn,
        'traj_batch': traj_batch,
        'feature': 'mean_distance',
        'coverage': coverage,
    }

    signature = inspect.signature(predict_performance)
    if 'conformal_active' in signature.parameters:
        kwargs['conformal_active'] = conformal_active

    return await predict_performance(**kwargs)


async def run_similarity_pipeline(
    *,
    target_id: str,
    pool: asyncpg.Pool,
    conn: asyncpg.Connection,

    # Stage 1
    modes: Optional[List[str]] = None,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 10,
    buffer_factor: int = 5,
    prefilter_features: Optional[List[str]] = None,
    metric: Literal['sidtw', 'qdtw'] = 'sidtw',
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    exclude_ids: Optional[List[str]] = None,

    # Stage 2
    stage2_active: bool = False,
    dtw_mode: Literal['position', 'joint'] = 'position',

    # Prognosis
    prognosis_active: bool = False,
    conformal_active: bool = True,
    coverage: float = 0.90,
) -> Dict[str, Any]:
    """
    Shared search/prognosis pipeline.

    Used by:
      - FastAPI search endpoint
      - offline calibration builder later

    Responsibilities:
      1. Run Stage 1 multimodal embedding search with RRF.
      2. Optionally run Stage 2 DTW reranking.
      3. Optionally attach performance prognosis.
      4. Optionally attach conformal intervals when Stage 2 is active.
    """
    t_start = time.time()

    if prefilter_features is None:
        prefilter_features = []

    # ── Stage 1: MultiModalSearcher ──────────────────────────────────────
    t1 = time.time()

    searcher = MultiModalSearcher(pool)
    result = await searcher.search_similar(
        target_id=target_id,
        modes=modes,
        weights=weights,
        limit=limit,
        buffer_factor=buffer_factor,
        prefilter_features=prefilter_features,
        metric=metric,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        exclude_ids=exclude_ids,
    )

    stage1_ms = (time.time() - t1) * 1000

    if result.get('error'):
        result['timing'] = {
            'stage1_ms': round(stage1_ms, 1),
            'total_ms': round((time.time() - t_start) * 1000, 1),
        }
        result['stage2_active'] = False
        return result

    _normalize_stage1_ranks(result)

    result['timing'] = {
        'stage1_ms': round(stage1_ms, 1),
    }

    # ── Stage 1 only: optional prognosis, no conformal ───────────────────
    if not stage2_active:
        result['stage2_active'] = False

        if prognosis_active:
            result = await _run_prediction(
                result=result,
                seg_batch={},
                traj_batch=None,
                conn=conn,
                metric=metric,
                coverage=coverage,
                conformal_active=False,
            )

        result['timing']['total_ms'] = round((time.time() - t_start) * 1000, 1)
        return result

    # From this point on, Stage 2 is active.
    # Set this BEFORE predict_performance(), otherwise predictor.py may use
    # Stage-1/RRF prediction logic instead of DTW prediction logic.
    result['stage2_active'] = True
    result['stage2_dtw_mode'] = dtw_mode

    # ── Stage 2: DTW reranking ───────────────────────────────────────────
    t2 = time.time()

    loader = TrajectoryLoader(conn)
    data_load_ms = 0.0
    candidates_traj: Dict[str, Any] = {}
    seg_batch: Dict[str, Any] = {}

    # ── Trajectory-level reranking ───────────────────────────────────────
    traj_results = result.get('traj_similarity', {}).get('results', [])

    if traj_results:
        traj_candidate_ids = [r['seg_id'] for r in traj_results if r.get('seg_id')]

        t_load = time.time()

        query_traj_data = await loader.load_trajectory_data(target_id, dtw_mode)

        if query_traj_data is not None and traj_candidate_ids:
            candidates_traj = await loader.load_trajectories_batch(
                traj_candidate_ids,
                dtw_mode,
            )
            data_load_ms += (time.time() - t_load) * 1000

            candidates_flat = {
                traj_id: data['trajectory']
                for traj_id, data in candidates_traj.items()
                if data is not None and data.get('trajectory') is not None
            }

            if candidates_flat:
                dtw_traj = rerank(
                    query_seq=query_traj_data['trajectory'],
                    candidates=candidates_flat,
                    limit=limit,
                    mode=dtw_mode,
                )

                dtw_lookup = {r['id']: r for r in dtw_traj}

                enriched_traj = []
                for r in traj_results:
                    sid = r.get('seg_id')
                    if sid in dtw_lookup:
                        r['dtw_distance'] = dtw_lookup[sid]['dtw_distance']
                        r['similarity_score'] = dtw_lookup[sid]['similarity_score']
                        r['rank_stage2'] = dtw_lookup[sid]['rank']
                    enriched_traj.append(r)

                enriched_traj.sort(key=lambda x: x.get('dtw_distance', float('inf')))
                result['traj_similarity']['results'] = enriched_traj

    # ── Segment-level reranking ──────────────────────────────────────────
    segment_groups = result.get('segment_similarity', [])

    all_seg_traj_ids: set[str] = set()
    all_seg_traj_ids.add(target_id)

    for group in segment_groups:
        for r in group.get('similar_segments', {}).get('results', []):
            cand_seg_id = r.get('seg_id')
            if cand_seg_id:
                all_seg_traj_ids.add(_seg_id_to_traj_id(cand_seg_id))

    if all_seg_traj_ids:
        t_load = time.time()
        seg_batch = await loader.load_trajectories_batch(
            list(all_seg_traj_ids),
            dtw_mode,
        )
        data_load_ms += (time.time() - t_load) * 1000

    for group in segment_groups:
        query_seg_id = group.get('target_segment')
        if not query_seg_id:
            continue

        query_traj_id_local = _seg_id_to_traj_id(query_seg_id)
        seg_results = group.get('similar_segments', {}).get('results', [])

        if not seg_results:
            continue

        query_traj_data = seg_batch.get(query_traj_id_local)
        if query_traj_data is None:
            continue

        query_arr = (query_traj_data.get('segments') or {}).get(query_seg_id)
        if query_arr is None:
            continue

        candidates_seg_flat = {}

        for r in seg_results:
            cand_seg_id = r.get('seg_id')
            if not cand_seg_id:
                continue

            cand_traj_id = _seg_id_to_traj_id(cand_seg_id)
            cand_traj_data = seg_batch.get(cand_traj_id)
            if cand_traj_data is None:
                continue

            cand_arr = (cand_traj_data.get('segments') or {}).get(cand_seg_id)
            if cand_arr is not None:
                candidates_seg_flat[cand_seg_id] = cand_arr

        if not candidates_seg_flat:
            continue

        dtw_seg = rerank(
            query_seq=query_arr,
            candidates=candidates_seg_flat,
            limit=limit,
            mode=dtw_mode,
        )

        dtw_seg_lookup = {r['id']: r for r in dtw_seg}

        enriched_seg = []
        for r in seg_results:
            sid = r.get('seg_id')
            if sid in dtw_seg_lookup:
                r['dtw_distance'] = dtw_seg_lookup[sid]['dtw_distance']
                r['similarity_score'] = dtw_seg_lookup[sid]['similarity_score']
                r['rank_stage2'] = dtw_seg_lookup[sid]['rank']
            enriched_seg.append(r)

        enriched_seg.sort(key=lambda x: x.get('dtw_distance', float('inf')))
        group['similar_segments']['results'] = enriched_seg

    stage2_ms = (time.time() - t2) * 1000

    # ── Prognosis after Stage 2 ──────────────────────────────────────────
    if prognosis_active:
        result = await _run_prediction(
            result=result,
            seg_batch=seg_batch or {},
            traj_batch=candidates_traj or {},
            conn=conn,
            metric=metric,
            coverage=coverage,
            conformal_active=conformal_active,
        )

    result['timing']['data_loading_ms'] = round(data_load_ms, 1)
    result['timing']['stage2_ms'] = round(stage2_ms, 1)
    result['timing']['total_ms'] = round((time.time() - t_start) * 1000, 1)

    return result