"""
quality_match.py
=================
Empirical match-quality lookup based on d_min_per_path_length buckets.

Complements conformal intervals: instead of a statistically calibrated
coverage guarantee, this answers "matches like this one historically had
this error" — bucketed per (metric, dtw_mode, retrieval_strategy, level,
k, search_modes, calibration_tag, config_stage).

Buckets are built offline by match_quality_builder.py into
prognosis.confidence_match_quality. This module only reads them.

Lookup strategy:
  1. Exact match on all key fields including config_stage
  2. Fall back to calibration_tag='all' if the requested tag has no buckets

config_hash is NOT used for lookup (audit only).

Cache:
  Bucket rows are cached in-process with a TTL of CACHE_TTL_SECONDS.
  After a match_quality_builder.py run, the cache expires automatically.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import asyncpg

logger = logging.getLogger(__name__)

_bucket_cache: Dict[Tuple, Tuple[List[dict], float]] = {}
CACHE_TTL_SECONDS = 300

_TIER_EXCELLENT = 'excellent'
_TIER_GOOD      = 'good'
_TIER_MODERATE  = 'moderate'
_TIER_POOR      = 'poor'


@dataclass
class MatchQuality:
    expected_error_mm:    float
    tier:                 str
    bucket:               int
    n_buckets:            int
    n_samples:            int
    calibration_tag_used: str


def _tier_for_bucket(bucket_error: float, best_error: float) -> str:
    if best_error <= 0:
        return _TIER_EXCELLENT
    ratio = bucket_error / best_error
    if ratio <= 1.2:
        return _TIER_EXCELLENT
    if ratio <= 2.0:
        return _TIER_GOOD
    if ratio <= 4.0:
        return _TIER_MODERATE
    return _TIER_POOR


def _make_search_modes_str(search_modes: Tuple[str, ...]) -> str:
    return ','.join(sorted(search_modes))


async def _fetch_buckets(
    conn:               asyncpg.Connection,
    metric:             str,
    dtw_mode:           str,
    retrieval_strategy: str,
    level:              str,
    k:                  int,
    search_modes_str:   str,
    calibration_tag:    str,
    config_stage:       int,
) -> List[dict]:
    cache_key = (metric, dtw_mode, retrieval_strategy, level, k,
                 search_modes_str, calibration_tag, config_stage)

    cached = _bucket_cache.get(cache_key)
    if cached is not None:
        rows, expiry = cached
        if time.monotonic() < expiry:
            return rows
        del _bucket_cache[cache_key]

    rows_raw = await conn.fetch("""
        SELECT bucket, d_min_lower, d_min_upper, mean_error, median_error, n_samples
        FROM prognosis.confidence_match_quality
        WHERE metric              = $1
          AND dtw_mode            = $2
          AND retrieval_strategy  = $3
          AND level               = $4
          AND config_k            = $5
          AND search_modes        = $6
          AND calibration_tag     = $7
          AND config_stage        = $8
        ORDER BY bucket
    """, metric, dtw_mode, retrieval_strategy, level, k,
        search_modes_str, calibration_tag, config_stage)

    rows = [dict(r) for r in rows_raw]
    _bucket_cache[cache_key] = (rows, time.monotonic() + CACHE_TTL_SECONDS)
    return rows


async def get_match_quality(
    conn:         asyncpg.Connection,
    d_min:        Optional[float],
    level:        str,
    retrieval_strategy: str             = 'decomposed',
    calibration_tag:    str             = 'all',
    metric:             str             = 'sidtw',
    dtw_mode:           str             = 'position',
    k:                  int             = 10,
    search_modes:       Tuple[str, ...] = ('joint', 'metadata', 'orientation', 'position', 'velocity'),
    config_stage:       int             = 2,
) -> Optional[MatchQuality]:
    """
    Look up the empirical match-quality tier for a given d_min.

    Falls back to calibration_tag='all' if no buckets exist for the requested tag.
    Returns None if no buckets found or d_min is None.

    config_stage: 1 = Stage 1 RRF, 2 = Stage 2 DTW.
    """
    if d_min is None:
        return None

    search_modes_str = _make_search_modes_str(search_modes)
    used_tag         = calibration_tag

    buckets = await _fetch_buckets(
        conn, metric, dtw_mode, retrieval_strategy, level,
        k, search_modes_str, calibration_tag, config_stage,
    )

    if not buckets and calibration_tag != 'all':
        buckets = await _fetch_buckets(
            conn, metric, dtw_mode, retrieval_strategy, level,
            k, search_modes_str, 'all', config_stage,
        )
        if buckets:
            used_tag = 'all'
            logger.warning(
                f"[MatchQuality] stage={config_stage} tag='{calibration_tag}' has no buckets — "
                f"fell back to tag='all' (level={level}, strategy={retrieval_strategy}). "
                f"Run: python match_quality_builder.py --tag {calibration_tag}"
            )

    if not buckets:
        return None

    match = None
    for b in buckets:
        if b['d_min_lower'] <= d_min <= b['d_min_upper']:
            match = b
            break
    if match is None:
        match = buckets[0] if d_min < buckets[0]['d_min_lower'] else buckets[-1]

    best_error = min(b['median_error'] for b in buckets)
    tier       = _tier_for_bucket(match['median_error'], best_error)

    return MatchQuality(
        expected_error_mm    = round(float(match['median_error']), 4),
        tier                 = tier,
        bucket               = match['bucket'],
        n_buckets            = len(buckets),
        n_samples            = match['n_samples'],
        calibration_tag_used = used_tag,
    )