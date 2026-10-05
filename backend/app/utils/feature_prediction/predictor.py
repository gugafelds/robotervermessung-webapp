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

p_hat per segment is the WEIGHTED MEDIAN of the neighbours' values (same
weights), and the trajectory ('decomposed') p_hat averages the segments by
DURATION, not path length. The measured trajectory value
(sidtw_average_distance) is time-weighted over its segments; path-length
weighting over-weighted fast, high-error segments, and the weighted mean was
pulled up by the right-skewed errors -- together a systematic overestimate of
~+0.03 (robotervermessung-recorder scripts/active-learning/SESSION_NOTES.md,
"Ursache der Überschätzung"). Median + duration lowered the MAE by 8-26 %
depending on the reference-set size.

Which neighbours predict (switch rule, 04.10.2026): per segment the metadata-mode neighbours (z-scored 10-D vector,
`meta_groups`), unless Stage 2 found a near-identical path -- best DTW distance per path length below the
threshold 'dtw_switch_d_per_length' in prognosis.confidence_info (fitted per calibration tag by
calibration_set_builder.py; no row -> metadata only) -- then the DTW neighbours. Calibration 'all' (10k trajectories,
measured queries), test split, trajectory MAE: switch 36.4 um vs metadata only 47.6, DTW 54.6, Stage 1 five modes 55.7.
Simulated candidates (AutoMode) practically never fall below the threshold (their DTW distances are 10-20x larger;
DTW alone 125 um), so they get the metadata prognosis (42.3 um).
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import numpy as np

from .conformal_predictor import compute_conformal_intervals, compute_stage1_conformal_interval

logger = logging.getLogger(__name__)

EPSILON = 1e-6
SWITCH_KEY = 'dtw_switch_d_per_length'
_switch_cache: Dict[str, Tuple[Optional[float], float]] = {}
SWITCH_CACHE_TTL = 300  # s, like quality_match.py -- a calibration run takes effect within 5 minutes


async def dtw_switch_threshold(conn: Optional[asyncpg.Connection], calibration_tag: str) -> Optional[float]:
    """Switch threshold for this calibration tag, falling back to 'all'; None (no row/table): metadata only."""
    hit = _switch_cache.get(calibration_tag)
    if hit and time.time() - hit[1] < SWITCH_CACHE_TTL:
        return hit[0]
    value = None
    if conn is not None:
        try:
            value = await conn.fetchval(
                "SELECT value FROM prognosis.confidence_info WHERE key = $1 AND calibration_tag = ANY($2::text[]) "
                "ORDER BY calibration_tag = $3 DESC LIMIT 1", SWITCH_KEY, [calibration_tag, 'all'], calibration_tag)
        except asyncpg.UndefinedTableError:
            pass
    _switch_cache[calibration_tag] = (value, time.time())
    return value


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

def _weighted_median(values: List[float], weights: List[float]) -> float:
    order = sorted(range(len(values)), key=lambda i: values[i])
    half, acc = 0.5 * sum(weights), 0.0
    for i in order:
        acc += weights[i]
        if acc >= half:
            return values[i]
    return values[order[-1]]


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
    p_hat   = _weighted_median(perf_values, weights)

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / (n - 1))
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
    """Stage 1 prediction: w_i = rrf_score (paper eq. 3). d_min = max rrf_score (best match)."""
    valid = []
    for r in results:
        features  = r.get('features') or {}
        perf_val  = features.get(feature)
        sid       = r.get('seg_id') or r.get('traj_id')
        rrf_score = r.get('rrf_score')
        if perf_val is None or sid is None or rrf_score is None:
            continue
        if float(rrf_score) <= EPSILON:
            continue
        valid.append({'seg_id': str(sid), 'rrf_score': float(rrf_score), 'perf_value': float(perf_val)})

    if len(valid) < 2:
        return None

    # w_i = rrf_score directly (paper eq. 3)
    weights     = [v['rrf_score'] for v in valid]
    perf_values = [v['perf_value'] for v in valid]

    p_hat    = _weighted_median(perf_values, weights)
    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / (n - 1))
    sigma    = max(perf_std, sigma_floor)

    rrf_scores   = [v['rrf_score'] for v in valid]
    d_min        = round(max(rrf_scores), 6)   # best match = highest rrf_score
    d_max        = round(min(rrf_scores), 6)   # worst match = lowest rrf_score
    d_normalized = round(sum(rrf_scores) / n,  6)   # mean rrf_score

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
    p_hat   = _weighted_median(perf_values, weights)

    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / (n - 1))
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
    weights:         List[float],
    sigma_floor:     float = 0.005,
) -> Optional[Dict[str, Any]]:
    """Segment predictions averaged with `weights` = segment durations (see module docstring)."""
    valid = [
        (pred, pl)
        for pred, pl in zip(seg_predictions, weights)
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
    meta_groups:      Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """meta_groups: target segment id -> metadata-mode neighbours (prognosis neighbours, see module docstring);
    None keeps the retrieval neighbours."""
    sigma_floor     = 0.005
    stage2_active   = bool(result.get('stage2_active'))
    path_length_map = _build_path_length_lookup(seg_batch or {})

    segment_groups:    list                 = result.get('segment_similarity', [])
    seg_predictions:   List[Optional[Dict]] = []
    seg_path_lengths:  List[float]          = []
    seg_agg_weights:   List[float]          = []  # segment duration (fallback: path length)
    seg_query_ids:     List[str]            = []
    seg_neighbor_ids:  List[List[str]]      = []
    stage1_seg_preds:  List[Dict]           = []

    switch_thr = await dtw_switch_threshold(conn, calibration_tag) if stage2_active and meta_groups else None

    for group in segment_groups:
        query_seg_id = group.get('target_segment', '')
        seg_results  = group.get('similar_segments', {}).get('results', [])

        seg_features   = group.get('target_segment_features') or {}
        query_path_len = float(seg_features.get('length') or 0.0)
        if query_path_len <= EPSILON:
            query_path_len = path_length_map.get(query_seg_id, 0.0)
        if query_path_len <= EPSILON:
            # Candidate trajectories have no stored features — estimate from neighbors
            neighbor_lengths = [
                float((r.get('features') or {}).get('length') or 0.0)
                for r in seg_results
            ]
            valid_nl = [l for l in neighbor_lengths if l > EPSILON]
            query_path_len = sum(valid_nl) / len(valid_nl) if valid_nl else 1.0
        if query_path_len > EPSILON:
            path_length_map[query_seg_id] = query_path_len
        seg_duration = float(seg_features.get('duration') or 0.0)
        agg_weight   = seg_duration if seg_duration > EPSILON else query_path_len

        meta_results = (meta_groups or {}).get(query_seg_id)
        meta_pred = _predict_stage1_rrf(
            results=meta_results, feature=feature, sigma_floor=sigma_floor,
        ) if meta_results else None
        if meta_pred is not None:
            meta_pred['source'] = 'metadata'
        # Stage 1 prognosis (also the stage1 calibration rows): metadata neighbours, retrieval neighbours as fallback
        s1_pred = meta_pred or _predict_stage1_rrf(results=seg_results, feature=feature, sigma_floor=sigma_floor)

        if stage2_active:
            dtw_pred = _predict_segment(
                seg_results=seg_results, query_path_length=query_path_len,
                feature=feature, sigma_floor=sigma_floor,
            )
            if dtw_pred is not None:
                dtw_pred['source'] = 'dtw'
                dtw_pred['p_hat_dtw'] = dtw_pred['p_hat']  # kept for refitting the threshold (calibration rows)
            near_identical = (dtw_pred is not None and switch_thr is not None
                              and dtw_pred['d_min'] < switch_thr * query_path_len)
            if near_identical or meta_pred is None:
                prediction = dtw_pred
            else:  # metadata p_hat/sigma; d_* stay DTW distances (match quality, refitting the threshold)
                prediction = {**meta_pred, **({k: dtw_pred[k] for k in ('d_min', 'd_max', 'd_normalized', 'p_hat_dtw')}
                                              if dtw_pred else {})}
        else:
            prediction = s1_pred

        if prediction is not None:
            prediction['query_path_length'] = query_path_len if query_path_len > EPSILON else None
            prediction['aggregation_weight'] = agg_weight
        stage1_seg_preds.append({
            'seg_id':            query_seg_id,
            'p_hat':             s1_pred.get('p_hat')        if s1_pred else None,
            'sigma':             s1_pred.get('sigma')        if s1_pred else None,
            'd_min':             s1_pred.get('d_min')        if s1_pred else None,
            'd_max':             s1_pred.get('d_max')        if s1_pred else None,
            'd_normalized':      s1_pred.get('d_normalized') if s1_pred else None,
            'query_path_length': query_path_len if query_path_len > EPSILON else None,
            'aggregation_weight': agg_weight,
        })

        used = meta_results if prediction is not None and prediction.get('source') == 'metadata' else seg_results
        nids = [str(r['seg_id']) for r in used if r.get('seg_id')]
        group['prediction'] = prediction
        seg_predictions.append(prediction)
        seg_path_lengths.append(query_path_len)
        seg_agg_weights.append(agg_weight)
        seg_query_ids.append(query_seg_id)
        seg_neighbor_ids.append(nids)

    decomposed_prediction = _aggregate_trajectory_decomposed(
        seg_predictions=seg_predictions,
        weights=seg_agg_weights,
        sigma_floor=sigma_floor,
    )

    traj_results            = result.get('traj_similarity', {}).get('results', [])
    traj_features           = result.get('target_traj_features') or {}
    total_query_path_length = float(traj_features.get('length') or 0) or sum(seg_path_lengths)

    if decomposed_prediction is not None:
        decomposed_prediction['query_path_length'] = total_query_path_length or None

    traj_neighbor_ids = [str(r['seg_id']) for r in traj_results if r.get('seg_id')]

    # Stage 1: RRF-weighted predictions (always computed — needed for calibration even in Stage 2)
    s1_direct_prediction = _predict_stage1_rrf(
        results=traj_results, feature=feature, sigma_floor=sigma_floor,
    )
    if s1_direct_prediction is not None:
        s1_direct_prediction['neighbor_ids']      = traj_neighbor_ids
        s1_direct_prediction['query_path_length'] = total_query_path_length or None

    # Stage 1 decomposed: duration-weighted aggregate of segment-level RRF predictions
    s1_decomposed_prediction = _aggregate_trajectory_decomposed(
        seg_predictions=[
            {'p_hat': s.get('p_hat'), 'sigma': s.get('sigma'),
             'd_min': s.get('d_min'), 'd_max': s.get('d_max'),
             'd_normalized': s.get('d_normalized')}
            if s.get('p_hat') is not None else None
            for s in stage1_seg_preds
        ],
        weights=seg_agg_weights,
        sigma_floor=sigma_floor,
    )

    if s1_decomposed_prediction is not None:
        s1_decomposed_prediction['query_path_length'] = total_query_path_length or None

    if stage2_active:
        direct_prediction = _predict_direct(
            traj_results=traj_results, query_path_length=total_query_path_length,
            feature=feature, sigma_floor=sigma_floor,
        )
        if direct_prediction is not None:
            direct_prediction['neighbor_ids']      = traj_neighbor_ids
            direct_prediction['query_path_length'] = total_query_path_length or None
    else:
        direct_prediction = s1_direct_prediction

    # Build segments list — only expose what the frontend needs
    segments = []
    for sid, pred, nids in zip(seg_query_ids, seg_predictions, seg_neighbor_ids):
        if pred:
            segments.append({
                'seg_id':            sid,
                'p_hat':             pred.get('p_hat'),
                'sigma':             pred.get('sigma'),
                'n_neighbors':       pred.get('n_neighbors'),
                'd_min':             pred.get('d_min'),
                'd_max':             pred.get('d_max'),
                'd_normalized':      pred.get('d_normalized'),
                'query_path_length': pred.get('query_path_length'),
                'neighbor_ids':      nids,
                'source':            pred.get('source', 'rrf'),
                'p_hat_dtw':         pred.get('p_hat_dtw'),
            })
        else:
            segments.append({'seg_id': sid, 'p_hat': None})

    result['prognosis'] = {
        'feature':                          feature,
        'stage':                            'stage2_dtw' if stage2_active else 'stage1_rrf',
        # Stage 2 (DTW) predictions
        'decomposed':                       decomposed_prediction,
        'direct':                           direct_prediction,
        # Stage 1 (RRF) predictions — always computed, used for calibration even in Stage 2 mode
        's1_direct':                        s1_direct_prediction,
        's1_decomposed':                    s1_decomposed_prediction,
        's1_segments':                      stage1_seg_preds,
        # Conformal intervals (filled in by conformal_predictor.py)
        'decomposed_conformal_interval':    None,
        'direct_conformal_interval':        None,
        's1_direct_conformal_interval':     None,
        's1_decomposed_conformal_interval': None,
        'segments':                         segments,
        'dtw_switch_d_per_length':          switch_thr,  # None: metadata only (shown in the frontend)
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