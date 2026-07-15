"""
conformal_predictor.py
======================
Conformal prediction intervals for Stage 1 (RRF) and Stage 2 (DTW).

Lookup key for confidence_quantiles
-------------------------------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag + config_stage

Lookup strategy (fuzzy fallback)
----------------------------------
  1. Exact:  all key fields match
  2. k diff: nearest available k, same modes + tag + stage
  3. modes:  any modes, same tag + stage
  4. tag:    tag='all', same stage

Each fallback attaches a CalibrationMismatch so the frontend can warn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import asyncpg

from .conformal_config import CalibrationConfig, get_active_config
from .quality_match import get_match_quality

logger = logging.getLogger(__name__)

EPSILON     = 1e-6
DEFAULT_COV = 0.90

# Simple in-process cache: key → (quantile, mismatch_or_None)
_quantile_cache: Dict[str, Tuple[Optional[float], Optional['CalibrationMismatch']]] = {}


# ═══════════════════════════════════════════════════════════════════════════
# Mismatch descriptor
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CalibrationMismatch:
    warning:         str
    requested_k:     Optional[int] = None
    used_k:          Optional[int] = None
    requested_modes: Optional[str] = None
    used_modes:      Optional[str] = None
    requested_tag:   Optional[str] = None
    used_tag:        Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ═══════════════════════════════════════════════════════════════════════════
# DB fetch helpers
# ═══════════════════════════════════════════════════════════════════════════

async def _fetch_exact(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float, config_stage: int,
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
          AND config_stage       = $9
        ORDER BY computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, k, search_modes_str, tag, float(coverage), config_stage)
    return float(row['quantile_value']) if row else None


async def _fetch_nearest_k(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float, config_stage: int,
) -> Optional[Tuple[float, int]]:
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
          AND config_stage       = $8
        ORDER BY ABS(config_k - $9), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, search_modes_str, tag, float(coverage), config_stage, k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['config_k'])
    return None


async def _fetch_any_modes(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, tag: str, coverage: float, config_stage: int,
) -> Optional[Tuple[float, int, str]]:
    rows = await conn.fetch("""
        SELECT quantile_value, config_k, search_modes
        FROM prognosis.confidence_quantiles
        WHERE metric             = $1
          AND dtw_mode           = $2
          AND retrieval_strategy = $3
          AND level              = $4
          AND calibration_tag    = $5
          AND coverage           = $6
          AND config_stage       = $7
        ORDER BY ABS(config_k - $8), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, tag, float(coverage), config_stage, k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['config_k']), str(rows[0]['search_modes'])
    return None


async def _fetch_exact_with_n(
    conn: asyncpg.Connection,
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float, config_stage: int,
) -> Optional[Tuple[float, int]]:
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
          AND config_stage       = $8
        ORDER BY ABS(config_k - $9), computed_at DESC
        LIMIT 1
    """, metric, dtw_mode, strategy, level, search_modes_str, tag, float(coverage), config_stage, k)
    if rows:
        return float(rows[0]['quantile_value']), int(rows[0]['n_calibration'])
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Cache key
# ═══════════════════════════════════════════════════════════════════════════

def _cache_key(
    metric: str, dtw_mode: str, strategy: str, level: str,
    k: int, search_modes_str: str, tag: str, coverage: float, config_stage: int,
) -> str:
    return f"{metric}:{dtw_mode}:{strategy}:{level}:{k}:{search_modes_str}:{tag}:{coverage}:{config_stage}"


# ═══════════════════════════════════════════════════════════════════════════
# Main quantile lookup — with fuzzy fallback
# ═══════════════════════════════════════════════════════════════════════════

async def get_calibration_quantile(
    conn:         asyncpg.Connection,
    cfg:          CalibrationConfig,
    coverage:     float = DEFAULT_COV,
    level:        str   = 'trajectory',
) -> Tuple[Optional[float], Optional[CalibrationMismatch]]:
    """
    Lookup conformal quantile with progressive fuzzy fallback.
    Returns (quantile_value, mismatch_or_None).
    """
    metric           = cfg.metric
    dtw_mode         = cfg.dtw_mode
    strategy         = cfg.retrieval_strategy
    k                = cfg.k
    search_modes_str = cfg.search_modes_str()
    tag              = cfg.calibration_tag
    stage            = cfg.config_stage

    ck = _cache_key(metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage, stage)
    if ck in _quantile_cache:
        return _quantile_cache[ck]

    # Step 1: Exact match
    q = await _fetch_exact(conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage, stage)
    if q is not None:
        _quantile_cache[ck] = (q, None)
        return q, None

    # Step 2: Nearest k, same modes + tag
    result = await _fetch_nearest_k(conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage, stage)
    if result is not None:
        q, used_k = result
        mismatch = CalibrationMismatch(
            warning=f"k mismatch: calibrated with k={used_k}, requested k={k}.",
            requested_k=k, used_k=used_k,
        )
        logger.info(f"Fuzzy quantile: k {k}→{used_k} ({metric}/{dtw_mode}/{strategy}/{level}/stage{stage})")
        _quantile_cache[ck] = (q, mismatch)
        return q, mismatch

    # Step 3: Nearest k, any modes, same tag
    result2 = await _fetch_any_modes(conn, metric, dtw_mode, strategy, level, k, tag, coverage, stage)
    if result2 is not None:
        q, used_k, used_modes = result2
        mismatch = CalibrationMismatch(
            warning=f"search_modes mismatch: calibrated with [{used_modes}], requested [{search_modes_str}]. k={used_k}.",
            requested_k=k, used_k=used_k,
            requested_modes=search_modes_str, used_modes=used_modes,
        )
        logger.info(f"Fuzzy quantile: modes+k mismatch, using [{used_modes}] k={used_k}")
        _quantile_cache[ck] = (q, mismatch)
        return q, mismatch

    # Step 4: Fallback to tag='all', same stage
    if tag != 'all':
        q = await _fetch_exact(conn, metric, dtw_mode, strategy, level, k, search_modes_str, 'all', coverage, stage)
        if q is not None:
            mismatch = CalibrationMismatch(
                warning=f"calibration_tag '{tag}' not found, using tag='all'.",
                requested_tag=tag, used_tag='all',
            )
            _quantile_cache[ck] = (q, mismatch)
            return q, mismatch

        result3 = await _fetch_any_modes(conn, metric, dtw_mode, strategy, level, k, 'all', coverage, stage)
        if result3 is not None:
            q, used_k, used_modes = result3
            mismatch = CalibrationMismatch(
                warning=f"tag '{tag}' not found. Fell back to tag='all', k={used_k}, modes=[{used_modes}].",
                requested_k=k, used_k=used_k,
                requested_modes=search_modes_str, used_modes=used_modes,
                requested_tag=tag, used_tag='all',
            )
            _quantile_cache[ck] = (q, mismatch)
            return q, mismatch

    logger.warning(
        f"No conformal quantile found — metric={metric} dtw_mode={dtw_mode} "
        f"strategy={strategy} level={level} k={k} modes={search_modes_str} "
        f"tag={tag} coverage={coverage} stage={stage}. "
        f"Run calibration_set_builder.py first."
    )
    _quantile_cache[ck] = (None, None)
    return None, None


async def get_calibration_quantile_for_tags(
    conn:         asyncpg.Connection,
    cfg:          CalibrationConfig,
    tags:         Sequence[str],
    coverage:     float = DEFAULT_COV,
    level:        str   = 'trajectory',
) -> Tuple[Optional[float], Optional[CalibrationMismatch]]:
    """
    Weighted-average quantile over multiple tags.
    Tags with n_calibration < MIN_N_CALIBRATION are skipped.
    Falls back to tag='all' if no tag passes the threshold.
    """
    MIN_N_CALIBRATION = 150

    if not tags or (len(tags) == 1 and tags[0] == 'all'):
        return await get_calibration_quantile(conn, cfg, coverage, level)

    metric           = cfg.metric
    dtw_mode         = cfg.dtw_mode
    strategy         = cfg.retrieval_strategy
    k                = cfg.k
    search_modes_str = cfg.search_modes_str()
    stage            = cfg.config_stage

    weighted_sum = 0.0
    total_weight = 0
    used_tags    = []
    skipped_tags = []

    for tag in tags:
        result = await _fetch_exact_with_n(
            conn, metric, dtw_mode, strategy, level, k, search_modes_str, tag, coverage, stage,
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

    # All tags skipped — fall back to 'all'
    cfg_all = cfg.with_tag('all')
    q, mm   = await get_calibration_quantile(conn, cfg_all, coverage, level)
    if q is not None:
        mm2 = CalibrationMismatch(
            warning=f"All tags {tags} had insufficient calibration data. Using tag='all'.",
            requested_tag=str(tags), used_tag='all',
        )
        return q, mm2
    return None, None


# ═══════════════════════════════════════════════════════════════════════════
# Interval builders
# ═══════════════════════════════════════════════════════════════════════════

def _build_interval(
    p_hat: float, sigma: float, q: float,
    coverage: float, mismatch: Optional[CalibrationMismatch],
    strategy: str,
    n_segments: Optional[int] = None,
) -> Dict[str, Any]:
    half   = q * sigma
    result: Dict[str, Any] = {
        'p_hat':    round(p_hat, 4),
        'sigma':    round(sigma, 6),
        'low':      round(max(0.0, p_hat - half), 4),
        'high':     round(p_hat + half, 4),
        'coverage': coverage,
        'strategy': strategy,
    }
    if n_segments is not None:
        result['n_segments'] = n_segments
    if mismatch is not None:
        result['calibration_mismatch'] = mismatch.to_dict()
    return result


def _compute_segment_interval(
    group: Dict[str, Any], q: float, sigma_floor: float,
    coverage: float, mismatch: Optional[CalibrationMismatch],
) -> Optional[Dict[str, Any]]:
    prediction = group.get('prediction') or {}
    p_hat = prediction.get('p_hat')
    sigma = prediction.get('sigma')
    if p_hat is None or sigma is None:
        return None
    sigma = max(float(sigma), sigma_floor, EPSILON)
    return _build_interval(float(p_hat), sigma, q, coverage, mismatch, 'decomposed')


def _aggregate_trajectory_interval(
    seg_intervals: List[Optional[Dict]], seg_path_lengths: List[float],
    q: float, sigma_floor: float, coverage: float,
    mismatch: Optional[CalibrationMismatch],
    strategy: str = 'decomposed',
) -> Optional[Dict[str, Any]]:
    valid = [
        (iv, pl) for iv, pl in zip(seg_intervals, seg_path_lengths)
        if iv is not None and pl > EPSILON
    ]
    if not valid:
        return None
    total  = sum(pl for _, pl in valid)
    p_hat  = sum(iv['p_hat'] * pl for iv, pl in valid) / total
    sigma  = max(sum(iv['sigma'] * pl for iv, pl in valid) / total, sigma_floor)
    return _build_interval(p_hat, sigma, q, coverage, mismatch, strategy, n_segments=len(valid))


# ═══════════════════════════════════════════════════════════════════════════
# Public: compute Stage 2 conformal intervals
# ═══════════════════════════════════════════════════════════════════════════

async def compute_conformal_intervals(
    result:          Dict[str, Any],
    conn:            asyncpg.Connection,
    strategy:        str                        = 'decomposed',
    coverage:        float                      = DEFAULT_COV,
    calibration_tag: str | List[str]            = 'all',
    path_length_map: Optional[Dict[str, float]] = None,
    k:               Optional[int]              = None,
    search_modes:    Optional[Tuple[str, ...]]  = None,
    dtw_mode:        str                        = 'position',
    metric:          str                        = 'sidtw',
) -> Dict[str, Any]:
    """
    Compute and attach Stage 2 conformal intervals to result.

    Writes:
      result['prognosis']['decomposed_conformal_interval']  — trajectory
      group['conformal_interval']                           — per segment
      result['prognosis']['direct_conformal_interval']      — direct trajectory
    """
    if path_length_map is None:
        path_length_map = {}

    cfg = get_active_config(
        strategy, calibration_tag if isinstance(calibration_tag, str) else calibration_tag[0],
        k=k, search_modes=search_modes, dtw_mode=dtw_mode, metric=metric, config_stage=2,
    )
    tags = [calibration_tag] if isinstance(calibration_tag, str) else calibration_tag

    q_seg,  mm_seg  = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'segment')
    q_traj, mm_traj = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'trajectory')

    if q_seg is None and q_traj is None:
        if 'prognosis' in result:
            result['prognosis']['decomposed_conformal_interval'] = None
            result['prognosis']['direct_conformal_interval']     = None
        return result

    q_for_seg   = q_seg  if q_seg  is not None else q_traj
    mm_for_seg  = mm_seg if q_seg  is not None else mm_traj
    q_for_traj  = q_traj if q_traj is not None else q_seg
    mm_for_traj = mm_traj if q_traj is not None else mm_seg
    sigma_floor = cfg.sigma_floor

    # ── Segment intervals ────────────────────────────────────────────────
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
            mq = await get_match_quality(
                conn,
                prediction.get('d_min'),
                level='segment',
                retrieval_strategy=strategy,
                calibration_tag=cfg.calibration_tag,
                metric=cfg.metric,
                dtw_mode=cfg.dtw_mode,
                k=cfg.k,
                search_modes=cfg.search_modes,
                config_stage=2,
            )
            if mq is not None:
                interval['match_quality'] = mq.__dict__
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

    # ── Decomposed trajectory interval ───────────────────────────────────
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
        mq = await get_match_quality(
            conn,
            decomposed_pred.get('d_min'),
            level='trajectory',
            retrieval_strategy=strategy,
            calibration_tag=cfg.calibration_tag,
            metric=cfg.metric,
            dtw_mode=cfg.dtw_mode,
            k=cfg.k,
            search_modes=cfg.search_modes,
            config_stage=2,
        )
        if mq is not None:
            traj_interval['match_quality'] = mq.__dict__

    if 'prognosis' in result:
        result['prognosis']['decomposed_conformal_interval'] = traj_interval

    # ── Direct trajectory interval ───────────────────────────────────────
    direct_interval = await _compute_direct_conformal_interval(
        result=result, conn=conn, cfg=cfg, tags=tags,
        coverage=coverage, sigma_floor=sigma_floor,
    )
    if 'prognosis' in result:
        result['prognosis']['direct_conformal_interval'] = direct_interval

    for group in segment_groups:
        group.pop('prediction', None)

    return result


async def _compute_direct_conformal_interval(
    result:      Dict[str, Any],
    conn:        asyncpg.Connection,
    cfg:         CalibrationConfig,
    tags:        Sequence[str],
    coverage:    float,
    sigma_floor: float,
) -> Optional[Dict[str, Any]]:
    """Stage 2 direct trajectory interval."""
    direct_cfg = get_active_config(
        'direct', cfg.calibration_tag,
        k=cfg.k, search_modes=cfg.search_modes,
        dtw_mode=cfg.dtw_mode, metric=cfg.metric, config_stage=2,
    )
    q, mismatch = await get_calibration_quantile_for_tags(conn, direct_cfg, tags, coverage, 'trajectory')
    if q is None:
        return None

    prognosis    = result.get('prognosis') or {}
    direct_pred  = prognosis.get('direct') or {}
    p_hat = direct_pred.get('p_hat')
    sigma = direct_pred.get('sigma')
    if p_hat is None or sigma is None:
        return None

    sigma  = max(float(sigma), sigma_floor, EPSILON)
    interval = _build_interval(float(p_hat), sigma, q, coverage, mismatch, 'direct')

    mq = await get_match_quality(
        conn,
        direct_pred.get('d_min'),
        level='trajectory',
        retrieval_strategy='direct',
        calibration_tag=direct_cfg.calibration_tag,
        metric=direct_cfg.metric,
        dtw_mode=direct_cfg.dtw_mode,
        k=direct_cfg.k,
        search_modes=direct_cfg.search_modes,
        config_stage=2,
    )
    if mq is not None:
        interval['match_quality'] = mq.__dict__

    return interval


# ═══════════════════════════════════════════════════════════════════════════
# Public: compute Stage 1 conformal interval
# ═══════════════════════════════════════════════════════════════════════════

async def compute_stage1_conformal_interval(
    result:          Dict[str, Any],
    conn:            asyncpg.Connection,
    coverage:        float                     = DEFAULT_COV,
    calibration_tag: str | List[str]           = 'all',
    k:               Optional[int]             = None,
    search_modes:    Optional[Tuple[str, ...]] = None,
    metric:          str                       = 'sidtw',
) -> None:
    """
    Compute Stage 1 conformal intervals — direct and decomposed.

    Writes directly into result['prognosis']:
      stage1_conformal_interval        — direct trajectory (RRF weighted)
      decomposed_conformal_interval    — segment-aggregated (length-weighted)
    """
    tags = [calibration_tag] if isinstance(calibration_tag, str) else calibration_tag
    cfg  = get_active_config(
        'stage1_rrf', tags[0],
        k=k, search_modes=search_modes,
        dtw_mode='none', metric=metric, config_stage=1,
    )
    sigma_floor = cfg.sigma_floor
    prognosis   = result.get('prognosis') or {}

    # ── Direct interval ──────────────────────────────────────────────────
    q_traj, mm_traj = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'trajectory')

    direct_interval = None
    if q_traj is not None:
        direct_pred = prognosis.get('direct') or {}
        p_hat = direct_pred.get('p_hat')
        sigma = direct_pred.get('sigma')
        if p_hat is not None and sigma is not None:
            sigma         = max(float(sigma), sigma_floor, EPSILON)
            direct_interval = _build_interval(float(p_hat), sigma, q_traj, coverage, mm_traj, 'stage1_rrf')
            mq = await get_match_quality(
                conn,
                direct_pred.get('d_min'),
                level='trajectory',
                retrieval_strategy='stage1_rrf',
                calibration_tag=cfg.calibration_tag,
                metric=cfg.metric,
                dtw_mode='none',
                k=cfg.k,
                search_modes=cfg.search_modes,
                config_stage=1,
            )
            if mq is not None:
                direct_interval['match_quality'] = mq.__dict__

    if 'prognosis' in result:
        result['prognosis']['stage1_conformal_interval'] = direct_interval

    # ── Decomposed interval — segment-level quantile, length-weighted ────
    q_seg, mm_seg = await get_calibration_quantile_for_tags(conn, cfg, tags, coverage, 'segment')
    if q_seg is None:
        return

    segment_groups   = result.get('segment_similarity', [])
    seg_intervals:   List[Optional[Dict]] = []
    seg_path_lengths: List[float]         = []

    for group in segment_groups:
        prediction = group.get('prediction') or {}
        p_hat = prediction.get('p_hat')
        sigma = prediction.get('sigma')
        if p_hat is None or sigma is None:
            seg_intervals.append(None)
            seg_path_lengths.append(0.0)
            continue

        sigma    = max(float(sigma), sigma_floor, EPSILON)
        interval = _build_interval(float(p_hat), sigma, q_seg, coverage, mm_seg, 'stage1_rrf')

        mq = await get_match_quality(
            conn,
            prediction.get('d_min'),
            level='segment',
            retrieval_strategy='stage1_rrf',
            calibration_tag=cfg.calibration_tag,
            metric=cfg.metric,
            dtw_mode='none',
            k=cfg.k,
            search_modes=cfg.search_modes,
            config_stage=1,
        )
        if mq is not None:
            interval['match_quality'] = mq.__dict__

        group['conformal_interval'] = interval
        seg_intervals.append(interval)

        pl = float(prediction.get('query_path_length') or 0.0)
        seg_path_lengths.append(pl)

    # Aggregate to trajectory level using length-weighted average
    traj_interval = _aggregate_trajectory_interval(
        seg_intervals=seg_intervals,
        seg_path_lengths=seg_path_lengths,
        q=q_seg,
        sigma_floor=sigma_floor,
        coverage=coverage,
        mismatch=mm_seg,
        strategy='stage1_rrf',
    )

    if traj_interval is not None:
        decomposed_pred = prognosis.get('decomposed') or {}
        mq = await get_match_quality(
            conn,
            decomposed_pred.get('d_min'),
            level='trajectory',
            retrieval_strategy='stage1_rrf',
            calibration_tag=cfg.calibration_tag,
            metric=cfg.metric,
            dtw_mode='none',
            k=cfg.k,
            search_modes=cfg.search_modes,
            config_stage=1,
        )
        if mq is not None:
            traj_interval['match_quality'] = mq.__dict__

    if 'prognosis' in result:
        result['prognosis']['decomposed_conformal_interval'] = traj_interval