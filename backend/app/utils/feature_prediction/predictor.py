"""
feature_prediction/predictor.py
================================
Performance prediction using retrieved neighbors.

Stage 2 (DTW): inverse distance weighting with RAW DTW distances,
               as published in the paper (eq. inverse_distance).
               w_i = 1 / (d_i + ε)

Stage 1 (RRF): rank-decay weighting (eq. isr).
               w_i ∝ 1 / r_i²
               d_min_per_path_length = 1 / best_rrf_score  (match-quality proxy)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import numpy as np

from .conformal_predictor import compute_conformal_intervals, compute_stage1_conformal_interval

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
    """Stage 2 segment prediction using inverse DTW distance weighting."""
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

    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    pl = max(query_path_length, EPSILON)
    d_min        = round(dtw_dists[0],  6)
    d_max        = round(dtw_dists[-1], 6)
    d_normalized = round(sum(dtw_dists) / len(dtw_dists) / pl, 6) if query_path_length > EPSILON else None

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_neighbors':  n,
        'd_min':        d_min,
        'd_max':        d_max,
        'd_normalized': d_normalized,
    }


def _predict_stage1_rrf(
    results:     List[Dict[str, Any]],
    feature:     str   = 'mean_distance',
    sigma_floor: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Stage 1 prediction using RRF score weighting (w_i ∝ rrf_score).

    d_min_per_path_length = 1 / best_rrf_score — used as match-quality proxy:
    high RRF score → small "distance" → good match.
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

    w_sum = sum(weights)
    if w_sum <= EPSILON:
        return None

    p_hat    = sum(w * p for w, p in zip(weights, perf_values)) / w_sum
    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    best_rrf  = max(weights)
    mean_rrf  = sum(weights) / len(weights)
    worst_rrf = min(weights)
    # RRF proxies: 1/score² — squaring rewards better-ranked neighbours more (per paper)
    d_min        = round(1.0 / best_rrf  ** 2, 6) if best_rrf  > EPSILON else None
    d_max        = round(1.0 / worst_rrf ** 2, 6) if worst_rrf > EPSILON else None
    d_normalized = round(1.0 / mean_rrf  ** 2, 6) if mean_rrf  > EPSILON else None

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_neighbors':  n,
        'd_min':        d_min,
        'd_max':        d_max,
        'd_normalized': d_normalized,
    }


def _predict_direct(
    traj_results:      List[Dict[str, Any]],
    query_path_length: float = 0.0,
    feature:           str   = 'mean_distance',
    sigma_floor:       float = 0.005,
) -> Optional[Dict[str, Any]]:
    """Stage 2 trajectory-level prediction using inverse DTW distance weighting."""
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

    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    sigma    = max(perf_std, sigma_floor)

    pl = max(query_path_length, EPSILON)
    d_min        = round(dtw_dists[0],  6)
    d_max        = round(dtw_dists[-1], 6)
    d_normalized = round(sum(dtw_dists) / len(dtw_dists) / pl, 6) if query_path_length > EPSILON else None

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_neighbors':  n,
        'd_min':        d_min,
        'd_max':        d_max,
        'd_normalized': d_normalized,
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

    def _wagg(key: str) -> Optional[float]:
        vals = [pred[key] for pred, _ in valid if pred.get(key) is not None]
        return round(sum(vals) / len(vals), 6) if vals else None

    return {
        'p_hat':        round(p_hat, 4),
        'sigma':        round(sigma, 6),
        'n_segments':   len(valid),
        'd_min':        _wagg('d_min'),
        'd_max':        _wagg('d_max'),
        'd_normalized': _wagg('d_normalized'),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main async entry point
# ═══════════════════════════════════════════════════════════════════════════

async def predict_performance(
    result:           Dict[str, Any],
    seg_batch:        Dict[str, Any],
    conn:             asyncpg.Connection,
    feature:          str                       = 'mean_distance',
    coverage:         float                     = 0.90,
    calibration_tag:  str                       = 'all',
    conformal_active: bool                      = True,
    k:                int                       = 10,
    search_modes:     Optional[Tuple[str, ...]] = None,
    dtw_mode:         str                       = 'position',
    metric:           str                       = 'sidtw',
) -> Dict[str, Any]:
    sigma_floor     = 0.005
    stage2_active   = bool(result.get('stage2_active'))
    path_length_map = _build_path_length_lookup(seg_batch or {})

    segment_groups:   list                 = result.get('segment_similarity', [])
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
                seg_results=seg_results, query_path_length=query_path_len,
                feature=feature, sigma_floor=sigma_floor,
            )
        else:
            prediction = _predict_stage1_rrf(
                results=seg_results, feature=feature, sigma_floor=sigma_floor,
            )

        if prediction is not None:
            prediction['query_path_length'] = query_path_len if query_path_len > EPSILON else None

        group['prediction'] = prediction
        seg_predictions.append(prediction)
        seg_path_lengths.append(query_path_len)
        seg_query_ids.append(query_seg_id)

    decomposed_prediction = _aggregate_trajectory_decomposed(
        seg_predictions=seg_predictions,
        path_lengths=seg_path_lengths,
        sigma_floor=sigma_floor,
    )

    traj_results            = result.get('traj_similarity', {}).get('results', [])
    total_query_path_length = sum(seg_path_lengths)

    if stage2_active:
        direct_prediction = _predict_direct(
            traj_results=traj_results, query_path_length=total_query_path_length,
            feature=feature, sigma_floor=sigma_floor,
        )
    else:
        direct_prediction = _predict_stage1_rrf(
            results=traj_results, feature=feature, sigma_floor=sigma_floor,
        )

    # Build segments list — only expose what the frontend needs
    segments = []
    for sid, pred in zip(seg_query_ids, seg_predictions):
        if pred:
            segments.append({
                'seg_id':                sid,
                'p_hat':                 pred.get('p_hat'),
                'sigma':                 pred.get('sigma'),
                'n_neighbors':           pred.get('n_neighbors'),
                'd_min':             pred.get('d_min'),
                'd_max':             pred.get('d_max'),
                'd_normalized':      pred.get('d_normalized'),
                'query_path_length': pred.get('query_path_length'),
            })
        else:
            segments.append({'seg_id': sid, 'p_hat': None})

    result['prognosis'] = {
        'feature':                       feature,
        'stage':                         'stage2_dtw' if stage2_active else 'stage1_rrf',
        'decomposed':                    decomposed_prediction,
        'direct':                        direct_prediction,
        'decomposed_conformal_interval': None,
        'direct_conformal_interval':     None,
        'stage1_conformal_interval':     None,
        'segments':                      segments,
    }

    if conformal_active:
        if stage2_active:
            result = await compute_conformal_intervals(
                result=result, conn=conn, strategy='decomposed',
                coverage=coverage, calibration_tag=calibration_tag,
                path_length_map=path_length_map,
                k=k, search_modes=search_modes, dtw_mode=dtw_mode, metric=metric,
            )
        else:
            # Stage 1: writes stage1_conformal_interval and decomposed_conformal_interval
            # directly into result['prognosis']
            await compute_stage1_conformal_interval(
                result=result, conn=conn,
                coverage=coverage, calibration_tag=calibration_tag,
                k=k, search_modes=search_modes, metric=metric,
            )

        for group in segment_groups:
            group.pop('prediction', None)

    return result