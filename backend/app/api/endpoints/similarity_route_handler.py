# backend/app/api/endpoints/search_route_handler.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
import logging
import time

from ...database import get_db, get_db_pool
from ...utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search/{target_id}")
async def search_similar(
        target_id: str,
        # --- Stage 1 parameters ---
        modes: Optional[str] = Query(
            None,
            description="Comma-separated modalities: joint,position,orientation,velocity,metadata"
        ),
        joint_weight:       float = Query(1.0, ge=0.0, le=1.0),
        position_weight:    float = Query(1.0, ge=0.0, le=1.0),
        orientation_weight: float = Query(1.0, ge=0.0, le=1.0),
        velocity_weight:    float = Query(1.0, ge=0.0, le=1.0),
        metadata_weight:    float = Query(1.0, ge=0.0, le=1.0),
        limit: int = Query(10, ge=1, le=100),
        prefilter_features: Optional[str] = Query(
            None,
            description="Comma-separated prefilter features: length,duration,movement_type,position_3d"
        ),
        # --- Tag / ID Filter ---
        include_tags: Optional[str] = Query(
            None,
            description="Comma-separated tags — only trajectories WITH these tags are searched"
        ),
        exclude_tags: Optional[str] = Query(
            None,
            description="Comma-separated tags — trajectories WITH these tags are excluded"
        ),
        exclude_ids: Optional[str] = Query(
            None,
            description="Comma-separated traj_ids to exclude completely from search"
        ),
        # --- Stage 2 parameters ---
        stage2_active: bool = Query(False, description="Enable DTW reranking (Stage 2)"),
        dtw_mode: Literal["position", "joint"] = Query(
            "position",
            description="DTW alignment domain: 'position' (3D Cartesian) or 'joint' (6D joint space)"
        ),
        metric: Literal["sidtw", "qdtw"] = Query(
            "sidtw",
            description="Evaluation metric for prognosis: 'sidtw' or 'qdtw'"
        ),
        prognosis_active: bool = Query(False, description="Enable performance prognosis"),
        # --- Conformal interval parameters ---
        calibration_tag: str = Query(
            'all',
            description=(
                "Calibration context for conformal intervals. "
                "Use 'all' (default) for the full-DB calibration, or a specific tag "
                "e.g. 'bandit_v1' when searching within a tagged subset. "
                "Falls back to 'all' automatically if the specific tag has no calibration data."
            )
        ),
        coverage: float = Query(
            0.90,
            ge=0.5,
            le=0.99,
            description="Target coverage for conformal prediction interval, e.g. 0.90 = 90%"
        ),
        pool=Depends(get_db_pool),
        conn=Depends(get_db),
):
    """
    Two-Stage Trajectory Similarity Search

    **Stage 1** (always): pgvector HNSW embedding search with RRF fusion
    across up to 5 modalities (position, joint, orientation, velocity, metadata).

    **Tag / ID Filter** (optional): narrow the search space before Stage 1.
      - include_tags: only search within trajectories that have one of these tags
      - exclude_tags: skip trajectories that have one of these tags
      - exclude_ids:  skip specific trajectory IDs entirely

    **Stage 2** (optional, stage2_active=true): cDTW reranking of Stage 1 candidates.

    **Prognosis** (optional, prognosis_active=true): distance-weighted performance
    prediction with conformal intervals. Use calibration_tag to select the matching
    calibration context (defaults to 'all', falls back to 'all' if tag not found).

    Examples:
        GET /search/1765989370?limit=10&stage2_active=true&prognosis_active=true
        GET /search/1765989370?include_tags=bandit_v1&calibration_tag=bandit_v1&prognosis_active=true
        GET /search/1765989370?exclude_ids=1781022623,1763474797
    """
    try:
        mode_list = [m.strip() for m in modes.split(',')] if modes else None

        weights = {
            'joint':       joint_weight,
            'position':    position_weight,
            'orientation': orientation_weight,
            'velocity':    velocity_weight,
            'metadata':    metadata_weight,
        }

        prefilter_list: list = []
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

        include_tags_list = (
            [t.strip() for t in include_tags.split(',') if t.strip()]
            if include_tags else None
        )
        exclude_tags_list = (
            [t.strip() for t in exclude_tags.split(',') if t.strip()]
            if exclude_tags else None
        )
        exclude_ids_list = (
            [i.strip() for i in exclude_ids.split(',') if i.strip()]
            if exclude_ids else None
        )

        result = await run_similarity_pipeline(
            target_id=target_id,
            pool=pool,
            conn=conn,

            modes=mode_list,
            weights=weights,
            limit=limit,
            buffer_factor=5,
            prefilter_features=prefilter_list,
            metric=metric,

            include_tags=include_tags_list,
            exclude_tags=exclude_tags_list,
            exclude_ids=exclude_ids_list,

            stage2_active=stage2_active,
            dtw_mode=dtw_mode,

            prognosis_active=prognosis_active,
            calibration_tag=calibration_tag,
            coverage=coverage,
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search for {target_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))