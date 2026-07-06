# backend/app/api/endpoints/similarity_candidate_route_handler.py
"""
similarity_candidate_route_handler.py
========================================
POST endpoint for searching against an UNSAVED, simulated candidate
(from the recorder's RoboDK-based PointGenerator) instead of an
existing traj_id in the database. See:
  - trajectory_loader_external.py   (Stage 2 DTW data)
  - external_embedding_builder.py   (Stage 1 embeddings)
  - multi_modal_searcher_external.py (Stage 1 search with injected embedding)
"""

from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...database import get_db, get_db_pool
from ...utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline
from ...utils.metadata_embeddings.embedding_calculator import EmbeddingCalculator

import logging
import math

logger = logging.getLogger(__name__)
router = APIRouter()


class CandidateTrajectory(BaseModel):
    timestamps: List[float]
    positions:  List[List[float]]   # [[x, y, z], ...]
    quats:      List[List[float]]   # [[qw, qx, qy, qz], ...]
    joints:     List[List[float]]   # [[j1..j6], ...]


class SearchCandidateRequest(BaseModel):
    trajectory:    CandidateTrajectory
    movement_type: str
    weight:        float = Field(..., description="Payload/end-effector weight in kg — required, no silent default")
    robot_model:   str   = Field(..., description="Must match an entry in motion.robot_info for embedding normalization")

    modes:              List[str]                    = ["position", "joint", "orientation", "velocity", "metadata"]
    weights:            Optional[Dict[str, float]]    = None
    dtw_mode:           Literal["position", "joint"]  = "position"
    metric:             Literal["sidtw", "qdtw"]      = "sidtw"
    calibration_tag:    str                           = "all"
    coverage:           float                         = 0.90
    limit:              int                           = 10
    stage2_active:      bool                          = True
    prognosis_active:   bool                          = True
    include_tags:       Optional[List[str]]           = None
    exclude_tags:       Optional[List[str]]           = None
    exclude_ids:        Optional[List[str]]            = None


async def _fetch_robot_info(conn, robot_model: str) -> Optional[Dict]:
    row = await conn.fetchrow("""
        SELECT vel_max, accel_max, max_payload, reach_xy, reach_z_max, reach_z_min
        FROM motion.robot_info
        WHERE robot_model = $1
    """, robot_model)
    return dict(row) if row else None


def _find_non_finite(obj, path="root"):
    """Recursively scans a dict/list for NaN/Infinity floats and returns their paths."""
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
    """NaN/Inf → None, rekursiv. Nötig weil manche DB-Segmente
    Null-Vektor orientation_embeddings haben → pgvector <=> gibt NaN."""
    if isinstance(obj, dict):
        return {k: _sanitize_non_finite(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_non_finite(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


@router.post("/search-candidate")
async def search_candidate(
    request: SearchCandidateRequest,
    pool=Depends(get_db_pool),
    conn=Depends(get_db),
):
    """
    Two-Stage Similarity Search against an unsaved, simulated candidate
    (e.g. a RoboDK-validated PointGenerator move that hasn't been
    physically measured yet).

    Same modes/prognosis/calibration semantics as GET /search/{target_id} —
    the only difference is that the QUERY side comes from this request
    body instead of an existing traj_id. prefilter_features is NOT
    supported here (no stored feature values to prefilter against).
    """
    try:
        robot_info = await _fetch_robot_info(conn, request.robot_model)
        if robot_info is None:
            logger.warning(f"robot_model '{request.robot_model}' not found — using fallback normalization values")

        embedding_calculator = EmbeddingCalculator(n_samples=10, robot_info=robot_info)

        external_payload = {
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
            external_payload=external_payload,
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

            stage2_active=request.stage2_active,
            dtw_mode=request.dtw_mode,

            prognosis_active=request.prognosis_active,
            calibration_tag=request.calibration_tag,
            coverage=request.coverage,
        )

        if result.get('error'):
            raise HTTPException(status_code=422, detail=result['error'])

        problems = _find_non_finite(result)
        if problems:
            logger.warning(
                f"[NaN-sanitize] {len(problems)} non-finite orientation distance(s) "
                f"— zero-vector embeddings in DB, sanitizing to None: "
                f"{[p for p, _ in problems[:5]]}"
            )
            result = _sanitize_non_finite(result)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in candidate similarity search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))