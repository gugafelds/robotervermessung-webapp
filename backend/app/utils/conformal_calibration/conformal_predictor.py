# ═══════════════════════════════════════════════════════════════════════════
# conformal_predictor.py
# Gehört nach: backend/app/utils/conformal_calibration/conformal_predictor.py
#
# Wird aufgerufen am Ende des Stage-2-Blocks in similarity_route_handler.py
# NUR wenn stage2_active == True.
# ═══════════════════════════════════════════════════════════════════════════

import math
import logging
from typing import Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)

EPSILON = 1e-6
DEFAULT_COVERAGE = 0.90


# ── 1. Quantil aus DB lesen (gecacht pro Request) ───────────────────────────

async def get_calibration_quantile(
    conn: asyncpg.Connection,
    dtw_mode: str = 'position',
    metric: str = 'sidtw',
    coverage: float = DEFAULT_COVERAGE,
) -> Optional[float]:
    """
    Liest das gespeicherte Konfidenz-Quantil aus evaluation.confidence_quantiles.
    Gibt None zurück wenn kein Eintrag gefunden wird.
    """
    row = await conn.fetchrow("""
        SELECT quantile_value
        FROM evaluation.confidence_quantiles
        WHERE dtw_mode = $1
          AND metric   = $2
          AND coverage = $3
        ORDER BY computed_at DESC
        LIMIT 1
    """, dtw_mode, metric, coverage)

    if row is None:
        logger.warning(
            f"No calibration quantile found for "
            f"dtw_mode={dtw_mode}, metric={metric}, coverage={coverage}. "
            f"Run calibration_set_builder.py first."
        )
        return None

    return float(row['quantile_value'])


# ── 2. Segment-Intervall berechnen ──────────────────────────────────────────

def compute_segment_interval(
    seg_results: List[Dict],
    q: float,
) -> Optional[Dict]:
    """
    Berechnet das Conformal Prediction Intervall für ein einzelnes Segment.

    Eingabe: seg_results — Liste von Nachbarn mit 'dtw_distance' und
             features.mean_distance (nach Stage-2-Reranking)

    Ausgabe:
        p_hat    : inverse-DTW gewichtete Prognose [mm]
        sigma    : lokaler Spread = d_min × std(perf)
        low      : untere Intervallgrenze [mm]
        high     : obere Intervallgrenze [mm]
        coverage : Ziel-Coverage (z.B. 0.90)
        n        : Anzahl genutzter Nachbarn
    """
    # Nur Nachbarn mit beiden Feldern
    valid = []
    for r in seg_results:
        dtw_dist  = r.get('dtw_distance')
        mean_dist = None
        if r.get('features'):
            mean_dist = r['features'].get('mean_distance')
        if dtw_dist is not None and mean_dist is not None:
            valid.append({
                'dtw_distance':  float(dtw_dist),
                'mean_distance': float(mean_dist),
            })

    if len(valid) < 2:
        return None

    # Sortiert nach DTW-Distanz (Stage 2 macht das schon, aber sicher ist sicher)
    valid.sort(key=lambda x: x['dtw_distance'])

    dtw_dists   = [v['dtw_distance']  for v in valid]
    perf_values = [v['mean_distance'] for v in valid]

    # Inverse-DTW Gewichtung (Gleichung 3 im Paper)
    weights = [1.0 / (d + EPSILON) for d in dtw_dists]
    w_sum   = sum(weights)
    p_hat   = sum(w * p for w, p in zip(weights, perf_values)) / w_sum

    # Lokaler Spread: σ = d_min × std(perf)
    d_min    = dtw_dists[0]
    n        = len(perf_values)
    mean_p   = sum(perf_values) / n
    perf_std = math.sqrt(sum((p - mean_p) ** 2 for p in perf_values) / n)
    d_min_norm = d_min / (d_min + sum(dtw_dists) / len(dtw_dists) + EPSILON)
    sigma = d_min_norm * perf_std

    # Conformal Intervall
    half_width = q * sigma
    return {
        'p_hat':    round(p_hat,          4),
        'sigma':    round(sigma,          6),
        'low':      round(max(0.0, p_hat - half_width), 4),
        'high':     round(p_hat + half_width,           4),
        'coverage': DEFAULT_COVERAGE,
        'n':        n,
    }


# ── 3. Trajektorie-Intervall aggregieren (längengewichtet) ──────────────────

def aggregate_trajectory_interval(
    seg_intervals: List[Dict],
    seg_durations: List[float],
) -> Optional[Dict]:
    """
    Kombiniert Segment-Intervalle zu einem Trajektorie-Intervall.
    Längengewichtung wie im Paper (Gleichung für p_gs).

    Für die Intervallgrenzen: konservativ — wir nehmen den
    längengewichteten Mittelwert der Grenzen.
    Das ist konsistent mit der Decomposed-Prognose im Paper.
    """
    valid = [
        (iv, dur)
        for iv, dur in zip(seg_intervals, seg_durations)
        if iv is not None and dur is not None and dur > 0
    ]

    if not valid:
        return None

    total_dur = sum(dur for _, dur in valid)
    if total_dur == 0:
        return None

    p_hat = sum(iv['p_hat'] * dur for iv, dur in valid) / total_dur
    low   = sum(iv['low']   * dur for iv, dur in valid) / total_dur
    high  = sum(iv['high']  * dur for iv, dur in valid) / total_dur

    return {
        'p_hat':    round(p_hat, 4),
        'low':      round(max(0.0, low),  4),
        'high':     round(high,           4),
        'coverage': DEFAULT_COVERAGE,
        'n_segments': len(valid),
    }


# ── 4. Haupt-Einstiegspunkt für similarity_route_handler.py ─────────────────

async def compute_conformal_intervals(
    result: Dict,
    conn: asyncpg.Connection,
    dtw_mode: str = 'position',
    metric: str = 'sidtw',
) -> Dict:
    """
    Ergänzt das bestehende similarity_route_handler Result-Dict um
    'conformal_interval' auf Segment- und Trajektorie-Ebene.

    Aufruf am Ende des Stage-2-Blocks:

        from utils.conformal_calibration.conformal_predictor import (
            compute_conformal_intervals
        )
        result = await compute_conformal_intervals(
            result, conn, dtw_mode=dtw_mode
        )

    Gibt das erweiterte result-Dict zurück.
    """
    # Quantil aus DB laden
    q = await get_calibration_quantile(conn, dtw_mode=dtw_mode, metric=metric)
    if q is None:
        # Kein Calibration Set vorhanden — Intervall weglassen, kein Crash
        result['conformal_interval'] = None
        return result

    segment_groups = result.get('segment_similarity', [])
    seg_intervals  = []
    seg_durations  = []

    for group in segment_groups:
        seg_results = group.get('similar_segments', {}).get('results', [])
        duration    = (
            group.get('target_segment_features', {}) or {}
        ).get('duration')

        interval = compute_segment_interval(seg_results, q)

        # Interval ans jeweilige Segment-Group anhängen
        group['conformal_interval'] = interval

        if interval is not None and duration is not None:
            seg_intervals.append(interval)
            seg_durations.append(float(duration))

    # Trajektorie-Intervall aggregieren
    traj_interval = aggregate_trajectory_interval(seg_intervals, seg_durations)
    result['conformal_interval'] = traj_interval

    logger.debug(
        f"Conformal interval computed: "
        f"p_hat={traj_interval['p_hat'] if traj_interval else 'N/A'} "
        f"[{traj_interval['low'] if traj_interval else 'N/A'}, "
        f"{traj_interval['high'] if traj_interval else 'N/A'}] mm"
    )

    return result