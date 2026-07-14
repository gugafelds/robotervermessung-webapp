# backend/app/api/endpoints/similarity_route_handler.py
"""
similarity_route_handler.py
=============================
Trajectory similarity search endpoints.

GET  /search/{target_id}   — search against an existing DB trajectory
POST /search/candidate     — search against an unsaved, simulated candidate
                             (from the recorder's RoboDK-based PointGenerator)

Both endpoints share the same pipeline (run_similarity_pipeline) and the
same modes/prognosis/calibration semantics. The only difference is the
QUERY side: an existing traj_id vs. an in-memory payload.

Previously the candidate endpoint lived in similarity_candidate_route_handler.py.
"""

import logging
import math
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...database import get_db, get_db_pool
from ...utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline
from ...utils.metadata_embeddings.embedding_calculator import EmbeddingCalculator

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared helpers ────────────────────────────────────────────────────────

def _find_non_finite(obj, path="root"):
    """Recursively finds NaN/Infinity floats and returns their paths."""
    issues = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            issues.extend(_find_non_finite(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            issues.extend(_find_non_finite(v, f"{path}[{i}]"))
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            issues.append((path, obj))
    return issues


def _sanitize_non_finite(obj):
    """
    NaN/Inf → None, rekursiv.
    Needed because some DB segments have zero-vector orientation embeddings
    — pgvector's <=> operator returns NaN for zero vectors.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_non_finite(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_non_finite(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


async def _fetch_robot_info(conn, robot_model: str) -> Optional[Dict]:
    row = await conn.fetchrow("""
        SELECT vel_max, accel_max, max_payload, reach_xy, reach_z_max, reach_z_min
        FROM motion.robot_info
        WHERE robot_model = $1
    """, robot_model)
    return dict(row) if row else None


def _sanitize_result(result: dict) -> dict:
    """Sanitize NaN/Inf in result and log if found."""
    problems = _find_non_finite(result)
    if problems:
        logger.warning(
            f"[NaN-sanitize] {len(problems)} non-finite value(s) in response "
            f"(likely zero-vector orientation embeddings in DB): "
            f"{[p for p, _ in problems[:5]]}"
        )
        result = _sanitize_non_finite(result)
    return result


# ── GET /search/{target_id} ───────────────────────────────────────────────

@router.get("/search/{target_id}")
async def search_trajectory(
        target_id: str,
        modes: Optional[str] = Query(
            None,
            description="Comma-separated modes: position, joint, orientation, velocity, metadata"
        ),
        joint_weight:       float = Query(1.0),
        position_weight:    float = Query(1.0),
        orientation_weight: float = Query(1.0),
        velocity_weight:    float = Query(1.0),
        metadata_weight:    float = Query(1.0),
        limit:              int   = Query(10, ge=1, le=100),
        prefilter_features: Optional[str] = Query(None),
        metric: Literal['sidtw', 'qdtw'] = Query('sidtw'),
        stage2_active:   bool = Query(False),
        dtw_mode: Literal['position', 'joint'] = Query('position'),
        prognosis_active: bool = Query(False),
        include_tags: Optional[str] = Query(None),
        exclude_tags: Optional[str] = Query(None),
        exclude_ids:  Optional[str] = Query(None),
        include_ids:  Optional[str] = Query(None),
        calibration_tag: Optional[str] = Query(
            'all',
            description=(
                "Comma-separated for multiple tags — quantile is weighted average by n_calibration. "
                "Use 'all' (default) for the full-DB calibration, or a specific tag "
                "e.g. 'bandit_v1' when searching within a tagged subset. "
                "Falls back to 'all' automatically if the specific tag has no calibration data."
            )
        ),
        coverage: float = Query(0.90, ge=0.5, le=0.99),
        pool=Depends(get_db_pool),
        conn=Depends(get_db),
):
    """
    Two-Stage Trajectory Similarity Search against an existing DB trajectory.

    **Stage 1** (always): pgvector HNSW embedding search with RRF fusion
    across up to 5 modalities (position, joint, orientation, velocity, metadata).

    **Stage 2** (optional, stage2_active=true): cDTW reranking of Stage 1 candidates.

    **Prognosis** (optional, prognosis_active=true): distance-weighted performance
    prediction with conformal intervals.

    Examples:
        GET /search/1765989370?limit=10&stage2_active=true&prognosis_active=true
        GET /search/1765989370?include_tags=bandit_v1&calibration_tag=bandit_v1
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
            [t for t in (t.strip() for t in include_tags.split(',')) if t and t != 'all']
            if include_tags else None
        ) or None
        exclude_tags_list = (
            [t.strip() for t in exclude_tags.split(',') if t.strip()]
            if exclude_tags else None
        )
        exclude_ids_list = (
            [i.strip() for i in exclude_ids.split(',') if i.strip()]
            if exclude_ids else None
        )
        include_ids_list = (
            [i.strip() for i in include_ids.split(',') if i.strip()]
            if include_ids else None
        )
        calibration_tags = (
            [t.strip() for t in calibration_tag.split(',') if t.strip()]
            if calibration_tag else ['all']
        )
        calibration_tag_param = calibration_tags if len(calibration_tags) > 1 else calibration_tags[0]

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
            include_ids=include_ids_list,
            stage2_active=stage2_active,
            dtw_mode=dtw_mode,
            prognosis_active=prognosis_active,
            calibration_tag=calibration_tag_param,
            coverage=coverage,
        )

        if result.get('error'):
            raise HTTPException(status_code=404, detail=result['error'])

        return _sanitize_result(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity search for {target_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /search/candidate ────────────────────────────────────────────────

class CandidateTrajectory(BaseModel):
    timestamps: List[float]
    positions:  List[List[float]]   # [[x, y, z], ...]
    quats:      List[List[float]]   # [[qw, qx, qy, qz], ...]
    joints:     List[List[float]]   # [[j1..j6], ...]


class SearchCandidateRequest(BaseModel):
    trajectory:    CandidateTrajectory
    movement_type: str
    weight:        float = Field(..., description="Payload weight in kg — required, no silent default")
    robot_model:   str   = Field(..., description="Must match motion.robot_info for embedding normalization")

    modes:           List[str]                   = ["position", "joint", "orientation", "velocity", "metadata"]
    weights:         Optional[Dict[str, float]]  = None
    dtw_mode:        Literal["position", "joint"] = "position"
    metric:          Literal["sidtw", "qdtw"]     = "sidtw"
    calibration_tag: str                          = "all"
    coverage:        float                        = 0.90
    limit:           int                          = 10
    stage2_active:   bool                         = True
    prognosis_active: bool                        = True
    include_tags:    Optional[List[str]]          = None
    exclude_tags:    Optional[List[str]]          = None
    exclude_ids:     Optional[List[str]]          = None
    include_ids:     Optional[List[str]]          = None


@router.post("/search/candidate")
async def search_candidate(
    request: SearchCandidateRequest,
    pool=Depends(get_db_pool),
    conn=Depends(get_db),
):
    """
    Two-Stage Similarity Search against an unsaved, simulated candidate
    (e.g. a RoboDK-validated PointGenerator move that hasn't been
    physically measured yet).

    Same modes/prognosis/calibration semantics as GET /search/{target_id}.
    prefilter_features is NOT supported here (no stored feature values).

    """
    try:
        robot_info = await _fetch_robot_info(conn, request.robot_model)
        if robot_info is None:
            logger.warning(
                f"robot_model '{request.robot_model}' not found in robot_info "
                f"— using fallback normalization values"
            )

        embedding_calculator = EmbeddingCalculator(n_samples=10, robot_info=robot_info)

        candidate_payload = {
            "trajectory": {
                "timestamps": request.trajectory.timestamps,
                "positions":  request.trajectory.positions,
                "quats":      request.trajectory.quats,
                "joints":     request.trajectory.joints,
            },
            "movement_type": request.movement_type,
            "weight":        request.weight,
        }

        weights = request.weights or {
            'joint': 1.0, 'position': 1.0, 'orientation': 1.0,
            'velocity': 1.0, 'metadata': 1.0,
        }

        result = await run_similarity_pipeline(
            external_payload=candidate_payload,
            external_embedding_calculator=embedding_calculator,
            pool=pool,
            conn=conn,
            modes=request.modes,
            weights=weights,
            limit=request.limit,
            buffer_factor=5,
            prefilter_features=[],
            metric=request.metric,
            include_tags=request.include_tags,
            exclude_tags=request.exclude_tags,
            exclude_ids=request.exclude_ids,
            include_ids=request.include_ids,
            stage2_active=request.stage2_active,
            dtw_mode=request.dtw_mode,
            prognosis_active=request.prognosis_active,
            calibration_tag=request.calibration_tag,
            coverage=request.coverage,
        )

        if result.get('error'):
            raise HTTPException(status_code=422, detail=result['error'])

        return _sanitize_result(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in candidate similarity search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))