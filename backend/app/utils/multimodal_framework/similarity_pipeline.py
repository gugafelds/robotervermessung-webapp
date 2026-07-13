"""
similarity_pipeline.py
=======================
Two-stage trajectory similarity search with optional prognosis.

Used by:
  - FastAPI search endpoint  (similarity_route_handler.py)
  - FastAPI candidate endpoint (similarity_candidate_route_handler.py) — external/unsaved candidates
  - Offline calibration builder (calibration_set_builder.py)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Literal, Optional

import asyncpg

from .multi_modal_searcher import MultiModalSearcher, MultiModalSearcherCandidate
from ..metadata_embeddings.trajectory_loader import TrajectoryLoader, TrajectoryLoaderCandidate
from ..metadata_embeddings.embedding_calculator import build_candidate_embeddings, build_candidate_embeddings_segmented, CANDIDATE_SEG_ID
from ..feature_prediction.predictor import predict_performance
from .dtw_reranker import rerank

logger = logging.getLogger(__name__)


def _seg_id_to_traj_id(seg_id: str) -> str:
    return seg_id.rsplit('_', 1)[0]


def _normalize_stage1_ranks(result: Dict[str, Any]) -> None:
    for r in result.get('traj_similarity', {}).get('results', []):
        if 'rank' in r and 'rank_stage1' not in r:
            r['rank_stage1'] = r.pop('rank')
    for group in result.get('segment_similarity', []):
        for r in group.get('similar_segments', {}).get('results', []):
            if 'rank' in r and 'rank_stage1' not in r:
                r['rank_stage1'] = r.pop('rank')


async def run_similarity_pipeline(
    *,
    target_id: Optional[str] = None,
    pool: asyncpg.Pool,
    conn: asyncpg.Connection,

    # External candidate (unsaved, simulated) — mutually exclusive with target_id
    external_payload:              Optional[Dict[str, Any]] = None,
    external_embedding_calculator: Optional[Any]            = None,

    # Stage 1
    modes:              Optional[List[str]]        = None,
    weights:            Optional[Dict[str, float]] = None,
    limit:              int                        = 10,
    buffer_factor:      int                        = 5,
    prefilter_features: Optional[List[str]]        = None,
    metric:             Literal['sidtw', 'qdtw']   = 'sidtw',
    include_tags:       Optional[List[str]]        = None,
    exclude_tags:       Optional[List[str]]        = None,
    exclude_ids:        Optional[List[str]]        = None,

    # Stage 2
    stage2_active: bool                         = False,
    dtw_mode:      Literal['position', 'joint'] = 'position',

    # Prognosis
    prognosis_active: bool  = False,
    calibration_tag:  str   = 'all',
    coverage:         float = 0.90,
    conformal_active: bool  = True,
) -> Dict[str, Any]:
    t_start = time.time()

    is_external = external_payload is not None
    if is_external:
        target_id = CANDIDATE_SEG_ID
        if prefilter_features:
            raise ValueError("prefilter_features is not supported for external candidates")
    elif target_id is None:
        raise ValueError("Either target_id or external_payload must be provided")

    if prefilter_features is None:
        prefilter_features = []

    # ── Stage 1 ──────────────────────────────────────────────────────────
    t1 = time.time()

    if is_external:
        segment_indices = external_payload.get('segment_indices')  # NEU

        if segment_indices:
            # ── Multi-Segment Kandidat ────────────────────────────────────
            rows = build_candidate_embeddings_segmented(
                external_payload, external_embedding_calculator, segment_indices
            )
            if rows is None:
                return {
                    'error': 'Could not compute segment embeddings for external candidate.',
                    'traj_similarity': {}, 'segment_similarity': [],
                }

            full_row = rows[0]
            seg_rows = rows[1:]

            full_embeddings = {
                'joint':       full_row['joint_embedding'],
                'position':    full_row['position_embedding'],
                'orientation': full_row['orientation_embedding'],
                'velocity':    full_row['velocity_embedding'],
                'metadata':    full_row['metadata_embedding'],
            }

            segment_embeddings_map = {
                row['seg_id']: {
                    'joint':       row['joint_embedding'],
                    'position':    row['position_embedding'],
                    'orientation': row['orientation_embedding'],
                    'velocity':    row['velocity_embedding'],
                    'metadata':    row['metadata_embedding'],
                }
                for row in seg_rows
            }

            searcher = MultiModalSearcherCandidate(
                pool,
                full_embeddings,
                CANDIDATE_SEG_ID,
                segment_embeddings_map=segment_embeddings_map,
            )

        else:
            embedding_row = build_candidate_embeddings(external_payload, external_embedding_calculator)
            if embedding_row is None:
                return {
                    'error': 'Could not compute embeddings for external candidate (too few points?)',
                    'traj_similarity': {}, 'segment_similarity': [],
                }

            external_embeddings = {
                'joint':       embedding_row['joint_embedding'],
                'position':    embedding_row['position_embedding'],
                'orientation': embedding_row['orientation_embedding'],
                'velocity':    embedding_row['velocity_embedding'],
                'metadata':    embedding_row['metadata_embedding'],
            }
            searcher = MultiModalSearcherCandidate(pool, external_embeddings, CANDIDATE_SEG_ID)

    else:
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
        result['timing']       = {'stage1_ms': round(stage1_ms, 1), 'total_ms': round((time.time() - t_start) * 1000, 1)}
        result['stage2_active'] = False
        return result

    _normalize_stage1_ranks(result)
    result['timing'] = {'stage1_ms': round(stage1_ms, 1)}

    # ── Stage 1 only ─────────────────────────────────────────────────────
    if not stage2_active:
        result['stage2_active'] = False
        if prognosis_active:
            result = await predict_performance(
            result=result, seg_batch={}, conn=conn,
            feature='mean_distance', coverage=coverage,
            calibration_tag=calibration_tag,
            conformal_active=conformal_active,
            k=limit,
            search_modes=tuple(sorted(modes or [])),
            dtw_mode=dtw_mode,
            metric=metric,
        )
        result['timing']['total_ms'] = round((time.time() - t_start) * 1000, 1)
        return result

    # ── Stage 2: DTW reranking ───────────────────────────────────────────
    t2 = time.time()
    loader       = TrajectoryLoader(conn)   # immer der echte Loader — lädt DB-Kandidaten
    data_load_ms = 0.0
    candidates_traj: Dict[str, Any] = {}
    seg_batch:       Dict[str, Any] = {}

    traj_results = result.get('traj_similarity', {}).get('results', [])
    if traj_results:
        traj_candidate_ids = [r['seg_id'] for r in traj_results if r.get('seg_id')]
        t_load = time.time()
        query_traj_data = await loader.load_trajectory_data(target_id, dtw_mode)

        if query_traj_data is not None and traj_candidate_ids:
            candidates_traj = await loader.load_trajectories_batch(traj_candidate_ids, dtw_mode)
            data_load_ms   += (time.time() - t_load) * 1000

            candidates_flat = {
                tid: data['trajectory']
                for tid, data in candidates_traj.items()
                if data is not None and data.get('trajectory') is not None
            }
            if candidates_flat:
                dtw_traj   = rerank(query_seq=query_traj_data['trajectory'],
                                    candidates=candidates_flat, limit=limit, mode=dtw_mode)
                dtw_lookup = {r['id']: r for r in dtw_traj}
                enriched   = []
                for r in traj_results:
                    sid = r.get('seg_id')
                    if sid in dtw_lookup:
                        r['dtw_distance']     = dtw_lookup[sid]['dtw_distance']
                        r['similarity_score'] = dtw_lookup[sid]['similarity_score']
                        r['rank_stage2']      = dtw_lookup[sid]['rank']
                    enriched.append(r)
                enriched.sort(key=lambda x: x.get('dtw_distance', float('inf')))
                result['traj_similarity']['results'] = enriched

    segment_groups = result.get('segment_similarity', [])
    all_seg_traj_ids: set = set() if is_external else {target_id}
    for group in segment_groups:
        for r in group.get('similar_segments', {}).get('results', []):
            cid = r.get('seg_id')
            if cid:
                all_seg_traj_ids.add(_seg_id_to_traj_id(cid))

    if all_seg_traj_ids:
        t_load    = time.time()
        seg_batch = await loader.load_trajectories_batch(list(all_seg_traj_ids), dtw_mode)
        data_load_ms += (time.time() - t_load) * 1000

    # Query-Segment des externen Kandidaten separat laden und in seg_batch
    # einspeisen — unter demselben Key, den _seg_id_to_traj_id() für das
    # Query-Segment liefern würde (bei uns: EXTERNAL_SEG_ID selbst, da
    # seg_id == traj_id für einen einzelnen externen Kandidaten).
    if is_external:
        segment_indices = external_payload.get('segment_indices')

        if segment_indices:
            boundaries = [0] + segment_indices
            traj = external_payload['trajectory']

            for i, group in enumerate(segment_groups):
                seg_id = group.get('target_segment')
                if seg_id is None:
                    continue

                start = boundaries[i]
                end   = boundaries[i + 1] + 1

                seg_payload = {
                    "trajectory": {
                        "timestamps": traj['timestamps'][start:end],
                        "positions":  traj['positions'][start:end],
                        "quats":      traj.get('quats', [])[start:end],
                        "joints":     traj.get('joints', [])[start:end],
                    },
                    "movement_type": external_payload['movement_type'],
                    "weight":        external_payload['weight'],
                }

                ext_loader = TrajectoryLoaderCandidate(seg_payload, candidate_seg_id=seg_id)
                ext_data   = await ext_loader.load_trajectory_data(seg_id, dtw_mode)
                if ext_data is not None:
                    seg_batch[seg_id] = ext_data

        else:
            ext_loader = TrajectoryLoaderCandidate(external_payload)
            ext_data   = await ext_loader.load_trajectory_data(target_id, dtw_mode)
            if ext_data is not None:
                seg_batch[target_id] = ext_data
    
    logger.info("[pipeline DEBUG] seg_batch keys: %s", list(seg_batch.keys()))
    logger.info("[pipeline DEBUG] segment_groups target_segments: %s",
                    [g.get('target_segment') for g in segment_groups])

    for group in segment_groups:
        query_seg_id = group.get('target_segment')

        logger.info("[pipeline DEBUG] entering group loop: query_seg_id=%s", query_seg_id)
    
        seg_results = group.get('similar_segments', {}).get('results', [])
        logger.info("[pipeline DEBUG] seg_results count=%d", len(seg_results))

        if not seg_results:
            logger.info("[pipeline DEBUG] skipping — no seg_results")
            continue
        
        query_traj_data = seg_batch.get(_seg_id_to_traj_id(query_seg_id))
        if query_traj_data is None and is_external:
            query_traj_data = seg_batch.get(query_seg_id)
        
        logger.info("[pipeline DEBUG] query_traj_data found=%s", query_traj_data is not None)
        
        query_arr = (query_traj_data.get('segments') or {}).get(query_seg_id) if query_traj_data else None
        logger.info("[pipeline DEBUG] query_arr=%s", query_arr.shape if query_arr is not None else None)

        if not query_seg_id:
            continue
        seg_results = group.get('similar_segments', {}).get('results', [])
        if not seg_results:
            continue
        query_traj_data = seg_batch.get(_seg_id_to_traj_id(query_seg_id))
        if query_traj_data is None and is_external:
            query_traj_data = seg_batch.get(query_seg_id)
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
            cand_data = seg_batch.get(_seg_id_to_traj_id(cand_seg_id))
            if cand_data is None:
                continue
            cand_arr = (cand_data.get('segments') or {}).get(cand_seg_id)
            if cand_arr is not None:
                candidates_seg_flat[cand_seg_id] = cand_arr

        if not candidates_seg_flat:
            continue

        dtw_seg     = rerank(query_seq=query_arr, candidates=candidates_seg_flat,
                             limit=limit, mode=dtw_mode)
        
        logger.info("[pipeline DEBUG] dtw_seg count=%d, first=%s", 
                    len(dtw_seg),
                    dtw_seg[0] if dtw_seg else None)
        
        dtw_seg_lup = {r['id']: r for r in dtw_seg}
        
        logger.info("[pipeline DEBUG] dtw_seg_lup keys sample=%s", 
                    list(dtw_seg_lup.keys())[:3])
        logger.info("[pipeline DEBUG] seg_results ids sample=%s",
                    [r.get('seg_id') for r in seg_results[:3]])

        dtw_seg_lup = {r['id']: r for r in dtw_seg}
        enriched    = []
        for r in seg_results:
            sid = r.get('seg_id')
            if sid in dtw_seg_lup:
                r['dtw_distance']     = dtw_seg_lup[sid]['dtw_distance']
                r['similarity_score'] = dtw_seg_lup[sid]['similarity_score']
                r['rank_stage2']      = dtw_seg_lup[sid]['rank']
            enriched.append(r)
        enriched.sort(key=lambda x: x.get('dtw_distance', float('inf')))
        group['similar_segments']['results'] = enriched

    stage2_ms = (time.time() - t2) * 1000
    result['stage2_active']   = True
    result['stage2_dtw_mode'] = dtw_mode

    # ── Prognosis ────────────────────────────────────────────────────────
    if prognosis_active:
        result = await predict_performance(
            result=result,
            seg_batch=seg_batch or {},
            conn=conn,
            feature='mean_distance',
            coverage=coverage,
            calibration_tag=calibration_tag,
            conformal_active=conformal_active,
            k=limit,
            search_modes=tuple(sorted(modes or [])),
            dtw_mode=dtw_mode,
            metric=metric,
        )

    result['timing']['data_loading_ms'] = round(data_load_ms, 1)
    result['timing']['stage2_ms']       = round(stage2_ms, 1)
    result['timing']['total_ms']        = round((time.time() - t_start) * 1000, 1)

    return result