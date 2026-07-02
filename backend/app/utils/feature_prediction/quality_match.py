"""
quality_match.py
=================
Empirical match-quality lookup based on d_min_per_path_length buckets.

Complements conformal intervals: instead of a statistically calibrated
coverage guarantee, this answers "matches like this one historically had
this error" — bucketed per (metric, dtw_mode, retrieval_strategy, level,
k, search_modes, calibration_tag).

Buckets are built offline (see populate_match_quality_buckets.sql) into
prognosis.confidence_match_quality. This module only reads them.

Lookup strategy mirrors get_calibration_quantile() in conformal_predictor.py:
  1. Exact match on (metric, dtw_mode, strategy, level, k, search_modes, tag)
  2. Fall back to calibration_tag='all' if the requested tag has no buckets
config_hash is NOT used for lookup (audit only) — same rationale as
conformal_config.py: it changes with tuning params (split_seed etc.)
that don't affect the actual retrieval configuration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import asyncpg

from .conformal_config import RetrievalStrategy, get_active_config

logger = logging.getLogger(__name__)

# Simple in-process cache: lookup key -> bucket rows (sorted by bucket)
_bucket_cache: Dict[Tuple, List[dict]] = {}

_TIER_EXCELLENT = 'excellent'
_TIER_GOOD      = 'good'
_TIER_MODERATE  = 'moderate'
_TIER_POOR      = 'poor'


@dataclass
class MatchQuality:
    expected_error_mm: float
    tier:               str    # excellent | good | moderate | poor
    bucket:             int
    n_buckets:          int
    n_samples:          int
    calibration_tag_used: str  # may differ from requested tag on fallback


# ═══════════════════════════════════════════════════════════════════════════
# Tier classification
# ═══════════════════════════════════════════════════════════════════════════

def _tier_for_bucket(bucket_error: float, best_error: float) -> str:
    """
    Classify a bucket relative to the best (lowest-error) bucket within the
    same lookup group — not a fixed absolute threshold, since baseline
    error varies substantially between calibration tags (see e.g. 'all'
    vs. 'new-map-test').
    """
    if best_error <= 0:
        return _TIER_EXCELLENT
    ratio = bucket_error / best_error
    if ratio <= 1.5:
        return _TIER_EXCELLENT
    if ratio <= 3.0:
        return _TIER_GOOD
    if ratio <= 6.0:
        return _TIER_MODERATE
    return _TIER_POOR


# ═══════════════════════════════════════════════════════════════════════════
# DB access
# ═══════════════════════════════════════════════════════════════════════════

async def _fetch_buckets(
    conn:               asyncpg.Connection,
    metric:              str,
    dtw_mode:            str,
    retrieval_strategy:  RetrievalStrategy,
    level:                str,
    k:                    int,
    search_modes_str:      str,
    calibration_tag:        str,
) -> List[dict]:
    cache_key = (metric, dtw_mode, retrieval_strategy, level, k, search_modes_str, calibration_tag)
    if cache_key in _bucket_cache:
        return _bucket_cache[cache_key]

    rows = await conn.fetch("""
        SELECT bucket, d_min_lower, d_min_upper, mean_error, median_error, n_samples
        FROM prognosis.confidence_match_quality
        WHERE metric              = $1
          AND dtw_mode            = $2
          AND retrieval_strategy  = $3
          AND level               = $4
          AND config_k            = $5
          AND search_modes        = $6
          AND calibration_tag     = $7
        ORDER BY bucket
    """, metric, dtw_mode, retrieval_strategy, level, k, search_modes_str, calibration_tag)

    buckets = [dict(r) for r in rows]
    _bucket_cache[cache_key] = buckets
    return buckets


# ═══════════════════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════════════════

async def get_match_quality(
    conn:                   asyncpg.Connection,
    d_min_per_path_length:   Optional[float],
    level:                    str,                          # 'segment' | 'trajectory'
    retrieval_strategy:        RetrievalStrategy = 'decomposed',
    calibration_tag:            str               = 'all',
    metric:                      str               = 'sidtw',
    dtw_mode:                     str               = 'position',
    k:                             Optional[int]    = None,
    search_modes:                  Optional[Tuple[str, ...]] = None,
) -> Optional[MatchQuality]:
    """
    Look up the empirical match-quality tier for a given d_min_per_path_length.

    Falls back to calibration_tag='all' if no buckets exist for the
    requested tag — same fallback philosophy as get_calibration_quantile().
    Returns None if no buckets are found at all (e.g. calibration not run
    yet for this configuration) or if d_min_per_path_length is None.
    """
    if d_min_per_path_length is None:
        return None

    cfg = get_active_config(retrieval_strategy, calibration_tag, k=k, search_modes=search_modes)
    used_tag = calibration_tag

    buckets = await _fetch_buckets(
        conn, metric, dtw_mode, retrieval_strategy, level,
        cfg.k, cfg.search_modes_str(), calibration_tag,
    )

    if not buckets and calibration_tag != 'all':
        buckets = await _fetch_buckets(
            conn, metric, dtw_mode, retrieval_strategy, level,
            cfg.k, cfg.search_modes_str(), 'all',
        )
        if buckets:
            used_tag = 'all'
            logger.info(
                f"[MatchQuality] tag='{calibration_tag}' has no buckets — "
                f"fell back to tag='all' (level={level}, strategy={retrieval_strategy})."
            )

    if not buckets:
        return None

    # Find the bucket whose [d_min_lower, d_min_upper] range contains the
    # value; clamp to the first/last bucket if outside the observed range
    # (e.g. a query more novel than anything seen during calibration).
    match = None
    for b in buckets:
        if b['d_min_lower'] <= d_min_per_path_length <= b['d_min_upper']:
            match = b
            break
    if match is None:
        match = buckets[0] if d_min_per_path_length < buckets[0]['d_min_lower'] else buckets[-1]

    best_error = min(b['mean_error'] for b in buckets)
    tier       = _tier_for_bucket(match['mean_error'], best_error)

    return MatchQuality(
        expected_error_mm    = round(float(match['mean_error']), 4),
        tier                  = tier,
        bucket                = match['bucket'],
        n_buckets             = len(buckets),
        n_samples             = match['n_samples'],
        calibration_tag_used  = used_tag,
    )