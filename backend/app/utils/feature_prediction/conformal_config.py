"""
conformal_config.py
===================
Shared configuration for the conformal prediction pipeline.

Used by:
  - calibration_set_builder.py  (offline)
  - conformal_predictor.py      (online)
  - quality_match.py            (online)

Lookup key for quantiles / match-quality buckets
-------------------------------------------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag + config_stage

config_stage = 1  →  Stage 1 RRF  (dtw_mode = 'none', retrieval_strategy = 'stage1_rrf')
config_stage = 2  →  Stage 2 DTW  (dtw_mode = 'position'|'joint')

config_hash is stored for resume/deduplication — NOT used for DB lookup.
It is derived only from the lookup-key fields so Stage 1 and Stage 2
always produce different hashes even with identical k/metric/search_modes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Literal, Optional, Tuple

RetrievalStrategy = Literal['decomposed', 'direct', 'stage1_rrf']


def _search_modes_str(modes: Tuple[str, ...]) -> str:
    """Stable, order-independent serialization of search modes."""
    return ','.join(sorted(modes))


@dataclass(frozen=True)
class CalibrationConfig:
    """
    Immutable configuration for a calibration run.

    config_hash is derived from the lookup-key fields only (not tuning params),
    so it changes when any key field changes — including config_stage.
    DB lookups use explicit columns, not the hash.
    """

    # ── Lookup key fields (all affect config_hash) ────────────────────────
    k:                  int
    dtw_mode:           str             # 'position' | 'joint' | 'none' (Stage 1)
    metric:             str
    search_modes:       Tuple[str, ...]
    retrieval_strategy: RetrievalStrategy
    calibration_tag:    str = 'all'
    config_stage:       int = 2         # 1 = Stage 1 RRF, 2 = Stage 2 DTW

    # ── Tuning params (NOT in hash) ───────────────────────────────────────
    sigma_floor:        float = 0.005
    test_ratio:         float = 0.2
    split_seed:         int   = 3

    def hash(self) -> str:
        """
        Hash over lookup-key fields only — guarantees Stage 1 and Stage 2
        produce different hashes even with identical k/metric/search_modes.
        """
        key = (
            f"{self.metric}:{self.dtw_mode}:{self.retrieval_strategy}"
            f":{self.config_stage}:{self.k}"
            f":{self.search_modes_str()}:{self.calibration_tag}"
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def search_modes_str(self) -> str:
        return _search_modes_str(self.search_modes)

    def with_strategy(self, strategy: RetrievalStrategy) -> 'CalibrationConfig':
        if strategy == 'stage1_rrf':
            return replace(self, retrieval_strategy=strategy, dtw_mode='none', config_stage=1)
        return replace(self, retrieval_strategy=strategy)

    def with_tag(self, tag: str) -> 'CalibrationConfig':
        return replace(self, calibration_tag=tag)

    def with_stage(self, stage: int) -> 'CalibrationConfig':
        return replace(self, config_stage=stage)


# Default config for Stage 2 (DTW)
DEFAULT_CONFIG = CalibrationConfig(
    k                  = 10,
    dtw_mode           = 'position',
    metric             = 'sidtw',
    search_modes       = ('joint', 'metadata', 'orientation', 'position', 'velocity'),
    retrieval_strategy = 'decomposed',
    calibration_tag    = 'all',
    config_stage       = 2,
    sigma_floor        = 0.005,
    test_ratio         = 0.2,
    split_seed         = 3,
)

# Default config for Stage 1 (RRF)
DEFAULT_CONFIG_STAGE1 = CalibrationConfig(
    k                  = 10,
    dtw_mode           = 'none',
    metric             = 'sidtw',
    search_modes       = ('joint', 'metadata', 'orientation', 'position', 'velocity'),
    retrieval_strategy = 'stage1_rrf',
    calibration_tag    = 'all',
    config_stage       = 1,
    sigma_floor        = 0.005,
    test_ratio         = 0.2,
    split_seed         = 3,
)


def get_active_config(
    retrieval_strategy: RetrievalStrategy         = 'decomposed',
    calibration_tag:    str                       = 'all',
    k:                  Optional[int]             = None,
    search_modes:       Optional[Tuple[str, ...]] = None,
    dtw_mode:           Optional[str]             = None,
    metric:             Optional[str]             = None,
    config_stage:       Optional[int]             = None,
) -> CalibrationConfig:
    """
    Build a CalibrationConfig from the given parameters, filling in
    defaults from DEFAULT_CONFIG (Stage 2) or DEFAULT_CONFIG_STAGE1.
    """
    is_stage1 = (
        retrieval_strategy == 'stage1_rrf'
        or (config_stage is not None and config_stage == 1)
    )
    base = DEFAULT_CONFIG_STAGE1 if is_stage1 else DEFAULT_CONFIG

    cfg = base.with_strategy(retrieval_strategy).with_tag(calibration_tag)

    if config_stage is not None:
        cfg = cfg.with_stage(config_stage)
    if k is not None:
        cfg = replace(cfg, k=k)
    if search_modes is not None and len(search_modes) > 0:
        cfg = replace(cfg, search_modes=tuple(sorted(search_modes)))
    if dtw_mode is not None:
        cfg = replace(cfg, dtw_mode=dtw_mode)
    if metric is not None:
        cfg = replace(cfg, metric=metric)

    return cfg