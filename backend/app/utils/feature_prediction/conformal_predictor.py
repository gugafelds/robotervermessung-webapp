"""
feature_prediction/conformal_predictor.py
==========================================
Conformal prediction intervals.

DB lookup key
--------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag + coverage

Fallback: if calibration_tag != 'all' and no row found, retries with 'all'.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import asyncpg

from .conformal_config import CalibrationConfig, RetrievalStrategy, get_active_config

logger = logging.getLogger(__name__)

EPSILON     = 1e-6
DEFAULT_COV = 0.90

_quantile_cache: Dict[str, float] = {}


def _cache_key(
    metric: str, dtw_mode: str, strategy: str,
    level: str, k: int, search_modes_str: str,
    tag: str, coverage: float,
) -> str:
    return f"{metric}:{dtw_mode}:{strategy}:{level}:{k}:{search_modes_str}:{tag}:{coverage}"


async def _fetch_quantile_row(
    conn:             asyncpg.Connection,
    metric:           str,
    dtw_mode:         str,
    strategy:         str,
    level:            str,
    k:                int,
    search_modes_str: str,
    tag:              str,
    coverage:         float,
) -> Optional[float]:
    row = await conn.fetchrow("""
        SELECT quantile_value
        FROM evaluation.confidence_quantiles
        WHERE metric             = $1
          AND dtw_mode           = $2
          AND retrieval_strategy = $3
          AND level              = $4
          AND config_k           = $5
          AND search_modes       = $6
          AND calibration_tag    = $7
          AND coverage           = $8
        ORDER BY computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, k, search_modes_str, tag, float(coverage))

    return float(row['quantile_value']) if row is not None else None


async def get_calibration_quantile(
    conn:     asyncpg.Connection,
    cfg:      CalibrationConfig,
    coverage: float = DEFAULT_COV,
    level:    str   = 'trajectory',
) -> Optional[float]:
    """
    Lookup conformal quantile by explicit key columns (not config_hash).
    Falls back to calibration_tag='all' if specific tag yields no result.
    """
    metric           = cfg.metric
    dtw_mode         = cfg.dtw_mode
    strategy         = cfg.retrieval_strategy
    k                = cfg.k
    search_modes_str = cfg.search_modes_str()
    tag              = cfg.calibration_tag

    ck = _cache_key(metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage)
    if ck in _quantile_cache:
        return _quantile_cache[ck]

    q = await _fetch_quantile_row(
        conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage,
    )

    # Fallback to 'all' tag if specific tag not found
    if q is None and tag != 'all':
        logger.info(
            f"No quantile for tag='{tag}' — falling back to tag='all' "
            f"({metric}/{dtw_mode}/{strategy}/{level}/k={k})"
        )
        q = await _fetch_quantile_row(
            conn, metric, dtw_mode, strategy, level, k, search_modes_str, 'all', coverage,
        )

    if q is None:
        logger.warning(
            f"No conformal quantile found — "
            f"metric={metric} dtw_mode={dtw_mode} strategy={strategy} "
            f"level={level} k={k} modes={search_modes_str} "
            f"tag={tag} coverage={coverage}. "
            f"Run calibration_set_builder.py first."
        )
        return None

    _quantile_cache[ck] = q
    return q


def _compute_segment_interval(
    group:       Dict[str, Any],
    q:           float,
    sigma_floor: float,
    coverage:    float,
) -> Optional[Dict[str, Any]]:
    prediction = group.get('prediction')
    if prediction is None or prediction.get('p_hat') is None:
        return None

    p_hat = float(prediction['p_hat'])
    sigma = float(prediction['sigma'])
    half  = q * sigma

    return {
        'p_hat':    round(p_hat,                  4),
        'sigma':    round(sigma,                  6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half,           4),
        'coverage': coverage,
    }


def _aggregate_trajectory_interval(
    seg_intervals:    List[Optional[Dict]],
    seg_path_lengths: List[float],
    q:                float,
    sigma_floor:      float,
    coverage:         float,
) -> Optional[Dict[str, Any]]:
    valid = [
        (iv, pl)
        for iv, pl in zip(seg_intervals, seg_path_lengths)
        if iv is not None and pl > EPSILON
    ]
    if not valid:
        return None

    total = sum(pl for _, pl in valid)
    if total <= EPSILON:
        return None

    p_hat = sum(iv['p_hat'] * pl for iv, pl in valid) / total
    sigma = max(sum(iv['sigma'] * pl for iv, pl in valid) / total, sigma_floor)
    half  = q * sigma

    return {
        'p_hat':      round(p_hat,                  4),
        'sigma':      round(sigma,                  6),
        'low':        round(max(0.0, p_hat - half), 4),
        'high':       round(p_hat + half,           4),
        'coverage':   coverage,
        'n_segments': len(valid),
    }


async def compute_conformal_intervals(
    result:          Dict[str, Any],
    conn:            asyncpg.Connection,
    strategy:        RetrievalStrategy          = 'decomposed',
    coverage:        float                      = DEFAULT_COV,
    calibration_tag: str                        = 'all',
    n_points_map:    Optional[Dict[str, int]]   = None,   # kept for API compat, unused
    path_length_map: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute and attach conformal intervals to result.

    Writes:
      result['prognosis']['decomposed_conformal_interval']  — trajectory level
      group['conformal_interval']                           — segment level
    """
    if path_length_map is None:
        path_length_map = {}

    cfg    = get_active_config(strategy, calibration_tag)
    q_seg  = await get_calibration_quantile(conn, cfg, coverage, 'segment')
    q_traj = await get_calibration_quantile(conn, cfg, coverage, 'trajectory')

    if q_seg is None and q_traj is None:
        if 'prognosis' in result:
            result['prognosis']['decomposed_conformal_interval'] = None
        return result

    q_for_seg   = q_seg  if q_seg  is not None else q_traj
    q_for_traj  = q_traj if q_traj is not None else q_seg
    sigma_floor = cfg.sigma_floor

    segment_groups    = result.get('segment_similarity', [])
    seg_intervals:    List[Optional[Dict]] = []
    seg_path_lengths: List[float]          = []

    for group in segment_groups:
        interval = _compute_segment_interval(
            group=group, q=q_for_seg, sigma_floor=sigma_floor, coverage=coverage,
        )
        group['conformal_interval'] = interval

        query_seg_id = group.get('target_segment', '')
        prediction   = group.get('prediction') or {}
        pl = float(
            prediction.get('query_path_length')
            or path_length_map.get(query_seg_id, 0.0)
            or 0.0
        )
        seg_intervals.append(interval)
        seg_path_lengths.append(pl)

    traj_interval = _aggregate_trajectory_interval(
        seg_intervals=seg_intervals,
        seg_path_lengths=seg_path_lengths,
        q=q_for_traj,
        sigma_floor=sigma_floor,
        coverage=coverage,
    ) if seg_intervals else None

    if 'prognosis' in result:
        result['prognosis']['decomposed_conformal_interval'] = traj_interval

    return result