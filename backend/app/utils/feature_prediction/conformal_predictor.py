"""
feature_prediction/conformal_predictor.py  (oder conformal/predictor.py)
=========================================================================
Conformal prediction intervals — called from feature_prediction/predictor.py.
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


async def get_calibration_quantile(
    conn:     asyncpg.Connection,
    cfg:      CalibrationConfig,
    coverage: float = DEFAULT_COV,
    level:    str   = 'trajectory',
) -> Optional[float]:
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


def _compute_segment_interval(
    group:          Dict[str, Any],
    q:              float,
    sigma_floor:    float,
    n_points_map:   Dict[str, int],
    coverage:       float,
) -> Optional[Dict[str, Any]]:
    prediction = group.get('prediction')

    if prediction is not None and prediction.get('p_hat') is not None:
        p_hat = float(prediction['p_hat'])
        sigma = float(prediction['sigma'])
    else:
        query_seg_id   = group.get('target_segment', '')
        query_n_points = n_points_map.get(query_seg_id, 1)
        seg_results    = group.get('similar_segments', {}).get('results', [])

        valid = []
        for r in seg_results:
            raw_dtw  = r.get('dtw_distance')
            features = r.get('features') or {}
            mean_d   = features.get('mean_distance')
            sid      = r.get('seg_id')
            if raw_dtw is None or mean_d is None:
                continue
            n_cand   = n_points_map.get(sid, query_n_points)
            denom    = max(query_n_points, n_cand, 1)
            norm_dtw = float(raw_dtw) / float(denom)
            valid.append({'dtw_distance': norm_dtw, 'mean_distance': float(mean_d)})

        if len(valid) < 2:
            return None

        valid.sort(key=lambda x: x['dtw_distance'])
        dists    = [v['dtw_distance']  for v in valid]
        perfs    = [v['mean_distance'] for v in valid]
        w        = [1.0 / (d + EPSILON) for d in dists]
        w_sum    = sum(w)
        p_hat    = sum(wi * pi for wi, pi in zip(w, perfs)) / w_sum
        n        = len(perfs)
        mean_p   = sum(perfs) / n
        perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perfs) / n)
        sigma    = max(perf_std, sigma_floor)

    half = q * sigma
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
    sigma = max(
        sum(iv['sigma'] * pl for iv, pl in valid) / total,
        sigma_floor,
    )
    half = q * sigma

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
    strategy:        RetrievalStrategy = 'decomposed',
    coverage:        float             = DEFAULT_COV,
    n_points_map:    Optional[Dict[str, int]]   = None,
    path_length_map: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute and attach conformal intervals.

    Writes:
      result['prognosis']['decomposed_conformal_interval']  ← NEU (statt result['conformal_interval'])
      group['conformal_interval']                           ← bleibt auf Segment-Ebene
    """
    if n_points_map is None:
        n_points_map = {}
    if path_length_map is None:
        path_length_map = {}

    cfg    = get_active_config(strategy)
    q_seg  = await get_calibration_quantile(conn, cfg, coverage, 'segment')
    q_traj = await get_calibration_quantile(conn, cfg, coverage, 'trajectory')

    if q_seg is None and q_traj is None:
        # Kein Calibration Set vorhanden — Intervall weglassen
        if 'prognosis' in result:
            result['prognosis']['decomposed_conformal_interval'] = None
        return result

    q_for_seg  = q_seg  if q_seg  is not None else q_traj
    q_for_traj = q_traj if q_traj is not None else q_seg
    sigma_floor = cfg.sigma_floor

    segment_groups   = result.get('segment_similarity', [])
    seg_intervals:   List[Optional[Dict]] = []
    seg_path_lengths: List[float]         = []

    for group in segment_groups:
        interval = _compute_segment_interval(
            group        = group,
            q            = q_for_seg,
            sigma_floor  = sigma_floor,
            n_points_map = n_points_map,
            coverage     = coverage,
        )
        # Segment-Level Intervall bleibt auf group
        group['conformal_interval'] = interval

        query_seg_id = group.get('target_segment', '')
        prediction   = group.get('prediction') or {}

        pl = float(
            prediction.get('query_path_length')
            or path_length_map.get(query_seg_id, 0.0)
            or 0.0
        )
        if pl <= EPSILON:
            pl = float(
                prediction.get('query_n_points')
                or n_points_map.get(query_seg_id, 1)
            )

        seg_intervals.append(interval)
        seg_path_lengths.append(pl)

    # Trajektorie-Level Intervall → nach prognosis
    traj_interval = _aggregate_trajectory_interval(
        seg_intervals    = seg_intervals,
        seg_path_lengths = seg_path_lengths,
        q                = q_for_traj,
        sigma_floor      = sigma_floor,
        coverage         = coverage,
    ) if seg_intervals else None

    # NEU: nach prognosis schreiben, nicht nach result top-level
    if 'prognosis' in result:
        result['prognosis']['decomposed_conformal_interval'] = traj_interval

    return result