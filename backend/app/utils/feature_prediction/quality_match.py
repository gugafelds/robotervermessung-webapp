"""
quality_match.py
=================
Empirical match-quality lookup based on d_min_per_path_length buckets (Stage 2) or sigma buckets (Stage 1,
see match_quality_builder.build_buckets_for_level).

Complements conformal intervals: instead of a statistically calibrated
coverage guarantee, this answers "matches like this one historically had
this error" — bucketed per (metric, dtw_mode, retrieval_strategy, level,
k, search_modes, calibration_tag, config_stage).

Buckets are built offline by match_quality_builder.py into
prognosis.confidence_match_quality. This module only reads them.

Lookup strategy:
  1. Exact match on all key fields including config_stage
  2. No buckets for the tag: None (no fallback to 'all', Baustein 2, 13.11.2026)

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

from .conformal_config import CalibrationConfig

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


# Fixed upper bounds (mm) of the expected error per tier -- the same meaning for every config and tag, whatever
# the error distribution of its calibration rows looks like.
TIER_BOUNDS_MM = ((0.03, _TIER_EXCELLENT), (0.05, _TIER_GOOD), (0.08, _TIER_MODERATE))


def _tier_for_error(expected_error: float) -> str:
    return next((tier for bound, tier in TIER_BOUNDS_MM if expected_error <= bound), _TIER_POOR)


def _make_search_modes_str(search_modes: Tuple[str, ...]) -> str:
    return ','.join(sorted(search_modes))


async def _fetch_buckets(
    conn: asyncpg.Connection,
    cfg:  CalibrationConfig,
    level: str,
) -> List[dict]:
    sm  = cfg.search_modes_str()
    cache_key = (cfg.metric, cfg.dtw_mode, cfg.retrieval_strategy, level,
                 cfg.k, sm, cfg.calibration_tag, cfg.config_stage)

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
    """, cfg.metric, cfg.dtw_mode, cfg.retrieval_strategy, level,
        cfg.k, sm, cfg.calibration_tag, cfg.config_stage)

    rows = [dict(r) for r in rows_raw]
    _bucket_cache[cache_key] = (rows, time.monotonic() + CACHE_TTL_SECONDS)
    return rows


async def get_match_quality(
    conn:  asyncpg.Connection,
    d_min: Optional[float],
    level: str,
    cfg:   CalibrationConfig,
) -> Optional[MatchQuality]:
    """
    Look up the empirical match-quality tier for a given d_min.

    Returns None if the tag has no buckets (no fallback to 'all') or d_min is None.
    """
    if d_min is None:
        return None

    used_tag = cfg.calibration_tag
    buckets  = await _fetch_buckets(conn, cfg, level)

    if not buckets:  # no fallback to 'all' (Baustein 2, 13.11.2026)
        return None

    match = None
    for b in buckets:
        if b['d_min_lower'] <= d_min <= b['d_min_upper']:
            match = b
            break
    if match is None:
        match = buckets[0] if d_min < buckets[0]['d_min_lower'] else buckets[-1]

    tier = _tier_for_error(float(match['median_error']))

    return MatchQuality(
        expected_error_mm    = round(float(match['median_error']), 4),
        tier                 = tier,
        bucket               = match['bucket'],
        n_buckets            = len(buckets),
        n_samples            = match['n_samples'],
        calibration_tag_used = used_tag,
    )