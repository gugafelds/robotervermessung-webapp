from fastapi import Depends, HTTPException, Query
from typing import Optional, Literal
import logging
import time
import sys

sys.path.append(
    r"\robotervermessung-webapp\backend\app"
)

from database import get_db, get_db_pool
from multi_modal_searcher_gen import MultiModalSearcherGen
from trajectory_loader_gen import TrajectoryLoaderGen
from utils.multimodal_framework.dtw_reranker import rerank

logger = logging.getLogger(__name__)

async def search_similar(
        target: str,
        # --- Stage 1 parameters ---
        limit: int = Query(10, ge=1, le=100),
        prefilter_features: Optional[str] = Query(
            None,
            description="Comma-separated prefilter features: length,duration,movement_type,position_3d"
        ),
        stage2_active: bool = Query(False, description="Enable DTW reranking (Stage 2)"),
        metric: Literal["sidtw", "qdtw"] = Query(                        
            "sidtw",                                                       
            description="Evaluation metric for prognosis: 'sidtw' or 'qdtw'"  
        ),                                                                 
        pool=Depends(get_db_pool),
        conn=Depends(get_db)
):
    try:
        dtw_mode = 'position'
        t_start = time.time()

        # ── Parse parameters ─────────────────────────────────────────────
        """prefilter_list = []
        if prefilter_features:
            prefilter_list = [f.strip() for f in prefilter_features.split(',') if f.strip()]
            allowed = {'length', 'duration', 'movement_type', 'position_3d',
                       'velocity_profile', 'acceleration_profile'}
            invalid = [f for f in prefilter_list if f not in allowed]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid prefilter features: {invalid}. Allowed: {list(allowed)}"
                )"""
            
        # ── Stage 1: MultiModalSearcher ──────────────────────────────────
        t1 = time.time()
        searcher = MultiModalSearcherGen(pool)
        result = await searcher.search_similar(
            target_id=target,
            modes=['position'],
            limit=limit,
            #sprefilter_features=prefilter_list,
            metric=metric,                                                 
        )

        if result.get('error'):
            print("result: ", result)
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
        loader = TrajectoryLoaderGen(conn)
        data_load_ms = 0.0

        # ── Trajectory-level reranking ────────────────────────────────────
        traj_results = result.get('traj_similarity', {}).get('results', [])

        if traj_results:
            traj_candidate_ids = [r['seg_id'] for r in traj_results]

            t_load = time.time()
            query_traj_data = await loader.load_trajectory_data(target, dtw_mode)

            if query_traj_data is not None:
                candidates_traj = await loader.load_trajectories_batch(
                    traj_candidate_ids, dtw_mode
                )
                data_load_ms = (time.time() - t_load) * 1000

                candidates_flat = {
                    traj_id: data['trajectory']
                    for traj_id, data in candidates_traj.items()
                }

                dtw_traj = rerank(
                    query_seq=query_traj_data['trajectory'],
                    candidates=candidates_flat,
                    limit=limit,
                    mode=dtw_mode,
                )

                dtw_lookup = {r['id']: r for r in dtw_traj}
                enriched_traj = []
                for r in traj_results:
                    sid = r['seg_id']
                    if sid in dtw_lookup:
                        r['dtw_distance'] = dtw_lookup[sid]['dtw_distance']
                        r['similarity_score'] = dtw_lookup[sid]['similarity_score']
                        r['rank_stage2'] = dtw_lookup[sid]['rank']
                    enriched_traj.append(r)

                enriched_traj.sort(key=lambda x: x.get('dtw_distance', float('inf')))
                result['traj_similarity']['results'] = enriched_traj

        # ── Segment-level reranking ───────────────────────────────────────
        def seg_id_to_traj_id(seg_id: str, fallback_traj_id: Optional[str] = None) -> str:
            if isinstance(seg_id, str) and seg_id.strip().startswith('['):
                return fallback_traj_id if fallback_traj_id is not None else seg_id
            return seg_id.rsplit('_', 1)[0] if '_' in seg_id else seg_id

        segment_groups = result.get('segment_similarity', [])

        all_seg_traj_ids: set = set()
        for group in segment_groups:
            for r in group.get('similar_segments', {}).get('results', []):
                all_seg_traj_ids.add(seg_id_to_traj_id(r['seg_id'], target))
        all_seg_traj_ids.add(target)

        seg_batch = await loader.load_trajectories_batch(
            list(all_seg_traj_ids), dtw_mode
        )

        for group in segment_groups:
            query_seg_id = group['target_segment']
            query_traj_id_local = seg_id_to_traj_id(query_seg_id, target)
            seg_results = group.get('similar_segments', {}).get('results', [])

            if not seg_results:
                continue

            query_traj_data = seg_batch.get(query_traj_id_local)
            if query_traj_data is None:
                logger.warning(f"Query traj not found in batch: {query_traj_id_local}")
                continue

            query_arr = query_traj_data['segments'].get(query_seg_id)
            if query_arr is None:
                logger.warning(f"Query segment not found: {query_seg_id}")
                continue

            candidates_seg_flat = {}
            for r in seg_results:
                cand_seg_id = r['seg_id']
                cand_traj_id = seg_id_to_traj_id(cand_seg_id, target)
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
        logger.error(f"Error in similarity search for {target}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))