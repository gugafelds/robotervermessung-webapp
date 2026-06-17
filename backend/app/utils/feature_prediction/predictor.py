"""
feature_prediction/predictor.py  — identisch mit vorheriger Version,
nur zwei Änderungen:
  1. group['prediction'] wird nach compute_conformal_intervals entfernt
  2. result['conformal_interval'] (top-level) wird nicht mehr gesetzt
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


def _sequence_len(seq: Any) -> int:
    try:
        return int(len(seq))
    except TypeError:
        return 0


def _path_length(seq: Any) -> float:
    arr = np.asarray(seq, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return 0.0
    coords = arr[:, :min(3, arr.shape[1])]
    return float(np.linalg.norm(np.diff(coords, axis=0), axis=1).sum())

def _normalize_dtw(
    raw_dtw: float,
    n_points_query: int,
    n_points_cand: int,
    query_path_length: float = 0.0,
    distance_normalization: str = 'per_path_length',
) -> float:
    raw = float(raw_dtw)

    if distance_normalization == 'raw':
        return raw

    if distance_normalization == 'per_point':
        denom = max(n_points_query, n_points_cand, 1)
        return raw / float(denom)

    if distance_normalization == 'per_path_length':
        return raw / max(float(query_path_length), EPSILON)

    raise ValueError(f"Unknown distance_normalization: {distance_normalization}")


def _seg_id_to_traj_id(seg_id: str) -> str:
    return seg_id.rsplit('_', 1)[0]


def _build_n_points_lookup(seg_batch: Dict[str, Any]) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    for traj_data in seg_batch.values():
        segments = (traj_data or {}).get('segments') or {}
        for seg_id, arr in segments.items():
            n = _sequence_len(arr)
            if n > 0:
                lookup[seg_id] = n
    return lookup


def _build_path_length_lookup(seg_batch: Dict[str, Any]) -> Dict[str, float]:
    lookup: Dict[str, float] = {}
    for traj_data in seg_batch.values():
        segments = (traj_data or {}).get('segments') or {}
        for seg_id, arr in segments.items():
            pl = _path_length(arr)
            if pl > EPSILON:
                lookup[seg_id] = pl
    return lookup


def _build_traj_n_points_lookup(
    traj_batch: Dict[str, Any],
    seg_batch:  Dict[str, Any],
    target_id:  str,
) -> Dict[str, int]:
    lookup: Dict[str, int] = {}

    for traj_id, data in (traj_batch or {}).items():
        arr = (data or {}).get('trajectory')
        if arr is not None:
            n = _sequence_len(arr)
            if n > 0:
                lookup[traj_id] = n

    if target_id not in lookup:
        query_data = seg_batch.get(target_id) or {}
        arr = query_data.get('trajectory')
        if arr is not None and _sequence_len(arr) > 0:
            lookup[target_id] = _sequence_len(arr)
        else:
            segs  = query_data.get('segments') or {}
            total = sum(_sequence_len(v) for v in segs.values())
            if total > 0:
                lookup[target_id] = total

    return lookup


def _predict_segment(
    seg_results:    List[Dict[str, Any]],
    query_n_points: int,
    cand_n_points:  Dict[str, int],
    query_path_length: float = 0.0,
    distance_normalization: str = 'per_path_length',
    feature:        str   = 'mean_distance',
    sigma_floor:    float = 0.005,
) -> Optional[Dict[str, Any]]:
    valid = []
    for r in seg_results:
        raw_dtw  = r.get('dtw_distance')
        features = r.get('features') or {}
        perf_val = features.get(feature)
        sid      = r.get('seg_id')
        if raw_dtw is None or perf_val is None or sid is None:
            continue
        n_cand   = cand_n_points.get(sid, query_n_points)
        norm_dtw = _normalize_dtw(
        raw_dtw=float(raw_dtw),
        n_points_query=query_n_points,
        n_points_cand=n_cand,
        query_path_length=query_path_length,
        distance_normalization=distance_normalization,
    )
        valid.append({'seg_id': sid, 'dtw_distance': norm_dtw, 'perf_value': float(perf_val)})

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])
    dtw_dists   = [v['dtw_distance'] for v in valid]
    perf_values = [v['perf_value']   for v in valid]
    ids         = [v['seg_id']       for v in valid]

    weights  = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum    = sum(weights)
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
    }

def _predict_stage1_rrf(
    results:      List[Dict[str, Any]],
    feature:      str   = 'mean_distance',
    sigma_floor:  float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Stage-1 prediction using RRF scores as weights.

    Used only when Stage 2 is not active, because dtw_distance is not available.
    No conformal interval is computed for this prediction.
    """
    valid = []

    for r in results:
        features = r.get('features') or {}
        perf_val = features.get(feature)
        sid = r.get('seg_id') or r.get('traj_id')

        if perf_val is None or sid is None:
            continue

        rrf_score = r.get('rrf_score')
        if rrf_score is None:
            continue

        weight = float(rrf_score)
        if weight <= EPSILON:
            continue

        valid.append({
            'seg_id': str(sid),
            'weight': weight,
            'perf_value': float(perf_val),
        })

    if len(valid) < 2:
        return None

    weights = [v['weight'] for v in valid]
    perf_values = [v['perf_value'] for v in valid]
    ids = [v['seg_id'] for v in valid]

    w_sum = sum(weights)
    if w_sum <= EPSILON:
        return None

    p_hat = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    n = len(perf_values)
    mean_p = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma = max(perf_std, sigma_floor)

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_neighbors':  n,
        'neighbor_ids': ids,
    }


def _aggregate_trajectory_decomposed(
    seg_predictions: List[Optional[Dict[str, Any]]],
    path_lengths:    List[float],
    sigma_floor:     float = 0.005,
) -> Optional[Dict[str, Any]]:
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

    return {'p_hat': round(p_hat, 4), 'sigma': round(sigma, 6), 'n_segments': len(valid)}


def _predict_direct(
    traj_results:       List[Dict[str, Any]],
    query_n_points:     int,
    cand_traj_n_points: Dict[str, int],
    feature:            str   = 'mean_distance',
    sigma_floor:        float = 0.005,
) -> Optional[Dict[str, Any]]:
    valid = []
    for r in traj_results:
        raw_dtw  = r.get('dtw_distance')
        features = r.get('features') or {}
        perf_val = features.get(feature)
        traj_id  = r.get('seg_id') or r.get('traj_id')
        if raw_dtw is None or perf_val is None or traj_id is None:
            continue
        n_cand   = cand_traj_n_points.get(traj_id, query_n_points)
        norm_dtw = _normalize_dtw(float(raw_dtw), query_n_points, n_cand)
        valid.append({'traj_id': traj_id, 'dtw_distance': norm_dtw, 'perf_value': float(perf_val)})

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])
    dtw_dists   = [v['dtw_distance'] for v in valid]
    perf_values = [v['perf_value']   for v in valid]
    ids         = [v['traj_id']      for v in valid]

    weights  = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum    = sum(weights)
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
    }


async def predict_performance(
    result:     Dict[str, Any],
    seg_batch:  Dict[str, Any],
    conn:       asyncpg.Connection,
    traj_batch: Optional[Dict[str, Any]] = None,
    feature:    str   = 'mean_distance',
    coverage:   float = 0.90,
) -> Dict[str, Any]:
    sigma_floor = 0.005
    target_id   = result.get('target_id', '')

    stage2_active = bool(result.get('stage2_active'))

    n_points_map      = _build_n_points_lookup(seg_batch or {})
    path_length_map   = _build_path_length_lookup(seg_batch or {})
    traj_n_points_map = _build_traj_n_points_lookup(traj_batch or {}, seg_batch or {}, target_id)

    # ── Decomposed ────────────────────────────────────────────────────────────
    segment_groups   = result.get('segment_similarity', [])
    seg_predictions:  List[Optional[Dict]] = []
    seg_path_lengths: List[float]          = []
    seg_query_ids:    List[str]            = []

    for group in segment_groups:
        query_seg_id   = group.get('target_segment', '')
        seg_results    = group.get('similar_segments', {}).get('results', [])
        query_n_points = n_points_map.get(query_seg_id, 1)

        seg_features   = group.get('target_segment_features') or {}
        query_path_len = float(seg_features.get('length') or 0.0)
        if query_path_len <= EPSILON:
            query_path_len = path_length_map.get(query_seg_id, 0.0)
        if query_path_len > EPSILON:
            path_length_map[query_seg_id] = query_path_len

        if stage2_active:
            prediction = _predict_segment(
                seg_results    = seg_results,
                query_n_points = query_n_points,
                cand_n_points  = n_points_map,
                feature        = feature,
                sigma_floor    = sigma_floor,
            )
        else:
            prediction = _predict_stage1_rrf(
                results     = seg_results,
                feature     = feature,
                sigma_floor = sigma_floor,
            )

        if prediction is not None:
            prediction['query_n_points'] = query_n_points if stage2_active else None
            prediction['query_path_length'] = query_path_len

        # Temporär auf group — wird von conformal_predictor gelesen, dann entfernt
        group['prediction'] = prediction
        seg_predictions.append(prediction)
        seg_path_lengths.append(query_path_len)
        seg_query_ids.append(query_seg_id)

    decomposed_prediction = _aggregate_trajectory_decomposed(
        seg_predictions = seg_predictions,
        path_lengths    = seg_path_lengths,
        sigma_floor     = sigma_floor,
    )

    # ── Direct ────────────────────────────────────────────────────────────────
    direct_prediction: Optional[Dict[str, Any]] = None
    traj_results = result.get('traj_similarity', {}).get('results', [])

    if stage2_active:
        if traj_batch is not None:
            query_n_points_t = traj_n_points_map.get(target_id, 1)
            direct_prediction = _predict_direct(
                traj_results       = traj_results,
                query_n_points     = query_n_points_t,
                cand_traj_n_points = traj_n_points_map,
                feature            = feature,
                sigma_floor        = sigma_floor,
            )
    else:
        direct_prediction = _predict_stage1_rrf(
            results     = traj_results,
            feature     = feature,
            sigma_floor = sigma_floor,
        )

    # ── Prognosis dict ────────────────────────────────────────────────────────
    result['prognosis'] = {
        'feature':                       feature,
        'stage': 'stage2_dtw' if stage2_active else 'stage1_rrf',
        'decomposed':                    decomposed_prediction,
        'direct':                        direct_prediction,
        'decomposed_conformal_interval': None,  # wird von compute_conformal_intervals gesetzt
        'direct_conformal_interval':     None,  # wird von _compute_direct_conformal_interval gesetzt
        'segments': [
            {'seg_id': sid, **pred} if pred else {'seg_id': sid, 'p_hat': None}
            for sid, pred in zip(seg_query_ids, seg_predictions)
        ],
    }

    # ── Conformal intervals ───────────────────────────────────────────────────
    if stage2_active:
        result = await compute_conformal_intervals(
            result          = result,
            conn            = conn,
            strategy        = 'decomposed',
            coverage        = coverage,
            n_points_map    = n_points_map,
            path_length_map = path_length_map,
        )

        if direct_prediction is not None:
            direct_interval = await _compute_direct_conformal_interval(
                prediction = direct_prediction,
                conn       = conn,
                coverage   = coverage,
            )
            result['prognosis']['direct_conformal_interval'] = direct_interval

    # ── Aufräumen: group['prediction'] entfernen ──────────────────────────────
    for group in segment_groups:
        group.pop('prediction', None)

    return result


async def _compute_direct_conformal_interval(
    prediction: Dict[str, Any],
    conn:       asyncpg.Connection,
    coverage:   float = 0.90,
) -> Optional[Dict[str, Any]]:
    from .conformal_predictor import get_calibration_quantile
    from .conformal_config    import get_active_config

    cfg = get_active_config('direct')
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