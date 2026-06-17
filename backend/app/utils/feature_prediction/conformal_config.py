"""
conformal_config.py
===================
Shared configuration dataclass for the conformal prediction pipeline.

Used by BOTH:
  - calibration_set_builder_v3.py  (offline, builds calibration set)
  - conformal_predictor.py         (online, computes intervals)

This ensures the config_hash is identical in both places —
which is required for the online scorer to find the correct
quantile rows in evaluation.confidence_quantiles.

Usage
-----
    from utils.conformal_calibration.conformal_config import (
        CalibrationConfig,
        DEFAULT_CONFIG,
        get_active_config,
    )
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal, Tuple

# ── Types ─────────────────────────────────────────────────────────────────────

DistanceNorm      = Literal['raw', 'per_point', 'per_path_length']
RetrievalStrategy = Literal['decomposed', 'direct']


# ═════════════════════════════════════════════════════════════════════════════
# CalibrationConfig
# ═════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalibrationConfig:
    """
    Immutable configuration that uniquely identifies a calibration run.

    Every field that affects the nonconformity scores or quantiles is
    included so that config_hash = SHA256(to_json())[:16] is a reliable
    cache key. Changing ANY field produces a new hash and a separate set
    of rows in the DB.
    """

    # Retrieval
    k:                      int
    dtw_mode:               str
    metric:                 str
    search_modes:           Tuple[str, ...]
    distance_normalization: DistanceNorm
    retrieval_strategy:     RetrievalStrategy

    # σ computation
    sigma_floor:            float

    # Split
    test_ratio:             float
    split_seed:             int

    # Metadata — included in hash so changes are tracked
    prediction_level:           str = 'segment_and_trajectory'
    sigma_source:               str = 'neighbor_perf_std_with_floor'
    trajectory_sigma_strategy:  str = 'weighted_mean_segment_sigma'
    weighting:                  str = 'inverse_normalized_dtw_distance'

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_json(self) -> str:
        """Stable JSON string — used to compute the hash."""
        return json.dumps(asdict(self), sort_keys=True)

    def hash(self) -> str:
        """16-char hex prefix of SHA-256(to_json()).  Matches DB config_hash column."""
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()[:16]

    # ── Convenience ───────────────────────────────────────────────────────

    def with_strategy(self, strategy: RetrievalStrategy) -> 'CalibrationConfig':
        """Return a copy with a different retrieval_strategy (different hash)."""
        from dataclasses import replace
        return replace(self, retrieval_strategy=strategy)



DEFAULT_CONFIG = CalibrationConfig(
    k                      = 10,
    dtw_mode               = 'position',
    metric                 = 'sidtw',
    search_modes           = ('position', 'joint', 'orientation', 'velocity', 'metadata'),
    distance_normalization = 'per_path_length',
    retrieval_strategy     = 'decomposed',
    sigma_floor            = 0.005,
    test_ratio             = 0.2,
    split_seed             = 3,
)


def get_active_config(
    retrieval_strategy: RetrievalStrategy = 'decomposed',
) -> CalibrationConfig:
    """
    Return the active config for a given retrieval strategy.

    The online scorer calls this to get the config_hash it needs
    to query evaluation.confidence_quantiles.

    If you rebuild the calibration set with different parameters,
    update DEFAULT_CONFIG above — the hash will change automatically.
    """
    return DEFAULT_CONFIG.with_strategy(retrieval_strategy)