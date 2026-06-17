"""
feature_prediction/predictor.py
================================
Performance prediction using retrieved neighbors.

Stage 2 (DTW): inverse distance weighting with RAW DTW distances,
               as published in the paper (eq. inverse_distance).
               w_i = 1 / (d_i + ε)

Stage 1 (RRF): rank-decay weighting (eq. isr).
               w_i ∝ 1 / r_i²

Changes vs. previous version
------------------------------
- traj_batch and target_id parameters removed from predict_performance().
  Both were only used by _build_traj_n_points_lookup(), which existed solely
  to support the now-removed DTW normalization. Raw DTW needs no n_points.
- calibration_tag parameter added — passed through to compute_conformal_intervals()
  so the correct quantile set is used for the current search context.
- _build_traj_n_points_lookup() and _build_n_points_lookup() removed.
- _normalize_dtw() removed (raw DTW, paper-conform).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import asyncpg
import numpy as np

from .conformal_predictor import compute_conformal_intervals

logger = logging.getLogger(__name__)

EPSILON = 1e-6


# ═══════════════════════════════════════════════════════════════════════════
# Geometry helpers
# ═══════════════════════════════════════════════════════════════════════════

def _path_length(seq: Any) -> float:
    arr = np.asarray(seq, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return 0.0
    coords = arr[:, :min(3, arr.shape[1])]
    return float(np.linalg.norm(np.diff(coords, axis=0), axis=1).sum())


def _seg_id_to_traj_id(seg_id: str) -> str:
    return seg_id.rsplit('_', 1)[0]


def _build_path_length_lookup(seg_batch: Dict[str, Any]) -> Dict[str, float]:
    lookup: Dict[str, float] = {}
    for traj_data in seg_batch.values():
        segments = (traj_data or {}).get('segments') or {}
        for seg_id, arr in segments.items():
            pl = _path_length(arr)
            if pl > EPSILON:
                lookup[seg_id] = pl
    return lookup


# ═══════════════════════════════════════════════════════════════════════════
# Core prediction functions
# ═══════════════════════════════════════════════════════════════════════════

def _predict_segment(
    seg_results:       List[Dict[str, Any]],
    query_path_length: float = 0.0,
    feature:           str   = 'mean_distance',
    sigma_floor:       float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Segment-level prediction using raw DTW distances (paper eq. inverse_distance).
    w_i = 1 / (d_i + ε)

    Also computes d_min_per_path_length as a future LACP sigma-model feature.
    """
    valid = []
    for r in seg_results:
        raw_dtw  = r.get('dtw_distance')
        features = r.get('features') or {}
        perf_val = features.get(feature)
        sid      = r.get('seg_id')
        if raw_dtw is None or perf_val is None or sid is None:
            continue
        valid.append({
            'seg_id':       sid,
            'dtw_distance': float(raw_dtw),
            'perf_value':   float(perf_val),
        })

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])
    dtw_dists   = [v['dtw_distance'] for v in valid]
    perf_values = [v['perf_value']   for v in valid]
    ids         = [v['seg_id']       for v in valid]

    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    d_min_raw             = dtw_dists[0]
    d_min_per_path_length = (
        d_min_raw / max(query_path_length, EPSILON)
        if query_path_length > EPSILON else None
    )

    return {
        'p_hat':                  round(p_hat, 4),
        'sigma':                  round(sigma, 6),
        'n_neighbors':            n,
        'neighbor_ids':           ids,
        'd_min':                  round(d_min_raw, 6),
        'd_min_per_path_length':  round(d_min_per_path_length, 6) if d_min_per_path_length is not None else None,
        'd_mean':                 round(sum(dtw_dists) / len(dtw_dists), 6),
    }


def _predict_direct(
    traj_results: List[Dict[str, Any]],
    feature:      str   = 'mean_distance',
    sigma_floor:  float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Trajectory-level prediction using raw DTW distances (paper eq. inverse_distance).
    w_i = 1 / (d_i + ε)
    """
    valid = []
    for r in traj_results:
        raw_dtw  = r.get('dtw_distance')
        features = r.get('features') or {}
        perf_val = features.get(feature)
        traj_id  = r.get('seg_id') or r.get('traj_id')
        if raw_dtw is None or perf_val is None or traj_id is None:
            continue
        valid.append({
            'traj_id':      traj_id,
            'dtw_distance': float(raw_dtw),
            'perf_value':   float(perf_val),
        })

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])
    dtw_dists   = [v['dtw_distance'] for v in valid]
    perf_values = [v['perf_value']   for v in valid]
    ids         = [v['traj_id']      for v in valid]

    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    return {
        'p_hat':       round(p_hat, 4),
        'sigma':       round(sigma, 6),
        'n_neighbors': n,
        'neighbor_ids': ids,
        'd_min':       round(dtw_dists[0], 6),
        'd_mean':      round(sum(dtw_dists) / len(dtw_dists), 6),
    }


def _predict_stage1_rrf(
    results:     List[Dict[str, Any]],
    feature:     str   = 'mean_distance',
    sigma_floor: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Stage-1 prediction using RRF scores as weights (rank-decay, paper eq. isr).
    No conformal interval is computed for Stage-1 predictions.
    No d_min available (no physical distances from Stage 1).
    """
    valid = []
    for r in results:
        features  = r.get('features') or {}
        perf_val  = features.get(feature)
        sid       = r.get('seg_id') or r.get('traj_id')
        rrf_score = r.get('rrf_score')
        if perf_val is None or sid is None or rrf_score is None:
            continue
        weight = float(rrf_score)
        if weight <= EPSILON:
            continue
        valid.append({'seg_id': str(sid), 'weight': weight, 'perf_value': float(perf_val)})

    if len(valid) < 2:
        return None

    weights     = [v['weight']     for v in valid]
    perf_values = [v['perf_value'] for v in valid]
    ids         = [v['seg_id']     for v in valid]

    w_sum = sum(weights)
    if w_sum <= EPSILON:
        return None

    p_hat    = sum(w * p for w, p in zip(weights, perf_values)) / w_sum
    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_neighbors':  n,
        'neighbor_ids': ids,
        'd_min':        None,
        'd_mean':       None,
    }


def _aggregate_trajectory_decomposed(
    seg_predictions: List[Optional[Dict[str, Any]]],
    path_lengths:    List[float],
    sigma_floor:     float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Length-weighted aggregation of segment predictions to trajectory level.
    Also aggregates d_min_per_path_length for LACP use.
    """
    valid = [
        (pred, pl)
        for pred, pl in zip(seg_predictions, path_lengths)
        if pred is not None and pl > EPSILON
    ]
    if not valid:
        return None

    total = sum(pl for _, pl in valid)
    if total <= EPSILON:
        return None

    p_hat = sum(pred['p_hat'] * pl for pred, pl in valid) / total
    sigma = max(sum(pred['sigma'] * pl for pred, pl in valid) / total, sigma_floor)

    d_min_vals = [
        pred['d_min_per_path_length']
        for pred, _ in valid
        if pred.get('d_min_per_path_length') is not None
    ]
    d_min_agg = round(sum(d_min_vals) / len(d_min_vals), 6) if d_min_vals else None

    return {
        'p_hat':                 round(p_hat, 4),
        'sigma':                 round(sigma, 6),
        'n_segments':            len(valid),
        'd_min_per_path_length': d_min_agg,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main async entry point
# ═══════════════════════════════════════════════════════════════════════════

async def predict_performance(
    result:          Dict[str, Any],
    seg_batch:       Dict[str, Any],
    conn:            asyncpg.Connection,
    feature:         str   = 'mean_distance',
    coverage:        float = 0.90,
    calibration_tag: str   = 'all',
) -> Dict[str, Any]:
    """
    Compute performance predictions and attach conformal intervals.

    Parameters
    ----------
    result          : pipeline result dict (modified in-place)
    seg_batch       : loaded trajectory/segment data for path-length resolution
    conn            : DB connection for quantile lookup
    feature         : performance feature to predict (default: 'mean_distance')
    coverage        : target conformal coverage (default: 0.90)
    calibration_tag : which calibration set to use for quantile lookup;
                      falls back to 'all' if tag not found in DB
    """
    sigma_floor   = 0.005
    stage2_active = bool(result.get('stage2_active'))
    path_length_map = _build_path_length_lookup(seg_batch or {})

    # ── Decomposed (segment-level) ────────────────────────────────────────
    segment_groups:   list              = result.get('segment_similarity', [])
    seg_predictions:  List[Optional[Dict]] = []
    seg_path_lengths: List[float]          = []
    seg_query_ids:    List[str]            = []

    for group in segment_groups:
        query_seg_id = group.get('target_segment', '')
        seg_results  = group.get('similar_segments', {}).get('results', [])

        seg_features   = group.get('target_segment_features') or {}
        query_path_len = float(seg_features.get('length') or 0.0)
        if query_path_len <= EPSILON:
            query_path_len = path_length_map.get(query_seg_id, 0.0)
        if query_path_len > EPSILON:
            path_length_map[query_seg_id] = query_path_len

        if stage2_active:
            prediction = _predict_segment(
                seg_results       = seg_results,
                query_path_length = query_path_len,
                feature           = feature,
                sigma_floor       = sigma_floor,
            )
        else:
            prediction = _predict_stage1_rrf(
                results     = seg_results,
                feature     = feature,
                sigma_floor = sigma_floor,
            )

        if prediction is not None:
            prediction['query_path_length'] = query_path_len if stage2_active else None

        group['prediction'] = prediction
        seg_predictions.append(prediction)
        seg_path_lengths.append(query_path_len)
        seg_query_ids.append(query_seg_id)

    decomposed_prediction = _aggregate_trajectory_decomposed(
        seg_predictions = seg_predictions,
        path_lengths    = seg_path_lengths,
        sigma_floor     = sigma_floor,
    )

    # ── Direct (trajectory-level) ─────────────────────────────────────────
    direct_prediction: Optional[Dict[str, Any]] = None
    traj_results = result.get('traj_similarity', {}).get('results', [])

    if stage2_active:
        direct_prediction = _predict_direct(
            traj_results = traj_results,
            feature      = feature,
            sigma_floor  = sigma_floor,
        )
    else:
        direct_prediction = _predict_stage1_rrf(
            results     = traj_results,
            feature     = feature,
            sigma_floor = sigma_floor,
        )

    # ── Prognosis dict ────────────────────────────────────────────────────
    result['prognosis'] = {
        'feature':                       feature,
        'stage':                         'stage2_dtw' if stage2_active else 'stage1_rrf',
        'decomposed':                    decomposed_prediction,
        'direct':                        direct_prediction,
        'decomposed_conformal_interval': None,
        'direct_conformal_interval':     None,
        'segments': [
            {'seg_id': sid, **pred} if pred else {'seg_id': sid, 'p_hat': None}
            for sid, pred in zip(seg_query_ids, seg_predictions)
        ],
    }

    # ── Conformal intervals (Stage 2 only) ────────────────────────────────
    if stage2_active:
        result = await compute_conformal_intervals(
            result          = result,
            conn            = conn,
            strategy        = 'decomposed',
            coverage        = coverage,
            calibration_tag = calibration_tag,
            path_length_map = path_length_map,
        )

        if direct_prediction is not None:
            direct_interval = await _compute_direct_conformal_interval(
                prediction      = direct_prediction,
                conn            = conn,
                coverage        = coverage,
                calibration_tag = calibration_tag,
            )
            result['prognosis']['direct_conformal_interval'] = direct_interval

    # ── Cleanup ───────────────────────────────────────────────────────────
    for group in segment_groups:
        group.pop('prediction', None)

    return result


async def _compute_direct_conformal_interval(
    prediction:      Dict[str, Any],
    conn:            asyncpg.Connection,
    coverage:        float = 0.90,
    calibration_tag: str   = 'all',
) -> Optional[Dict[str, Any]]:
    from .conformal_predictor import get_calibration_quantile
    from .conformal_config    import get_active_config

    cfg = get_active_config('direct', calibration_tag)
    q   = await get_calibration_quantile(conn, cfg, coverage, level='trajectory')
    if q is None:
        return None

    p_hat = prediction['p_hat']
    sigma = prediction['sigma']
    half  = q * sigma

    return {
        'p_hat':    p_hat,
        'sigma':    round(sigma, 6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half, 4),
        'coverage': coverage,
        'strategy': 'direct',
    }