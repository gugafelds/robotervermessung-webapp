"""
conformal_predictor.py
======================
Online conformal prediction interval computation.

Integrated into similarity_route_handler.py at the end of the Stage-2 block:

    from utils.conformal_calibration.conformal_predictor import (
        compute_conformal_intervals,
    )
    result = await compute_conformal_intervals(result, conn, strategy='decomposed')

Only called when stage2_active == True.

Key design decision:
    DTW distances from Stage 2 are normalized by query segment duration
    before weighting — consistent with calibration_set_builder_v3.py which
    uses distance_normalization='per_point'. Duration is used as a proxy
    for sequence length (proportional at constant sampling rate).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import asyncpg

from .conformal_config import (
    CalibrationConfig,
    RetrievalStrategy,
    get_active_config,
)

logger = logging.getLogger(__name__)

EPSILON     = 1e-6
DEFAULT_COV = 0.90


# ═════════════════════════════════════════════════════════════════════════════
# Quantile cache — one DB hit per (config_hash, coverage, level)
# ═════════════════════════════════════════════════════════════════════════════

_quantile_cache: Dict[str, float] = {}


async def get_calibration_quantile(
    conn:     asyncpg.Connection,
    cfg:      CalibrationConfig,
    coverage: float = DEFAULT_COV,
    level:    str   = 'trajectory',
) -> Optional[float]:
    """
    Read the stored conformal quantile for this exact config + coverage.
    Returns None when no matching row exists (calibration not yet run).
    """
    cache_key = f"{cfg.hash()}:{coverage}:{level}"
    if cache_key in _quantile_cache:
        return _quantile_cache[cache_key]

    row = await conn.fetchrow("""
        SELECT quantile_value
        FROM evaluation.confidence_quantiles
        WHERE config_hash        = $1
          AND coverage           = $2
          AND level              = $3
          AND retrieval_strategy = $4
        ORDER BY computed_at DESC
        LIMIT 1
    """, cfg.hash(), float(coverage), level, cfg.retrieval_strategy)

    if row is None:
        logger.warning(
            f"No conformal quantile found — "
            f"config_hash={cfg.hash()}  coverage={coverage}  "
            f"level={level}  strategy={cfg.retrieval_strategy}. "
            f"Run calibration_set_builder_v3.py first."
        )
        return None

    q = float(row['quantile_value'])
    _quantile_cache[cache_key] = q
    return q


# ═════════════════════════════════════════════════════════════════════════════
# Segment-level interval
# ═════════════════════════════════════════════════════════════════════════════

def _normalize_dtw(raw_dtw: float, query_duration: float) -> float:
    """
    Normalize raw DTW distance by query duration.

    This mirrors calibration_set_builder_v3.py with
    distance_normalization='per_point', using duration as a proxy
    for sequence length (valid at constant sampling rate).

    Builder uses: raw / max(len_query, len_candidate)
    Online uses:  raw / query_duration  (duration ∝ sequence_length)

    The absolute scale differs but the relative ordering and
    weighting ratios are preserved — which is what matters for
    inverse-DTW weighted prediction.
    """
    return raw_dtw / max(query_duration, EPSILON)


def _compute_segment_interval(
    seg_results:    List[Dict[str, Any]],
    q:              float,
    sigma_floor:    float,
    query_duration: float,
) -> Optional[Dict[str, Any]]:
    """
    Compute a conformal prediction interval for one segment.

    σ = max(std(neighbor_perf), sigma_floor)   — consistent with builder
    interval = [p̂ - q·σ,  p̂ + q·σ]

    DTW distances are normalized by query_duration before weighting
    to match the builder's per_point normalization.
    """
    valid = []
    for r in seg_results:
        raw_dtw   = r.get('dtw_distance')
        features  = r.get('features') or {}
        mean_dist = features.get('mean_distance')

        if raw_dtw is None or mean_dist is None:
            continue

        norm_dtw = _normalize_dtw(float(raw_dtw), query_duration)

        valid.append({
            'dtw_distance':  norm_dtw,
            'mean_distance': float(mean_dist),
        })

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])

    dtw_dists   = [v['dtw_distance']  for v in valid]
    perf_values = [v['mean_distance'] for v in valid]

    # Inverse-DTW weighted prediction — same as paper Eq. 3
    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    # σ — consistent with builder: perf_std with floor
    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    half = q * sigma

    return {
        'p_hat':    round(p_hat,                  4),
        'sigma':    round(sigma,                  6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half,           4),
        'coverage': DEFAULT_COV,
        'n':        n,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Trajectory-level aggregation (Decomposed)
# ═════════════════════════════════════════════════════════════════════════════

def _aggregate_trajectory_interval(
    seg_intervals: List[Dict[str, Any]],
    seg_durations: List[float],
    q:             float,
    sigma_floor:   float,
) -> Optional[Dict[str, Any]]:
    """
    Combine segment intervals into a trajectory interval.

    Length-weighted aggregation following paper Eq. p_gs:
      p̂_traj  = Σ (duration_i · p̂_i)   / Σ duration_i
      σ_traj   = max(Σ (duration_i · σ_i) / Σ duration_i, sigma_floor)
      interval = [p̂_traj - q·σ_traj,  p̂_traj + q·σ_traj]

    Note: q here is the trajectory-level quantile, not the segment one.
    """
    valid = [
        (iv, dur)
        for iv, dur in zip(seg_intervals, seg_durations)
        if iv is not None and dur is not None and dur > EPSILON
    ]
    if not valid:
        return None

    total = sum(dur for _, dur in valid)
    if total <= EPSILON:
        return None

    p_hat = sum(iv['p_hat'] * dur for iv, dur in valid) / total
    sigma = max(
        sum(iv['sigma'] * dur for iv, dur in valid) / total,
        sigma_floor,
    )

    half = q * sigma

    return {
        'p_hat':      round(p_hat,                  4),
        'sigma':      round(sigma,                  6),
        'low':        round(max(0.0, p_hat - half), 4),
        'high':       round(p_hat + half,           4),
        'coverage':   DEFAULT_COV,
        'n_segments': len(valid),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Main entry point — called from similarity_route_handler.py
# ═════════════════════════════════════════════════════════════════════════════

async def compute_conformal_intervals(
    result:   Dict[str, Any],
    conn:     asyncpg.Connection,
    strategy: RetrievalStrategy = 'decomposed',
    coverage: float             = DEFAULT_COV,
) -> Dict[str, Any]:
    """
    Enrich the similarity search result with conformal prediction intervals.

    Called ONLY when stage2_active == True.

    Adds to result:
      result['conformal_interval']                            — trajectory-level
      result['segment_similarity'][i]['conformal_interval']   — per segment

    Usage in similarity_route_handler.py:
        if stage2_active:
            from utils.conformal_calibration.conformal_predictor import (
                compute_conformal_intervals,
            )
            result = await compute_conformal_intervals(
                result, conn, strategy='decomposed'
            )
    """
    cfg = get_active_config(strategy)

    # Load quantiles — segment level for per-segment intervals,
    # trajectory level for the aggregated result.
    q_seg  = await get_calibration_quantile(conn, cfg, coverage, level='segment')
    q_traj = await get_calibration_quantile(conn, cfg, coverage, level='trajectory')

    if q_seg is None and q_traj is None:
        result['conformal_interval'] = None
        return result

    # Fallback: if one level is missing use the other
    q_for_seg  = q_seg  if q_seg  is not None else q_traj
    q_for_traj = q_traj if q_traj is not None else q_seg

    sigma_floor    = cfg.sigma_floor
    segment_groups = result.get('segment_similarity', [])

    seg_intervals: List[Optional[Dict]] = []
    seg_durations: List[float]          = []

    for group in segment_groups:
        seg_results = group.get('similar_segments', {}).get('results', [])
        seg_features = group.get('target_segment_features') or {}

        # duration as proxy for sequence length — used for DTW normalization
        query_duration = float(seg_features.get('duration') or 1.0)

        interval = _compute_segment_interval(
            seg_results    = seg_results,
            q              = q_for_seg,
            sigma_floor    = sigma_floor,
            query_duration = query_duration,
        )

        # Attach interval to the segment group in the response
        group['conformal_interval'] = interval

        if interval is not None:
            seg_intervals.append(interval)
            seg_durations.append(query_duration)

    # Trajectory-level interval — use trajectory q and duration-weighted aggregation
    traj_interval = _aggregate_trajectory_interval(
        seg_intervals = seg_intervals,
        seg_durations = seg_durations,
        q             = q_for_traj,
        sigma_floor   = sigma_floor,
    ) if seg_intervals else None

    result['conformal_interval'] = traj_interval

    logger.debug(
        "Conformal interval: "
        f"p̂={traj_interval['p_hat'] if traj_interval else 'N/A'}  "
        f"[{traj_interval['low'] if traj_interval else 'N/A'}, "
        f"{traj_interval['high'] if traj_interval else 'N/A'}] mm  "
        f"q_seg={q_for_seg:.4f}  q_traj={q_for_traj:.4f}  "
        f"strategy={strategy}"
    )

    return result