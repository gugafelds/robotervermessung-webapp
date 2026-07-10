# backend/app/api/endpoints/correction_route_handler.py
"""
correction_route_handler.py
============================
POST /api/correction/predict

Nimmt eine SimulatedTrajectory entgegen, führt eine multimodale
Ähnlichkeitssuche durch und berechnet eine gewichtete Korrektur
[dx, dy, dz] pro Segment.

Basiert auf dem Korrekturansatz von [Name Studentin] — die Logik der
gewichteten Mittelung (1/dtw) und der Abweichungsberechnung aus
sidtw_evaluation wurde direkt übernommen und in die Backend-Pipeline
integriert.
"""

import asyncio
from typing import List, Literal, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...database import get_db, get_db_pool
from ...utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline
from ...utils.metadata_embeddings.embedding_calculator import EmbeddingCalculator

import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────

class CorrectionTrajectory(BaseModel):
    timestamps: List[float]
    positions:  List[List[float]]
    quats:      List[List[float]]
    joints:     List[List[float]]


class CorrectionRequest(BaseModel):
    trajectory:      CorrectionTrajectory
    movement_type:   str
    weight:          float = Field(..., description="Payload in kg")
    robot_model:     str   = Field(..., description="e.g. abb_irb4400")
    limit:           int   = 5
    mode:            Literal["relative", "linear"] = "relative"
    segment_indices: list[int] = []


class CorrectionResponse(BaseModel):
    corrections: List[List[float]]  # [[dx, dy, dz], ...] — one per segment


# ── Helpers ───────────────────────────────────────────────────────────────

async def _get_segment_data(conn, seg_id: str, n: int = 10):
    """
    Holt die letzten n Punkte aus sidtw_evaluation für ein Segment
    und berechnet die mittlere Abweichung in x, y, z.

    Direkt übernommen aus dem Korrekturskript (get_segment_data Funktion).
    """
    query = """
        SELECT sidtw_act_x, sidtw_cmd_x,
               sidtw_act_y, sidtw_cmd_y,
               sidtw_act_z, sidtw_cmd_z
        FROM evaluation.sidtw_evaluation
        WHERE seg_id = $1
        ORDER BY points_order DESC
        LIMIT $2
    """
    result = await conn.fetch(query, seg_id, n)

    if not result:
        return None

    x_diff, y_diff, z_diff = 0.0, 0.0, 0.0
    for row in result:
        x_diff += float(row["sidtw_act_x"] - row["sidtw_cmd_x"])
        y_diff += float(row["sidtw_act_y"] - row["sidtw_cmd_y"])
        z_diff += float(row["sidtw_act_z"] - row["sidtw_cmd_z"])

    n_rows = len(result)
    return x_diff / n_rows, y_diff / n_rows, z_diff / n_rows


async def _fetch_robot_info(conn, robot_model: str) -> Optional[Dict]:
    row = await conn.fetchrow("""
        SELECT vel_max, accel_max, max_payload, reach_xy, reach_z_max, reach_z_min
        FROM motion.robot_info
        WHERE robot_model = $1
    """, robot_model)
    return dict(row) if row else None

async def _get_all_segment_data(conn, seg_ids: list[str], last_points: int = 10) -> dict:
    """
    Holt alle Segment-Daten in einem einzigen Query.
    Direkt übernommen aus dem Korrekturskript (get_segment_data Funktion).
    """
    query = """
        SELECT seg_id, sidtw_deviation, sidtw_cmd_x, sidtw_cmd_y, sidtw_cmd_z,
               sidtw_act_x, sidtw_act_y, sidtw_act_z
        FROM (
            SELECT seg_id, sidtw_deviation, sidtw_cmd_x, sidtw_cmd_y, sidtw_cmd_z,
                   sidtw_act_x, sidtw_act_y, sidtw_act_z,
                   ROW_NUMBER() OVER (
                       PARTITION BY seg_id
                       ORDER BY points_order DESC
                   ) AS rn
            FROM evaluation.sidtw_evaluation
            WHERE seg_id = ANY($1::text[])
        ) t
        WHERE rn <= $2
        ORDER BY seg_id, rn;
    """
    result = await conn.fetch(query, seg_ids, last_points)

    data = {}
    for row in result:
        sid   = str(row["seg_id"])
        x_diff = float(row["sidtw_act_x"] - row["sidtw_cmd_x"]) / last_points
        y_diff = float(row["sidtw_act_y"] - row["sidtw_cmd_y"]) / last_points
        z_diff = float(row["sidtw_act_z"] - row["sidtw_cmd_z"]) / last_points

        if sid in data:
            data[sid][0] += x_diff
            data[sid][1] += y_diff
            data[sid][2] += z_diff
        else:
            data[sid] = [x_diff, y_diff, z_diff]

    return data


# ── Endpoint ──────────────────────────────────────────────────────────────

@router.post("/predict", response_model=CorrectionResponse)
async def predict_correction(
    request: CorrectionRequest,
    pool=Depends(get_db_pool),
    conn=Depends(get_db),
):
    try:
        robot_info = await _fetch_robot_info(conn, request.robot_model)
        if robot_info is None:
            logger.warning(f"robot_model '{request.robot_model}' not found — using fallback.")

        embedding_calculator = EmbeddingCalculator(n_samples=10, robot_info=robot_info)

        # ── Ein einziger Pipeline-Aufruf — intern segmentweise ────────────
        similarity_result = await run_similarity_pipeline(
            external_payload={
                "trajectory": {
                    "timestamps": request.trajectory.timestamps,
                    "positions":  request.trajectory.positions,
                    "quats":      request.trajectory.quats,
                    "joints":     request.trajectory.joints,
                },
                "movement_type":  request.movement_type,
                "weight":         request.weight,
                "segment_indices": request.segment_indices,
            },
            external_embedding_calculator=embedding_calculator,
            pool=pool,
            conn=conn,
            modes=["position", "joint", "orientation", "velocity", "metadata"],
            limit=request.limit,
            stage2_active=True,
            dtw_mode="position",
            metric="sidtw",
            prognosis_active=False,
        )

        if similarity_result.get("error"):
            raise HTTPException(status_code=422, detail=similarity_result["error"])

        # ── Alle IDs auf einmal sammeln ───────────────────────────────────
        seg_groups = similarity_result.get("segment_similarity", [])
        all_ids = []
        for group in seg_groups:
            for s in group.get("similar_segments", {}).get("results", []):
                if s.get("seg_id"):
                    all_ids.append(s["seg_id"])

        query_data = await _get_all_segment_data(conn, all_ids)

        # ── Korrektur pro Segment ────────────────────
        corrections = []
        eps = 1e-9

        for group in seg_groups:
            similar_segments = group.get("similar_segments", {}).get("results", [])

            x_diffs, y_diffs, z_diffs, dtw_distances = [], [], [], []

            for s in similar_segments:
                seg_id = s.get("seg_id")
                dtw    = s.get("dtw_distance")
                if seg_id is None or dtw is None:
                    continue
                res = query_data.get(str(seg_id))
                if res is None:
                    continue
                x_diffs.append(res[0])
                y_diffs.append(res[1])
                z_diffs.append(res[2])
                dtw_distances.append(float(dtw))

            if not x_diffs:
                corrections.append([0.0, 0.0, 0.0])
                continue

            x_corr, y_corr, z_corr = 0.0, 0.0, 0.0

            if request.mode == "linear":
                k          = len(x_diffs)
                weight_sum = (k * (k + 1)) / 2
                for i in range(k):
                    w       = (k - i) / weight_sum
                    x_corr += w * x_diffs[i]
                    y_corr += w * y_diffs[i]
                    z_corr += w * z_diffs[i]
            else:
                inverse_dtw   = [1.0 / (d + eps) for d in dtw_distances]
                total_inverse = sum(inverse_dtw)
                weights_dtw   = [v / total_inverse for v in inverse_dtw]
                for i, w in enumerate(weights_dtw):
                    x_corr += w * x_diffs[i]
                    y_corr += w * y_diffs[i]
                    z_corr += w * z_diffs[i]

            corrections.append([x_corr, y_corr, z_corr])

        logger.info(
            "[correction] %d segments processed, %d corrections computed.",
            len(seg_groups), len(corrections),
        )

        return CorrectionResponse(corrections=corrections)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in correction prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))