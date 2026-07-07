"""
feature_prediction/conformal_predictor.py
==========================================
Conformal prediction intervals.

Lookup strategy (Problem 1 — fuzzy quantile lookup)
-----------------------------------------------------
Exact match first, then progressive fallback:
  1. Exact:  metric + dtw_mode + strategy + level + k + search_modes + tag + coverage
  2. k diff: same but nearest available k (closest abs diff)
  3. modes:  same but ignore search_modes (any modes, same k preferred)
  4. tag:    same but tag='all' (if original tag != 'all')

Each fallback that fires attaches a CalibrationMismatch to the result
so the frontend can show a warning.

Problem 2 — Stage 1 conformal
-------------------------------
Stage 1 (RRF) produces no conformal interval — only p_hat/sigma.
compute_conformal_intervals() is only called with stage2_active=True.
This is enforced in predictor.py, not here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import asyncpg

from .conformal_config import CalibrationConfig, RetrievalStrategy, get_active_config
from .quality_match import get_match_quality

logger = logging.getLogger(__name__)

EPSILON     = 1e-6
DEFAULT_COV = 0.90

# Simple in-process cache: key → (quantile, mismatch_or_None)
_quantile_cache: Dict[str, Tuple[float, Optional['CalibrationMismatch']]] = {}


# ═══════════════════════════════════════════════════════════════════════════
# Mismatch descriptor
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CalibrationMismatch:
    """Describes how the found quantile differs from what was requested."""
    warning:           str
    requested_k:       Optional[int]   = None
    used_k:            Optional[int]   = None
    requested_modes:   Optional[str]   = None
    used_modes:        Optional[str]   = None
    requested_tag:     Optional[str]   = None
    used_tag:          Optional[str]   = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ═══════════════════════════════════════════════════════════════════════════
# DB fetch helpers
# ═══════════════════════════════════════════════════════════════════════════

async def _fetch_exact(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float,
) -> Optional[float]:
    row = await conn.fetchrow("""
        SELECT quantile_value
        FROM prognosis.confidence_quantiles
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
    return float(row['quantile_value']) if row else None


async def _fetch_nearest_k(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float,
) -> Optional[Tuple[float, int]]:
    """Find row with nearest available k, same search_modes and tag."""
    rows = await conn.fetch("""
        SELECT quantile_value, config_k
        FROM prognosis.confidence_quantiles
        WHERE metric             = $1
          AND dtw_mode           = $2
          AND retrieval_strategy = $3
          AND level              = $4
          AND search_modes       = $5
          AND calibration_tag    = $6
          AND coverage           = $7
        ORDER BY ABS(config_k - $8), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, search_modes_str, tag, float(coverage), k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['config_k'])
    return None


async def _fetch_any_modes(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, tag: str, coverage: float,
) -> Optional[Tuple[float, int, str]]:
    """Find row ignoring search_modes, nearest k."""
    rows = await conn.fetch("""
        SELECT quantile_value, config_k, search_modes
        FROM prognosis.confidence_quantiles
        WHERE metric             = $1
          AND dtw_mode           = $2
          AND retrieval_strategy = $3
          AND level              = $4
          AND calibration_tag    = $5
          AND coverage           = $6
        ORDER BY ABS(config_k - $7), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, tag, float(coverage), k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['config_k']), str(rows[0]['search_modes'])
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Main quantile lookup — with fuzzy fallback
# ═══════════════════════════════════════════════════════════════════════════

def _cache_key(
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float,
) -> str:
    return f"{metric}:{dtw_mode}:{strategy}:{level}:{k}:{search_modes_str}:{tag}:{coverage}"


async def get_calibration_quantile(
    conn:     asyncpg.Connection,
    cfg:      CalibrationConfig,
    coverage: float = DEFAULT_COV,
    level:    str   = 'trajectory',
) -> Tuple[Optional[float], Optional[CalibrationMismatch]]:
    """
    Lookup conformal quantile with progressive fuzzy fallback.

    Returns (quantile_value, mismatch_or_None).
    mismatch is None on exact match, otherwise describes what was used.
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

    # ── Step 1: Exact match ───────────────────────────────────────────────
    q = await _fetch_exact(conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage)
    if q is not None:
        _quantile_cache[ck] = (q, None)
        return q, None

    # ── Step 2: Nearest k, same modes + tag ──────────────────────────────
    result = await _fetch_nearest_k(conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage)
    if result is not None:
        q, used_k = result
        mismatch = CalibrationMismatch(
            warning=f"k mismatch: calibrated with k={used_k}, requested k={k}. Interval may be slightly miscalibrated.",
            requested_k=k,
            used_k=used_k,
        )
        logger.info(f"Fuzzy quantile lookup: k {k}→{used_k} ({metric}/{dtw_mode}/{strategy}/{level})")
        _quantile_cache[ck] = (q, mismatch)
        return q, mismatch

    # ── Step 3: Nearest k, any modes, same tag ───────────────────────────
    result2 = await _fetch_any_modes(conn, metric, dtw_mode, strategy, level, k, tag, coverage)
    if result2 is not None:
        q, used_k, used_modes = result2
        mismatch = CalibrationMismatch(
            warning=f"search_modes mismatch: calibrated with [{used_modes}], requested [{search_modes_str}]. "
                    f"k={used_k} used. Interval may be miscalibrated.",
            requested_k=k,
            used_k=used_k,
            requested_modes=search_modes_str,
            used_modes=used_modes,
        )
        logger.info(f"Fuzzy quantile lookup: modes+k mismatch, using [{used_modes}] k={used_k}")
        _quantile_cache[ck] = (q, mismatch)
        return q, mismatch

    # ── Step 4: Fallback to tag='all' ────────────────────────────────────
    if tag != 'all':
        # Try exact with tag='all'
        q = await _fetch_exact(conn, metric, dtw_mode, strategy, level, k, search_modes_str, 'all', coverage)
        if q is not None:
            mismatch = CalibrationMismatch(
                warning=f"calibration_tag '{tag}' not found, using tag='all'.",
                requested_tag=tag,
                used_tag='all',
            )
            _quantile_cache[ck] = (q, mismatch)
            return q, mismatch

        # Nearest k + any modes with tag='all'
        result3 = await _fetch_any_modes(conn, metric, dtw_mode, strategy, level, k, 'all', coverage)
        if result3 is not None:
            q, used_k, used_modes = result3
            mismatch = CalibrationMismatch(
                warning=f"calibration_tag '{tag}' not found. Fell back to tag='all' with k={used_k}, modes=[{used_modes}]. "
                        f"Interval is approximate.",
                requested_k=k,
                used_k=used_k,
                requested_modes=search_modes_str,
                used_modes=used_modes,
                requested_tag=tag,
                used_tag='all',
            )
            _quantile_cache[ck] = (q, mismatch)
            return q, mismatch

    logger.warning(
        f"No conformal quantile found — "
        f"metric={metric} dtw_mode={dtw_mode} strategy={strategy} "
        f"level={level} k={k} modes={search_modes_str} "
        f"tag={tag} coverage={coverage}. "
        f"Run calibration_set_builder.py first."
    )
    _quantile_cache[ck] = (None, None)
    return None, None

async def get_calibration_quantile_for_tags(
    conn:     asyncpg.Connection,
    cfg:      CalibrationConfig,
    tags:     Sequence[str],
    coverage: float = DEFAULT_COV,
    level:    str   = 'trajectory',
) -> Tuple[Optional[float], Optional[CalibrationMismatch]]:
    """
    Weighted-average quantile over multiple tags.

    Tags with n_calibration < MIN_N_CALIBRATION are skipped.
    Falls back to tag='all' if no tag passes the threshold.
    """
    MIN_N_CALIBRATION = 500

    if not tags or (len(tags) == 1 and tags[0] == 'all'):
        return await get_calibration_quantile(conn, cfg, coverage, level)

    metric           = cfg.metric
    dtw_mode         = cfg.dtw_mode
    strategy         = cfg.retrieval_strategy
    k                = cfg.k
    search_modes_str = cfg.search_modes_str()

    weighted_sum = 0.0
    total_weight = 0
    used_tags    = []
    skipped_tags = []

    for tag in tags:
        result = await _fetch_exact_with_n(
            conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage,
        )
        if result is None:
            skipped_tags.append(tag)
            continue
        q, n_cal = result
        if n_cal < MIN_N_CALIBRATION:
            skipped_tags.append(f"{tag}(n={n_cal})")
            continue
        weighted_sum += q * n_cal
        total_weight += n_cal
        used_tags.append(tag)

    if total_weight > 0:
        q_avg    = weighted_sum / total_weight
        mismatch = None
        if skipped_tags:
            mismatch = CalibrationMismatch(
                warning=f"Tags {skipped_tags} skipped (n_calibration < {MIN_N_CALIBRATION}). "
                        f"Weighted average over {used_tags}.",
            )
        return q_avg, mismatch

    # Fallback auf 'all'
    logger.warning(f"No tags passed threshold {MIN_N_CALIBRATION}, falling back to tag='all'")
    q, mm = await get_calibration_quantile(conn, replace(cfg, calibration_tag='all'), coverage, level)
    if q is not None:
        mismatch = CalibrationMismatch(
            warning=f"All tags {list(tags)} had n_calibration < {MIN_N_CALIBRATION}. Fell back to tag='all'.",
            requested_tag=','.join(tags),
            used_tag='all',
        )
        return q, mismatch
    return None, None

# ═══════════════════════════════════════════════════════════════════════════
# Interval computation
# ═══════════════════════════════════════════════════════════════════════════

def _compute_segment_interval(
    group:       Dict[str, Any],
    q:           float,
    sigma_floor: float,
    coverage:    float,
    mismatch:    Optional[CalibrationMismatch] = None,
) -> Optional[Dict[str, Any]]:
    prediction = group.get('prediction')
    if prediction is None or prediction.get('p_hat') is None:
        return None

    p_hat = float(prediction['p_hat'])
    sigma = float(prediction['sigma'])
    half  = q * sigma

    result: Dict[str, Any] = {
        'p_hat':    round(p_hat,                  4),
        'sigma':    round(sigma,                  6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half,           4),
        'coverage': coverage,
    }
    if mismatch is not None:
        result['calibration_mismatch'] = mismatch.to_dict()
    return result


def _aggregate_trajectory_interval(
    seg_intervals:    List[Optional[Dict]],
    seg_path_lengths: List[float],
    q:                float,
    sigma_floor:      float,
    coverage:         float,
    mismatch:         Optional[CalibrationMismatch] = None,
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

    result: Dict[str, Any] = {
        'p_hat':      round(p_hat,                  4),
        'sigma':      round(sigma,                  6),
        'low':        round(max(0.0, p_hat - half), 4),
        'high':       round(p_hat + half,           4),
        'coverage':   coverage,
        'n_segments': len(valid),
    }
    if mismatch is not None:
        result['calibration_mismatch'] = mismatch.to_dict()
    return result


async def compute_conformal_intervals(
    result:          Dict[str, Any],
    conn:            asyncpg.Connection,
    strategy:        RetrievalStrategy          = 'decomposed',
    coverage:        float                      = DEFAULT_COV,
    calibration_tag: str | List[str]            = 'all',
    n_points_map:    Optional[Dict[str, int]]   = None,   # kept for API compat, unused
    path_length_map: Optional[Dict[str, float]] = None,
    k:               Optional[int]              = None,
    search_modes:    Optional[Tuple[str, ...]]  = None,
    dtw_mode:        str                        = 'position',
    metric:          str                        = 'sidtw',
) -> Dict[str, Any]:
    """
    Compute and attach conformal intervals to result.

    Writes:
      result['prognosis']['decomposed_conformal_interval']  — trajectory level
      group['conformal_interval']                           — segment level
    """
    if path_length_map is None:
        path_length_map = {}

    cfg = get_active_config(strategy, calibration_tag, k=k, search_modes=search_modes, dtw_mode=dtw_mode, metric=metric)

    tags = [calibration_tag] if isinstance(calibration_tag, str) else calibration_tag
    q_seg,  mm_seg  = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'segment')
    q_traj, mm_traj = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'trajectory')

    if q_seg is None and q_traj is None:
        if 'prognosis' in result:
            result['prognosis']['decomposed_conformal_interval'] = None
        return result

    q_for_seg   = q_seg  if q_seg  is not None else q_traj
    mm_for_seg  = mm_seg if q_seg  is not None else mm_traj
    q_for_traj  = q_traj if q_traj is not None else q_seg
    mm_for_traj = mm_traj if q_traj is not None else mm_seg
    sigma_floor = cfg.sigma_floor

    segment_groups    = result.get('segment_similarity', [])
    seg_intervals:    List[Optional[Dict]] = []
    seg_path_lengths: List[float]          = []

    for group in segment_groups:
        interval = _compute_segment_interval(
            group=group, q=q_for_seg, sigma_floor=sigma_floor,
            coverage=coverage, mismatch=mm_for_seg,
        )

        if interval is not None:
            prediction = group.get('prediction') or {}
            match_quality = await get_match_quality(
                conn, prediction.get('d_min_per_path_length'),
                level='segment', retrieval_strategy=strategy,
                calibration_tag=calibration_tag,
                metric=cfg.metric, dtw_mode=cfg.dtw_mode,
                k=cfg.k, search_modes=cfg.search_modes,
            )
            if match_quality is not None:
                interval['match_quality'] = match_quality.__dict__
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
        mismatch=mm_for_traj,
    ) if seg_intervals else None

    if traj_interval is not None:
        decomposed_pred = (result.get('prognosis') or {}).get('decomposed') or {}
        match_quality = await get_match_quality(
            conn, decomposed_pred.get('d_min_per_path_length'),
            level='trajectory', retrieval_strategy=strategy,
            calibration_tag=calibration_tag,
            metric=cfg.metric, dtw_mode=cfg.dtw_mode,
            k=cfg.k, search_modes=cfg.search_modes,
        )
        if match_quality is not None:
            traj_interval['match_quality'] = match_quality.__dict__

    if 'prognosis' in result:
        result['prognosis']['decomposed_conformal_interval'] = traj_interval

    return result

async def _compute_direct_conformal_interval(
    prediction:      Dict[str, Any],
    conn:            asyncpg.Connection,
    coverage:        float                     = 0.90,
    calibration_tag: str | List[str]           = 'all',
    k:               int                       = 10,
    search_modes:    Optional[Tuple[str, ...]] = None,
    dtw_mode:        str                       = 'position',
    metric:          str                       = 'sidtw',
) -> Optional[Dict[str, Any]]:

    tags = [calibration_tag] if isinstance(calibration_tag, str) else calibration_tag
    cfg  = get_active_config('direct', tags[0], k=k, search_modes=search_modes, dtw_mode=dtw_mode, metric=metric)

    q, mismatch = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, level='trajectory')
    if q is None:
        return None

    p_hat = prediction['p_hat']
    sigma = prediction['sigma']
    half  = q * sigma

    result: Dict[str, Any] = {
        'p_hat':    p_hat,
        'sigma':    round(sigma, 6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half, 4),
        'coverage': coverage,
        'strategy': 'direct',
    }
    if mismatch is not None:
        result['calibration_mismatch'] = mismatch.to_dict()
    return result

async def _fetch_exact_with_n(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float,
) -> Optional[Tuple[float, int]]:
    """Fetch exact quantile + n_calibration for weighted averaging."""
    rows = await conn.fetch("""
        SELECT quantile_value, n_calibration
        FROM prognosis.confidence_quantiles
        WHERE metric             = $1
          AND dtw_mode           = $2
          AND retrieval_strategy = $3
          AND level              = $4
          AND search_modes       = $5
          AND calibration_tag    = $6
          AND coverage           = $7
        ORDER BY ABS(config_k - $8), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, search_modes_str, tag, float(coverage), k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['n_calibration'])
    return None