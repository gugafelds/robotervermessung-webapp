# backend/app/api/endpoints/search_route_handler.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
import logging
import time

from ...database import get_db, get_db_pool
from ...utils.multimodal_framework.multi_modal_searcher import MultiModalSearcher
from ...utils.trajectory_loader import TrajectoryLoader
from ...utils.multimodal_framework.dtw_reranker import rerank

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/search/{target_id}")
async def search_similar(
        target_id: str,
        # --- Stage 1 parameters ---
        modes: Optional[str] = Query(
            None,
            description="Comma-separated modalities: joint,position,orientation,velocity,metadata"
        ),
        joint_weight: float = Query(1.0, ge=0.0, le=1.0),
        position_weight: float = Query(1.0, ge=0.0, le=1.0),
        orientation_weight: float = Query(1.0, ge=0.0, le=1.0),
        velocity_weight: float = Query(1.0, ge=0.0, le=1.0),
        metadata_weight: float = Query(1.0, ge=0.0, le=1.0),
        limit: int = Query(10, ge=1, le=100),
        prefilter_features: Optional[str] = Query(
            None,
            description="Comma-separated prefilter features: length,duration,movement_type,position_3d"
        ),
        # --- Stage 2 parameters ---
        stage2_active: bool = Query(False, description="Enable DTW reranking (Stage 2)"),
        dtw_mode: Literal["position", "joint"] = Query(
            "position",
            description="DTW alignment domain: 'position' (3D Cartesian) or 'joint' (6D joint space)"
        ),
        pool=Depends(get_db_pool),
        conn=Depends(get_db)
):
    """
    Two-Stage Trajectory Similarity Search

    **Stage 1** (always): pgvector HNSW embedding search with RRF fusion
    across up to 5 modalities (position, joint, orientation, velocity, metadata).
    Runs s+1 searches: one for the full trajectory + one per segment.

    **Stage 2** (optional, stage2_active=true): cDTW reranking of Stage 1
    candidates for both trajectory-level and segment-level results.

    Example:
        GET /search/similar/1765989370?limit=10&stage2_active=true&dtw_mode=position
    """
    try:
        t_start = time.time()

        # ── Parse parameters ─────────────────────────────────────────────
        mode_list = [m.strip() for m in modes.split(',')] if modes else None

        weights = {
            'joint':       joint_weight,
            'position':    position_weight,
            'orientation': orientation_weight,
            'velocity':    velocity_weight,
            'metadata':    metadata_weight,
        }

        prefilter_list = []
        if prefilter_features:
            prefilter_list = [f.strip() for f in prefilter_features.split(',') if f.strip()]
            allowed = {'length', 'duration', 'movement_type', 'position_3d',
                       'velocity_profile', 'acceleration_profile'}
            invalid = [f for f in prefilter_list if f not in allowed]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid prefilter features: {invalid}. Allowed: {list(allowed)}"
                )

        # ── Stage 1: MultiModalSearcher ──────────────────────────────────
        t1 = time.time()
        searcher = MultiModalSearcher(pool)
        result = await searcher.search_similar(
            target_id=target_id,
            modes=mode_list,
            weights=weights,
            limit=limit,
            prefilter_features=prefilter_list,
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        stage1_ms = (time.time() - t1) * 1000

        # rank → rank_stage1 für Konsistenz mit späterem rank_stage2
        for r in result.get('traj_similarity', {}).get('results', []):
            if 'rank' in r:
                r['rank_stage1'] = r.pop('rank')
        for group in result.get('segment_similarity', []):
            for r in group.get('similar_segments', {}).get('results', []):
                if 'rank' in r:
                    r['rank_stage1'] = r.pop('rank')

        result['timing'] = {'stage1_ms': round(stage1_ms, 1)}

        # ── Stage 2: DTW reranking (optional) ────────────────────────────
        if not stage2_active:
            result['stage2_active'] = False
            result['timing']['total_ms'] = round((time.time() - t_start) * 1000, 1)
            return result

        t2 = time.time()
        loader = TrajectoryLoader(conn)
        data_load_ms = 0.0

        # ── Trajectory-level reranking ────────────────────────────────────
        traj_results = result.get('traj_similarity', {}).get('results', [])

        if traj_results:
            traj_candidate_ids = [r['seg_id'] for r in traj_results]

            # Load query trajectory
            t_load = time.time()
            query_traj_data = await loader.load_trajectory_data(target_id, dtw_mode)

            if query_traj_data is not None:
                # Load all candidates at once
                candidates_traj = await loader.load_trajectories_batch(
                    traj_candidate_ids, dtw_mode
                )
                data_load_ms = (time.time() - t_load) * 1000

                # Flatten to {id: array}
                candidates_flat = {
                    traj_id: data['trajectory']
                    for traj_id, data in candidates_traj.items()
                }

                t_dtw = time.time()
                dtw_traj = rerank(
                    query_seq=query_traj_data['trajectory'],
                    candidates=candidates_flat,
                    limit=limit,
                    mode=dtw_mode,
                )

                # Merge DTW results back into traj_similarity
                # keeping existing enriched features, just updating rank + distance
                dtw_lookup = {r['id']: r for r in dtw_traj}
                enriched_traj = []
                for r in traj_results:
                    sid = r['seg_id']
                    if sid in dtw_lookup:
                        r['dtw_distance'] = dtw_lookup[sid]['dtw_distance']
                        r['similarity_score'] = dtw_lookup[sid]['similarity_score']
                        r['rank_stage2'] = dtw_lookup[sid]['rank']
                    enriched_traj.append(r)

                # Re-sort by DTW distance
                enriched_traj.sort(key=lambda x: x.get('dtw_distance', float('inf')))
                result['traj_similarity']['results'] = enriched_traj

        # ── Segment-level reranking ───────────────────────────────────────
        # Segment-IDs haben Format "<traj_id>_<n>" (z.B. "1769774562_1")
        # TrajectoryLoader lädt nach traj_id → wir parsen die traj_id heraus
        # und greifen dann auf data['segments'][seg_id] zu.

        def seg_id_to_traj_id(seg_id: str) -> str:
            """'1769774562_1'  →  '1769774562'"""
            return seg_id.rsplit('_', 1)[0]

        segment_groups = result.get('segment_similarity', [])

        # Alle benötigten traj_ids für Segment-Kandidaten vorab sammeln
        # und in einem einzigen Batch-Query laden
        all_seg_traj_ids: set = set()
        for group in segment_groups:
            for r in group.get('similar_segments', {}).get('results', []):
                all_seg_traj_ids.add(seg_id_to_traj_id(r['seg_id']))
        # Query-traj_id selbst auch laden (enthält Query-Segmente)
        all_seg_traj_ids.add(target_id)

        seg_batch = await loader.load_trajectories_batch(
            list(all_seg_traj_ids), dtw_mode
        )

        for group in segment_groups:
            query_seg_id = group['target_segment']          # z.B. "1769774547_1"
            query_traj_id_local = seg_id_to_traj_id(query_seg_id)
            seg_results = group.get('similar_segments', {}).get('results', [])

            if not seg_results:
                continue

            # Query-Segment-Array aus Batch-Ergebnis holen
            query_traj_data = seg_batch.get(query_traj_id_local)
            if query_traj_data is None:
                logger.warning(f"Query traj not found in batch: {query_traj_id_local}")
                continue

            query_arr = query_traj_data['segments'].get(query_seg_id)
            if query_arr is None:
                logger.warning(f"Query segment not found: {query_seg_id}")
                continue

            # Kandidaten-Arrays aufbauen: {seg_id: array}
            candidates_seg_flat = {}
            for r in seg_results:
                cand_seg_id = r['seg_id']                # z.B. "1769774562_1"
                cand_traj_id = seg_id_to_traj_id(cand_seg_id)
                cand_traj_data = seg_batch.get(cand_traj_id)
                if cand_traj_data is None:
                    continue
                cand_arr = cand_traj_data['segments'].get(cand_seg_id)
                if cand_arr is not None:
                    candidates_seg_flat[cand_seg_id] = cand_arr

            if not candidates_seg_flat:
                logger.warning(f"No candidate arrays found for segment group {query_seg_id}")
                continue

            dtw_seg = rerank(
                query_seq=query_arr,
                candidates=candidates_seg_flat,
                limit=limit,
                mode=dtw_mode,
            )

            # Merge DTW-Ergebnisse zurück
            dtw_seg_lookup = {r['id']: r for r in dtw_seg}
            enriched_seg = []
            for r in seg_results:
                sid = r['seg_id']
                if sid in dtw_seg_lookup:
                    r['dtw_distance'] = dtw_seg_lookup[sid]['dtw_distance']
                    r['similarity_score'] = dtw_seg_lookup[sid]['similarity_score']
                    r['rank_stage2'] = dtw_seg_lookup[sid]['rank']
                enriched_seg.append(r)

            enriched_seg.sort(key=lambda x: x.get('dtw_distance', float('inf')))
            group['similar_segments']['results'] = enriched_seg

        stage2_ms = (time.time() - t2) * 1000
        result['stage2_active'] = True
        result['stage2_dtw_mode'] = dtw_mode
        result['timing']['data_loading_ms'] = round(data_load_ms, 1)
        result['timing']['stage2_ms'] = round(stage2_ms, 1)
        result['timing']['total_ms'] = round((time.time() - t_start) * 1000, 1)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search for {target_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))