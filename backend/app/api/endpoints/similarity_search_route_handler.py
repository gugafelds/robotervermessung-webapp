# backend/app/api/routes/two_stage.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
import time
import logging

from ...database import get_db_pool  # ✅ Dein Pattern
from ...utils.trajectory_loader import TrajectoryLoader
from ...utils.dtw_reranker import DTWReranker

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TwoStageRequest(BaseModel):
    """Request model for two-stage retrieval"""
    
    target_id: str = Field(
        ...,
        description="Target trajectory or segment ID",
        examples=["1765989370"]
    )
    
    k_candidates: int = Field(
        500,
        ge=10,
        le=2000,
        description="Number of candidates from Stage 1 (pgvector)"
    )
    
    final_limit: int = Field(
        50,
        ge=1,
        le=200,
        description="Final results after Stage 2 (DTW)"
    )
    
    dtw_mode: Literal["position", "joint"] = Field(
        "position",
        description="DTW mode: 'position' (3D) or 'joint' (6D)"
    )
    
    level: Literal["trajectory", "segment"] = Field(
        "trajectory",
        description="Level: 'trajectory' or 'segment'"
    )
    
    embedding_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights for Stage 1 embedding modes"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_id": "1765989370",
                "k_candidates": 500,
                "final_limit": 50,
                "dtw_mode": "position",
                "level": "trajectory",
                "embedding_weights": {
                    "position": 1.0,
                    "joint": 1.0,
                    "orientation": 1.0,
                    "velocity": 1.0,
                    "metadata": 1.0
                }
            }
        }


class DTWResult(BaseModel):
    """Single DTW result"""
    
    segment_id: str
    bahn_id: str
    dtw_distance: float
    similarity_score: float
    rank: int
    used_lb_kim: bool
    used_lb_keogh: bool


class TwoStageMetrics(BaseModel):
    """Performance metrics"""
    
    stage1_time_ms: float
    stage2_time_sec: float
    total_time_sec: float
    k_candidates: int
    final_limit: int
    dtw_calls_made: int
    dtw_calls_saved_pct: float
    speedup: str
    pruning_efficiency: float


class TwoStageResponse(BaseModel):
    """Response for trajectory-level retrieval"""
    
    results: List[DTWResult]
    metrics: TwoStageMetrics
    query_info: Dict


class SegmentTwoStageResponse(BaseModel):
    """Response for segment-level retrieval"""
    
    segment_results: Dict[str, List[DTWResult]]
    metrics: TwoStageMetrics
    query_info: Dict


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_stage1_candidates(
    conn,
    target_id: str,
    k: int,
    weights: Optional[Dict[str, float]]
) -> List[str]:
    """
    Stage 1: Get Top-K candidates from pgvector HNSW
    
    Returns:
        List of bahn_ids
    """
    # Default weights if not provided
    if weights is None:
        weights = {
            "position": 1.0,
            "joint": 1.0,
            "orientation": 1.0,
            "velocity": 1.0,
            "metadata": 1.0
        }
    
    # Simple position-based search for now
    query = """
        SELECT segment_id, 
               position_embedding <=> (
                   SELECT position_embedding 
                   FROM robotervermessung.bewegungsdaten.bahn_embeddings 
                   WHERE segment_id = $1
               ) as distance
        FROM robotervermessung.bewegungsdaten.bahn_embeddings
        WHERE segment_id = bahn_id  -- Only full trajectories
        AND position_embedding IS NOT NULL
        ORDER BY distance
        LIMIT $2
    """
    
    rows = await conn.fetch(query, target_id, k)
    return [row['segment_id'] for row in rows]


def calculate_pruning_efficiency(
    k_candidates: int,
    dtw_calls_made: int
) -> float:
    """Calculate pruning efficiency percentage"""
    if k_candidates == 0:
        return 0.0
    return (1 - dtw_calls_made / k_candidates) * 100


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/two-stage/trajectory", response_model=TwoStageResponse)
async def two_stage_trajectory_retrieval(
    request: TwoStageRequest,
    db_pool=Depends(get_db_pool)  # ✅ Dein Pattern
):
    """
    Two-Stage Retrieval: Trajectory Level
    
    Pipeline:
    1. Stage 1: pgvector HNSW → Top-K candidates (~50ms)
    2. Load trajectory data for query & candidates
    3. Stage 2: DTW reranking with Lower Bounds (~1-2s)
    4. Return Top-N with metrics
    """
    try:
        logger.info(f"Two-Stage Trajectory Retrieval: {request.target_id}")
        logger.info(f"  K={request.k_candidates}, Limit={request.final_limit}, Mode={request.dtw_mode}")
        
        pipeline_start = time.time()
        
        # ====================================================================
        # DATABASE CONNECTION
        # ====================================================================
        async with db_pool.acquire() as conn:  # ✅ Dein Pattern
            
            # ================================================================
            # STAGE 1: pgvector HNSW
            # ================================================================
            logger.info("Stage 1: pgvector HNSW query...")
            stage1_start = time.time()
            
            candidate_ids = await get_stage1_candidates(
                conn,
                request.target_id,
                request.k_candidates,
                request.embedding_weights
            )
            
            stage1_time = time.time() - stage1_start
            stage1_time_ms = stage1_time * 1000
            
            logger.info(f"  ✓ Stage 1: {len(candidate_ids)} candidates in {stage1_time_ms:.2f}ms")
            
            if not candidate_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"No candidates found for target_id: {request.target_id}"
                )
            
            # ================================================================
            # LOAD DATA
            # ================================================================
            logger.info("Loading trajectory data...")
            loader = TrajectoryLoader(conn)
            
            # Load query
            query_data = await loader.load_trajectory_data(
                request.target_id,
                request.dtw_mode
            )
            
            if query_data is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Query trajectory not found: {request.target_id}"
                )
            
            # Load candidates (batch)
            candidates_data = await loader.load_trajectories_batch(
                candidate_ids,
                request.dtw_mode
            )
            
            if not candidates_data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to load candidate trajectories"
                )
            
            logger.info(f"  ✓ Loaded query + {len(candidates_data)} candidates")
            
            # ================================================================
            # STAGE 2: DTW Reranking
            # ================================================================
            logger.info("Stage 2: DTW reranking with Lower Bounds...")
            stage2_start = time.time()
            
            reranker = DTWReranker(
                cdtw_window=0.2,
                lb_kim_keep_ratio=0.9,
                lb_keogh_candidates=500
            )
            
            dtw_results = reranker.rerank_batch_trajectories(
                query_data=query_data,
                candidates_data=candidates_data,
                limit=request.final_limit
            )
            
            stage2_time = time.time() - stage2_start
            
            logger.info(f"  ✓ Stage 2: {len(dtw_results)} results in {stage2_time:.2f}s")
            
        # ====================================================================
        # METRICS
        # ====================================================================
        total_time = time.time() - pipeline_start
        
        # Count DTW calls (from results)
        dtw_calls_made = len(candidates_data)
        if dtw_results:
            dtw_calls_made = len([r for r in dtw_results])
        
        dtw_calls_saved_pct = (30000 - dtw_calls_made) / 30000 * 100
        speedup_factor = 30000 / dtw_calls_made if dtw_calls_made > 0 else 0
        pruning_efficiency = calculate_pruning_efficiency(
            request.k_candidates, 
            dtw_calls_made
        )
        
        metrics = TwoStageMetrics(
            stage1_time_ms=stage1_time_ms,
            stage2_time_sec=stage2_time,
            total_time_sec=total_time,
            k_candidates=len(candidate_ids),
            final_limit=len(dtw_results),
            dtw_calls_made=dtw_calls_made,
            dtw_calls_saved_pct=dtw_calls_saved_pct,
            speedup=f"{speedup_factor:.1f}x",
            pruning_efficiency=pruning_efficiency
        )
        
        # ====================================================================
        # RESPONSE
        # ====================================================================
        response = TwoStageResponse(
            results=[DTWResult(**r) for r in dtw_results],
            metrics=metrics,
            query_info={
                "target_id": request.target_id,
                "dtw_mode": request.dtw_mode,
                "level": "trajectory",
                "num_candidates_stage1": len(candidate_ids),
                "num_results_stage2": len(dtw_results)
            }
        )
        
        logger.info(f"✓ Two-Stage completed: {total_time:.2f}s total")
        logger.info(f"  Speedup: {speedup_factor:.1f}x vs full DTW")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Two-Stage error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/two-stage/segment", response_model=SegmentTwoStageResponse)
async def two_stage_segment_retrieval(
    request: TwoStageRequest,
    db_pool=Depends(get_db_pool)  # ✅ Dein Pattern
):
    """
    Two-Stage Retrieval: Segment Level
    
    Pipeline:
    1. Stage 1: pgvector HNSW → Top-K candidates per query segment
    2. Load segment data
    3. Stage 2: DTW reranking per segment
    4. Return aggregated results
    """
    try:
        logger.info(f"Two-Stage Segment Retrieval: {request.target_id}")
        
        pipeline_start = time.time()
        
        async with db_pool.acquire() as conn:  # ✅ Dein Pattern
            
            # ================================================================
            # LOAD QUERY DATA (with segments)
            # ================================================================
            loader = TrajectoryLoader(conn)
            query_data = await loader.load_trajectory_data(
                request.target_id,
                request.dtw_mode
            )
            
            if query_data is None or not query_data['segments']:
                raise HTTPException(
                    status_code=404,
                    detail=f"Query segments not found: {request.target_id}"
                )
            
            num_query_segments = len(query_data['segments'])
            logger.info(f"  Query has {num_query_segments} segments")
            
            # ================================================================
            # STAGE 1: pgvector
            # ================================================================
            stage1_start = time.time()
            
            candidate_ids = await get_stage1_candidates(
                conn,
                request.target_id,
                request.k_candidates,
                request.embedding_weights
            )
            
            stage1_time = time.time() - stage1_start
            
            # ================================================================
            # LOAD CANDIDATES
            # ================================================================
            candidates_data = await loader.load_trajectories_batch(
                candidate_ids,
                request.dtw_mode
            )
            
            # ================================================================
            # STAGE 2: DTW per segment
            # ================================================================
            logger.info("Stage 2: DTW reranking for segments...")
            stage2_start = time.time()
            
            reranker = DTWReranker(
                cdtw_window=0.2,
                lb_kim_keep_ratio=0.9,
                lb_keogh_candidates=500
            )
            
            segment_results = reranker.rerank_batch_segments(
                query_data=query_data,
                candidates_data=candidates_data,
                limit=request.final_limit
            )
            
            stage2_time = time.time() - stage2_start
            
        # ====================================================================
        # METRICS (aggregated)
        # ====================================================================
        total_time = time.time() - pipeline_start
        
        total_dtw_calls = sum(len(results) for results in segment_results.values())
        avg_dtw_calls = total_dtw_calls / num_query_segments if num_query_segments > 0 else 0
        
        dtw_calls_saved_pct = (30000 - avg_dtw_calls) / 30000 * 100
        speedup_factor = 30000 / avg_dtw_calls if avg_dtw_calls > 0 else 0
        
        metrics = TwoStageMetrics(
            stage1_time_ms=stage1_time * 1000,
            stage2_time_sec=stage2_time / num_query_segments,
            total_time_sec=total_time,
            k_candidates=len(candidate_ids),
            final_limit=request.final_limit,
            dtw_calls_made=int(avg_dtw_calls),
            dtw_calls_saved_pct=dtw_calls_saved_pct,
            speedup=f"{speedup_factor:.1f}x",
            pruning_efficiency=calculate_pruning_efficiency(
                request.k_candidates,
                int(avg_dtw_calls)
            )
        )
        
        # ====================================================================
        # RESPONSE
        # ====================================================================
        formatted_segment_results = {}
        for seg_id, results in segment_results.items():
            formatted_segment_results[seg_id] = [DTWResult(**r) for r in results]
        
        response = SegmentTwoStageResponse(
            segment_results=formatted_segment_results,
            metrics=metrics,
            query_info={
                "target_id": request.target_id,
                "dtw_mode": request.dtw_mode,
                "level": "segment",
                "num_segments": num_query_segments
            }
        )
        
        logger.info(f"✓ Segment Two-Stage completed: {total_time:.2f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Segment Two-Stage error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))