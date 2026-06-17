"""
conformal_config.py
===================
Shared configuration for the conformal prediction pipeline.

Used by:
  - calibration_set_builder.py  (offline)
  - conformal_predictor.py      (online)

Lookup key for quantiles
-------------------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag

config_hash is stored for audit only — NOT used for DB lookup.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Literal, Tuple

RetrievalStrategy = Literal['decomposed', 'direct']


def _search_modes_str(modes: Tuple[str, ...]) -> str:
    """Stable, order-independent serialization of search modes."""
    return ','.join(sorted(modes))


@dataclass(frozen=True)
class CalibrationConfig:
    """
    Immutable configuration for a calibration run.

    config_hash = SHA256(to_json())[:16] is stored for audit.
    DB lookups use explicit columns, not the hash.
    """

    # Lookup key fields
    k:                  int
    dtw_mode:           str
    metric:             str
    search_modes:       Tuple[str, ...]
    retrieval_strategy: RetrievalStrategy
    calibration_tag:    str = 'all'

    # Not in lookup key — tuning params stored in config JSONB only
    sigma_floor:        float = 0.005
    test_ratio:         float = 0.2
    split_seed:         int   = 3

    # Metadata
    prediction_level:          str = 'segment_and_trajectory'
    sigma_source:              str = 'neighbor_perf_std_with_floor'
    trajectory_sigma_strategy: str = 'weighted_mean_segment_sigma'
    weighting:                 str = 'inverse_raw_dtw_distance'

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    def hash(self) -> str:
        """Audit hash only — not used for DB lookup."""
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()[:16]

    def search_modes_str(self) -> str:
        return _search_modes_str(self.search_modes)

    def with_strategy(self, strategy: RetrievalStrategy) -> 'CalibrationConfig':
        return replace(self, retrieval_strategy=strategy)

    def with_tag(self, tag: str) -> 'CalibrationConfig':
        return replace(self, calibration_tag=tag)


DEFAULT_CONFIG = CalibrationConfig(
    k                  = 10,
    dtw_mode           = 'position',
    metric             = 'sidtw',
    search_modes       = ('position', 'joint', 'orientation', 'velocity', 'metadata'),
    retrieval_strategy = 'decomposed',
    calibration_tag    = 'all',
    sigma_floor        = 0.005,
    test_ratio         = 0.2,
    split_seed         = 3,
)


def get_active_config(
    retrieval_strategy: RetrievalStrategy = 'decomposed',
    calibration_tag:    str               = 'all',
) -> CalibrationConfig:
    """
    Return the active config for online use.
    Update DEFAULT_CONFIG when pipeline parameters change.
    """
    return DEFAULT_CONFIG.with_strategy(retrieval_strategy).with_tag(calibration_tag)