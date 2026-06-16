"""
calibration_set_builder_v4.py
================================
Offline script to build conformal calibration and test sets for the
retrieval-based robot trajectory performance prediction framework.

Main changes vs. v1
-------------------
1. Uses `nonconformity_score` instead of `alpha` to avoid confusion with
   conformal error level alpha.
2. Stores and filters by a `config_hash`, including K, DTW mode, metric,
   search modes, distance normalization, sigma floor, and split settings.
3. Supports bundled calibration: one search_similar(target_id=traj_id) can build both direct and decomposed outputs.
4. Uses conservative split-conformal quantiles via rank ceil((n+1)*coverage).
5. Adds a sigma floor to avoid exploding scores when neighbor performance std
   is close to zero.
6. Stores raw and normalized DTW distances. The normalized distance is used for
   inverse-distance weighting and uncertainty features.
7. Implements deterministic trajectory-level calibration/test split.
8. `--full-rebuild` really deletes old rows for the active config hash.
9. Computes empirical coverage on a held-out test split.
10. Stores log_prediction_error for sigma-model training.
11. Creates a per-call MultiModalSearcher instance to avoid sharing mutable searcher state across concurrent tasks.
12. Supports direct trajectory calibration in addition to decomposed segment aggregation.
13. For --retrieval-strategy both, processes one trajectory bundle at a time so Direct and Decomposed reuse the same search_similar result.

Usage
-----
    python calibration_set_builder_v4.py --k 10 --batch 10 --limit 1000
    python calibration_set_builder_v4.py --full-rebuild
    python calibration_set_builder_v4.py --distance-normalization per_point --test-ratio 0.2

Requirements
------------
    pip install asyncpg numpy tqdm python-dotenv --break-system-packages
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

import asyncpg
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from utils.multimodal_framework.dtw_reranker import rerank
from utils.multimodal_framework.multi_modal_searcher import MultiModalSearcher
from utils.metadata_embeddings.trajectory_loader import TrajectoryLoader

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost/dbname',
)

# ── Constants ─────────────────────────────────────────────────────────────────
EPSILON = 1e-6
DEFAULT_SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']
ALLOWED_METRICS = {'sidtw', 'ed', 'qdtw', 'gd'}
ALLOWED_DTW_MODES = {'position', 'joint', 'orientation', 'velocity', 'metadata'}

DistanceNorm = Literal['raw', 'per_point', 'per_path_length']
SplitRole = Literal['calibration', 'test']
Level = Literal['segment', 'trajectory']
RetrievalStrategy = Literal['decomposed', 'direct']


@dataclass(frozen=True)
class CalibrationConfig:
    k: int
    dtw_mode: str
    metric: str
    search_modes: Tuple[str, ...]
    distance_normalization: DistanceNorm
    sigma_floor: float
    test_ratio: float
    split_seed: int
    retrieval_strategy: RetrievalStrategy = 'decomposed'
    prediction_level: str = 'segment_and_trajectory'
    sigma_source: str = 'neighbor_perf_std_with_floor'
    trajectory_sigma_strategy: str = 'weighted_mean_segment_sigma'
    weighting: str = 'inverse_normalized_dtw_distance'

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    def hash(self) -> str:
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()[:16]


# ═════════════════════════════════════════════════════════════════════════════
# Generic helpers
# ═════════════════════════════════════════════════════════════════════════════


def validate_metric(metric: str) -> str:
    if metric not in ALLOWED_METRICS:
        raise ValueError(f"Unsupported metric '{metric}'. Allowed: {sorted(ALLOWED_METRICS)}")
    return metric


def validate_dtw_mode(mode: str) -> str:
    if mode not in ALLOWED_DTW_MODES:
        raise ValueError(f"Unsupported dtw mode '{mode}'. Allowed: {sorted(ALLOWED_DTW_MODES)}")
    return mode


def stable_json_loads(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    # asyncpg may return a custom JSON wrapper in some setups
    return dict(value)


def seg_id_to_traj_id(seg_id: str) -> str:
    # Existing segment IDs follow the convention <traj_id>_<segment_number>.
    return seg_id.rsplit('_', 1)[0]


def sequence_len(seq: Any) -> int:
    try:
        return int(len(seq))
    except TypeError:
        return 0


def path_length(seq: Any) -> float:
    """Approximate Cartesian path length from the first up to 3 columns."""
    arr = np.asarray(seq, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2:
        return 0.0
    coords = arr[:, : min(3, arr.shape[1])]
    diffs = np.diff(coords, axis=0)
    return float(np.linalg.norm(diffs, axis=1).sum())


def normalize_dtw_distance(
    raw_distance: float,
    query_seq: Any,
    candidate_seq: Any,
    method: DistanceNorm,
    query_path_len: Optional[float] = None,
) -> float:
    raw = float(raw_distance)
    if method == 'raw':
        return raw

    if method == 'per_point':
        denom = max(sequence_len(query_seq), sequence_len(candidate_seq), 1)
        return raw / float(denom)

    if method == 'per_path_length':
        q_len = query_path_len if query_path_len is not None else path_length(query_seq)
        return raw / max(float(q_len), EPSILON)

    raise ValueError(f"Unknown distance normalization: {method}")


def split_role_for_traj(traj_id: str, test_ratio: float, split_seed: int) -> SplitRole:
    """Deterministic trajectory-level split; prevents segment leakage."""
    if test_ratio <= 0:
        return 'calibration'
    if test_ratio >= 1:
        return 'test'

    digest = hashlib.sha256(f'{split_seed}:{traj_id}'.encode('utf-8')).hexdigest()
    value = int(digest[:12], 16) / float(16**12 - 1)
    return 'test' if value < test_ratio else 'calibration'


# ═════════════════════════════════════════════════════════════════════════════
# DB helpers
# ═════════════════════════════════════════════════════════════════════════════


async def create_pool(url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        url,
        min_size=5,
        max_size=20,
        server_settings={'search_path': 'motion, public'},
    )


async def ensure_calibration_tables(conn: asyncpg.Connection) -> None:
    """Create calibration and quantile tables if they do not exist."""
    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS evaluation;

        CREATE TABLE IF NOT EXISTS evaluation.confidence_calibration_seg (
            seg_id                 TEXT        NOT NULL,
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed'
                                      CHECK (retrieval_strategy IN ('decomposed', 'direct')),

            -- LOO prediction
            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,

            -- Local residual scale estimate used for normalized conformal score
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            -- DTW-geometry and neighborhood features for future sigma-model training
            dtw_features           JSONB       NOT NULL,

            -- Metadata
            k_neighbors            INT         NOT NULL,
            neighbor_ids           TEXT[]      NOT NULL,
            query_length           INT,
            query_path_length      FLOAT,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Config snapshot
            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            config_k               INT         NOT NULL,
            config_dtw_mode        TEXT        NOT NULL,
            config_metric          TEXT        NOT NULL,

            PRIMARY KEY (seg_id, config_hash)
        );

        CREATE TABLE IF NOT EXISTS evaluation.confidence_calibration_traj (
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed'
                                      CHECK (retrieval_strategy IN ('decomposed', 'direct')),

            -- Aggregated trajectory-level prediction
            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            -- Aggregated segment/DTW features
            traj_features          JSONB       NOT NULL,
            segment_ids            TEXT[]      NOT NULL,
            n_segments             INT         NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Config snapshot
            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            config_k               INT         NOT NULL,
            config_dtw_mode        TEXT        NOT NULL,
            config_metric          TEXT        NOT NULL,

            PRIMARY KEY (traj_id, config_hash)
        );

        -- Backward-compatible schema migration for tables created by earlier v2 drafts.
        ALTER TABLE evaluation.confidence_calibration_seg
            ADD COLUMN IF NOT EXISTS log_prediction_error FLOAT;
        ALTER TABLE evaluation.confidence_calibration_traj
            ADD COLUMN IF NOT EXISTS log_prediction_error FLOAT;

        ALTER TABLE evaluation.confidence_calibration_seg
            ADD COLUMN IF NOT EXISTS retrieval_strategy TEXT DEFAULT 'decomposed';
        ALTER TABLE evaluation.confidence_calibration_traj
            ADD COLUMN IF NOT EXISTS retrieval_strategy TEXT DEFAULT 'decomposed';
        UPDATE evaluation.confidence_calibration_seg
        SET retrieval_strategy = 'decomposed'
        WHERE retrieval_strategy IS NULL;
        UPDATE evaluation.confidence_calibration_traj
        SET retrieval_strategy = 'decomposed'
        WHERE retrieval_strategy IS NULL;

        UPDATE evaluation.confidence_calibration_seg
        SET log_prediction_error = LN(prediction_error + 1e-6)
        WHERE log_prediction_error IS NULL;
        UPDATE evaluation.confidence_calibration_traj
        SET log_prediction_error = LN(prediction_error + 1e-6)
        WHERE log_prediction_error IS NULL;

        ALTER TABLE evaluation.confidence_calibration_seg
            ALTER COLUMN log_prediction_error SET NOT NULL;
        ALTER TABLE evaluation.confidence_calibration_traj
            ALTER COLUMN log_prediction_error SET NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_ccs_config_role
            ON evaluation.confidence_calibration_seg (config_hash, split_role);
        CREATE INDEX IF NOT EXISTS idx_ccs_traj_id
            ON evaluation.confidence_calibration_seg (traj_id);
        CREATE INDEX IF NOT EXISTS idx_ccs_score
            ON evaluation.confidence_calibration_seg (nonconformity_score);
        CREATE INDEX IF NOT EXISTS idx_ccs_features
            ON evaluation.confidence_calibration_seg USING gin (dtw_features);

        CREATE INDEX IF NOT EXISTS idx_cct_config_role
            ON evaluation.confidence_calibration_traj (config_hash, split_role);
        CREATE INDEX IF NOT EXISTS idx_cct_strategy
            ON evaluation.confidence_calibration_traj (retrieval_strategy, config_hash, split_role);
        CREATE INDEX IF NOT EXISTS idx_cct_score
            ON evaluation.confidence_calibration_traj (nonconformity_score);
        CREATE INDEX IF NOT EXISTS idx_cct_features
            ON evaluation.confidence_calibration_traj USING gin (traj_features);

        CREATE TABLE IF NOT EXISTS evaluation.confidence_quantiles (
            id                     SERIAL      PRIMARY KEY,
            level                  TEXT        NOT NULL CHECK (level IN ('segment', 'trajectory')),
            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed'
                                      CHECK (retrieval_strategy IN ('decomposed', 'direct')),
            dtw_mode               TEXT        NOT NULL,
            metric                 TEXT        NOT NULL,
            config_k               INT         NOT NULL,
            coverage               FLOAT       NOT NULL,
            quantile_value         FLOAT       NOT NULL,
            n_calibration          INT         NOT NULL,
            n_test                 INT,
            mae_calibration        FLOAT,
            mae_test               FLOAT,
            empirical_coverage     FLOAT,
            mean_interval_width    FLOAT,
            median_interval_width  FLOAT,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (level, config_hash, coverage)
        );

        ALTER TABLE evaluation.confidence_quantiles
            ADD COLUMN IF NOT EXISTS retrieval_strategy TEXT DEFAULT 'decomposed';
        UPDATE evaluation.confidence_quantiles
        SET retrieval_strategy = 'decomposed'
        WHERE retrieval_strategy IS NULL;
    """)
    logger.info("Calibration tables ready.")


async def delete_config_rows(conn: asyncpg.Connection, config_hash: str) -> None:
    await conn.execute(
        "DELETE FROM evaluation.confidence_quantiles WHERE config_hash = $1",
        config_hash,
    )
    await conn.execute(
        "DELETE FROM evaluation.confidence_calibration_traj WHERE config_hash = $1",
        config_hash,
    )
    await conn.execute(
        "DELETE FROM evaluation.confidence_calibration_seg WHERE config_hash = $1",
        config_hash,
    )
    logger.info(f"Deleted previous rows for config_hash={config_hash}")


async def get_all_seg_ids(
    conn: asyncpg.Connection,
    metric: str,
    max_trajectories: Optional[int] = None,
) -> List[Tuple[str, str, float]]:
    """
    Return (seg_id, traj_id, actual_mean_distance) for real segments.

    If max_trajectories is set, randomly sample that many trajectories first,
    then return all their segments. This avoids taking only the first N segments.
    """
    metric = validate_metric(metric)
    table_name = f"evaluation.{metric}_info"
    value_col = f"{metric}_average_distance"

    if max_trajectories:
        rows = await conn.fetch(f"""
            SELECT
                m.seg_id,
                m.traj_id,
                ei.{value_col} AS mean_distance
            FROM motion.traj_metadata m
            JOIN {table_name} ei ON m.seg_id = ei.seg_id
            WHERE m.seg_id != m.traj_id
              AND ei.{value_col} IS NOT NULL
              AND m.traj_id = ANY(
                  SELECT traj_id
                  FROM motion.traj_metadata
                  WHERE seg_id = traj_id
                  ORDER BY RANDOM()
                  LIMIT $1
              )
        """, max_trajectories)
    else:
        rows = await conn.fetch(f"""
            SELECT
                m.seg_id,
                m.traj_id,
                ei.{value_col} AS mean_distance
            FROM motion.traj_metadata m
            JOIN {table_name} ei ON m.seg_id = ei.seg_id
            WHERE m.seg_id != m.traj_id
              AND ei.{value_col} IS NOT NULL
        """)

    return [(r['seg_id'], r['traj_id'], float(r['mean_distance'])) for r in rows]


async def get_already_computed_segments(conn: asyncpg.Connection, config_hash: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT seg_id
        FROM evaluation.confidence_calibration_seg
        WHERE config_hash = $1
        """,
        config_hash,
    )
    return {r['seg_id'] for r in rows}


async def get_actual_trajectory_values(
    conn: asyncpg.Connection,
    traj_ids: Sequence[str],
    metric: str,
) -> Dict[str, float]:
    """Return trajectory-level actual values when available in evaluation.<metric>_info."""
    if not traj_ids:
        return {}

    metric = validate_metric(metric)
    table_name = f"evaluation.{metric}_info"
    value_col = f"{metric}_average_distance"

    rows = await conn.fetch(f"""
        SELECT
            m.traj_id,
            ei.{value_col} AS mean_distance
        FROM motion.traj_metadata m
        JOIN {table_name} ei ON m.seg_id = ei.seg_id
        WHERE m.seg_id = m.traj_id
          AND m.traj_id = ANY($1::text[])
          AND ei.{value_col} IS NOT NULL
    """, list(traj_ids))

    return {r['traj_id']: float(r['mean_distance']) for r in rows}


async def get_all_traj_ids(
    conn: asyncpg.Connection,
    metric: str,
    max_trajectories: Optional[int] = None,
) -> List[Tuple[str, float]]:
    """Return (traj_id, actual_mean_distance) for whole trajectories."""
    metric = validate_metric(metric)
    table_name = f"evaluation.{metric}_info"
    value_col = f"{metric}_average_distance"

    limit_sql = "ORDER BY RANDOM() LIMIT $1" if max_trajectories else "ORDER BY m.traj_id"
    args: Tuple[Any, ...] = (max_trajectories,) if max_trajectories else ()

    rows = await conn.fetch(f"""
        SELECT
            m.traj_id,
            ei.{value_col} AS mean_distance
        FROM motion.traj_metadata m
        JOIN {table_name} ei ON m.seg_id = ei.seg_id
        WHERE m.seg_id = m.traj_id
          AND ei.{value_col} IS NOT NULL
        {limit_sql}
    """, *args)

    return [(r['traj_id'], float(r['mean_distance'])) for r in rows]


async def get_all_segments_for_trajectories(
    conn: asyncpg.Connection,
    traj_ids: Sequence[str],
) -> Dict[str, List[str]]:
    """Return traj_id -> all segment IDs, used to avoid same-trajectory leakage."""
    if not traj_ids:
        return {}

    rows = await conn.fetch("""
        SELECT traj_id, seg_id
        FROM motion.traj_metadata
        WHERE traj_id = ANY($1::text[])
    """, list(traj_ids))

    out: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        out[r['traj_id']].append(r['seg_id'])
    return out




async def get_segment_actual_values_for_trajectories(
    conn: asyncpg.Connection,
    traj_ids: Sequence[str],
    metric: str,
) -> Dict[str, float]:
    """Return seg_id -> actual segment-level performance values."""
    if not traj_ids:
        return {}

    metric = validate_metric(metric)
    table_name = f"evaluation.{metric}_info"
    value_col = f"{metric}_average_distance"

    rows = await conn.fetch(f"""
        SELECT
            m.seg_id,
            ei.{value_col} AS mean_distance
        FROM motion.traj_metadata m
        JOIN {table_name} ei ON m.seg_id = ei.seg_id
        WHERE m.seg_id != m.traj_id
          AND m.traj_id = ANY($1::text[])
          AND ei.{value_col} IS NOT NULL
    """, list(traj_ids))

    return {r['seg_id']: float(r['mean_distance']) for r in rows}

async def get_already_computed_trajectories(conn: asyncpg.Connection, config_hash: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT traj_id
        FROM evaluation.confidence_calibration_traj
        WHERE config_hash = $1
        """,
        config_hash,
    )
    return {r['traj_id'] for r in rows}


def get_candidate_id(row: Dict[str, Any], level: Level) -> Optional[str]:
    """Best-effort candidate id extraction from MultiModalSearcher result rows."""
    keys = (
        ['traj_id', 'trajectory_id', 'id', 'seg_id']
        if level == 'trajectory'
        else ['seg_id', 'segment_id', 'id']
    )
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value)
    return None


def extract_results_from_search(search_result: Dict[str, Any], level: Level, target_id: str) -> List[Dict[str, Any]]:
    """
    Robustly extract trajectory/segment candidate rows from MultiModalSearcher output.

    The exact payload differs between framework versions, so we first look inside the
    expected subtree and then recursively collect lists named `results`.
    """
    if level == 'trajectory':
        root = search_result.get('trajectory_similarity', search_result)
    else:
        root = search_result.get('segment_similarity', search_result)

    collected: List[Dict[str, Any]] = []

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            if isinstance(obj.get('results'), list):
                collected.extend([x for x in obj['results'] if isinstance(x, dict)])
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for item in obj:
                # For segment results, prefer the group belonging to the target segment.
                if level == 'segment' and isinstance(item, dict):
                    target = item.get('target_segment') or item.get('target_id')
                    if target is not None and str(target) != str(target_id):
                        continue
                visit(item)

    visit(root)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for row in collected:
        cid = get_candidate_id(row, level)
        if cid is None or cid in seen:
            continue
        seen.add(cid)
        unique.append(row)
    return unique




def extract_segment_groups_from_search(
    search_result: Dict[str, Any],
    target_segment_ids: Sequence[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract target_segment -> candidate rows from the segment part of a trajectory search.

    MultiModalSearcher(target_id=<traj_id>) returns both whole-trajectory results and
    one segment-similarity group per query segment. This helper keeps that grouping so
    decomposed predictions can be built without calling search_similar again per segment.
    """
    target_set = {str(x) for x in target_segment_ids}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    root = search_result.get('segment_similarity', [])

    def add_group(target: Any, results: Any) -> None:
        if target is None or not isinstance(results, list):
            return
        target_s = str(target)
        if target_set and target_s not in target_set:
            return
        rows = [r for r in results if isinstance(r, dict)]
        if rows:
            # Deduplicate candidates while preserving rank order.
            seen: set[str] = set()
            unique: List[Dict[str, Any]] = []
            for row in rows:
                cid = get_candidate_id(row, 'segment')
                if cid is None or cid in seen:
                    continue
                seen.add(cid)
                unique.append(row)
            groups[target_s] = unique

    def visit(obj: Any, inherited_target: Any = None) -> None:
        if isinstance(obj, dict):
            target = obj.get('target_segment') or obj.get('target_id') or inherited_target

            # Common payload shape from the current framework.
            similar_segments = obj.get('similar_segments')
            if isinstance(similar_segments, dict):
                add_group(target, similar_segments.get('results'))

            # Fallback shapes.
            add_group(target, obj.get('results'))

            for value in obj.values():
                visit(value, target)
        elif isinstance(obj, list):
            for item in obj:
                visit(item, inherited_target)

    visit(root)
    return groups


def collect_candidate_traj_ids_from_search(search_result: Dict[str, Any]) -> List[str]:
    """Collect trajectory IDs needed for loading direct and decomposed candidates."""
    out: List[str] = []

    for row in extract_results_from_search(search_result, 'trajectory', target_id=''):
        cid = get_candidate_id(row, 'trajectory')
        if cid:
            out.append(seg_id_to_traj_id(cid) if '_' in cid else cid)

    segment_groups = extract_segment_groups_from_search(search_result, target_segment_ids=[])
    # If target_segment_ids is empty, the helper filters nothing only if we explicitly recurse below.
    if not segment_groups:
        # Manual fallback: collect all result rows under segment_similarity.
        def visit(obj: Any) -> None:
            if isinstance(obj, dict):
                if isinstance(obj.get('results'), list):
                    for row in obj['results']:
                        if isinstance(row, dict):
                            sid = get_candidate_id(row, 'segment')
                            if sid:
                                out.append(row.get('traj_id') or seg_id_to_traj_id(sid))
                for value in obj.values():
                    visit(value)
            elif isinstance(obj, list):
                for item in obj:
                    visit(item)
        visit(search_result.get('segment_similarity', []))
    else:
        for rows in segment_groups.values():
            for row in rows:
                sid = get_candidate_id(row, 'segment')
                if sid:
                    out.append(row.get('traj_id') or seg_id_to_traj_id(sid))

    return list(dict.fromkeys(str(x) for x in out if x))

def get_sequence_from_loaded_trajectory(data: Optional[Dict[str, Any]], entity_id: str) -> Optional[np.ndarray]:
    """Return whole-trajectory sequence from TrajectoryLoader output.

    Preferred: data['segments'][traj_id], because in this project whole trajectories
    are stored with seg_id == traj_id. Fallback: concatenate non-empty segments.
    """
    if not data:
        return None

    for key in ('trajectory', 'sequence', 'data', 'points'):
        value = data.get(key)
        if value is not None and sequence_len(value) > 0:
            return np.asarray(value, dtype=float)

    segments = data.get('segments') or {}
    if entity_id in segments and sequence_len(segments[entity_id]) > 0:
        return np.asarray(segments[entity_id], dtype=float)

    arrays: List[np.ndarray] = []
    for sid in sorted(segments.keys()):
        if sid == entity_id:
            continue
        arr = segments.get(sid)
        if arr is not None and sequence_len(arr) > 0:
            arrays.append(np.asarray(arr, dtype=float))

    if not arrays:
        return None
    return np.concatenate(arrays, axis=0)


def count_real_segments(data: Optional[Dict[str, Any]], traj_id: str) -> int:
    if not data:
        return 0
    segments = data.get('segments') or {}
    real = [sid for sid in segments.keys() if sid != traj_id]
    return len(real) if real else len(segments)


# ═════════════════════════════════════════════════════════════════════════════
# Segment-level core computation
# ═════════════════════════════════════════════════════════════════════════════


def compute_loo_prediction(
    neighbors: List[Dict[str, Any]],
    sigma_floor: float,
) -> Optional[Dict[str, Any]]:
    """
    Given enriched neighbor list, compute LOO prediction and DTW/neighborhood features.

    `dtw_distance` is expected to be the normalized DTW distance and is used for
    inverse-distance weighting. Raw distances are stored separately for diagnostics.
    """
    valid = [
        n for n in neighbors
        if n.get('dtw_distance') is not None
        and n.get('dtw_distance_raw') is not None
        and n.get('mean_distance') is not None
    ]

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])

    dtw_dists = np.array([n['dtw_distance'] for n in valid], dtype=float)
    dtw_raw = np.array([n['dtw_distance_raw'] for n in valid], dtype=float)
    perf_values = np.array([n['mean_distance'] for n in valid], dtype=float)
    cand_lengths = np.array([n.get('candidate_length', 0) for n in valid], dtype=float)
    cand_path_lengths = np.array([n.get('candidate_path_length', 0.0) for n in valid], dtype=float)
    ids = [n['seg_id'] for n in valid]

    # Inverse normalized-DTW weighted prediction.
    weights = 1.0 / (dtw_dists + EPSILON)
    p_hat = float(np.dot(weights, perf_values) / weights.sum())

    # sigma = neighbor performance std, protected by sigma_floor.
    perf_std_raw = float(perf_values.std())
    perf_mean = float(perf_values.mean())
    perf_cv = perf_std_raw / (perf_mean + EPSILON)
    sigma = max(perf_std_raw, sigma_floor)

    d_min = float(dtw_dists.min())
    d_mean = float(dtw_dists.mean())
    d_max = float(dtw_dists.max())
    d_std = float(dtw_dists.std())
    d_spread = d_max - d_min
    d_rel = d_spread / (d_max + EPSILON)
    d_cv = d_std / (d_mean + EPSILON)

    raw_d_min = float(dtw_raw.min())
    raw_d_mean = float(dtw_raw.mean())
    raw_d_max = float(dtw_raw.max())
    raw_d_spread = raw_d_max - raw_d_min

    # A simple density proxy: neighbors close to the best match.
    close_threshold = d_min * 1.25 + EPSILON
    num_close_neighbors = int(np.sum(dtw_dists <= close_threshold))

    # Gap between the first and second match. Higher can mean the best match is isolated.
    d_gap_2_1 = float(dtw_dists[1] - dtw_dists[0]) if len(dtw_dists) > 1 else 0.0

    weighted_perf_var = float(
        np.dot(weights, (perf_values - p_hat) ** 2) / weights.sum()
    )
    weighted_perf_std = math.sqrt(max(weighted_perf_var, 0.0))

    return {
        'p_hat': p_hat,
        'sigma': sigma,
        'ids': ids,
        'dtw_features': {
            # Normalized DTW distances used by the conformal layer
            'd_min': d_min,
            'd_mean': d_mean,
            'd_max': d_max,
            'd_std': d_std,
            'd_spread': d_spread,
            'd_rel': d_rel,
            'd_cv': d_cv,
            'd_gap_2_1': d_gap_2_1,
            'num_close_neighbors': num_close_neighbors,

            # Raw DTW distances for diagnostics/reproducibility
            'raw_d_min': raw_d_min,
            'raw_d_mean': raw_d_mean,
            'raw_d_max': raw_d_max,
            'raw_d_spread': raw_d_spread,

            # Neighbor performance distribution
            'perf_std_raw': perf_std_raw,
            'perf_std': sigma,
            'perf_cv': perf_cv,
            'perf_mean': perf_mean,
            'weighted_perf_std': weighted_perf_std,
            'perf_min': float(perf_values.min()),
            'perf_max': float(perf_values.max()),
            'perf_spread': float(perf_values.max() - perf_values.min()),

            # Candidate size diagnostics
            'candidate_length_mean': float(cand_lengths.mean()) if len(cand_lengths) else 0.0,
            'candidate_path_length_mean': float(cand_path_lengths.mean()) if len(cand_path_lengths) else 0.0,
        },
    }


async def process_segment(
    seg_id: str,
    traj_id: str,
    p_actual: float,
    split_role: SplitRole,
    pool: asyncpg.Pool,
    cfg: CalibrationConfig,
    exclude_ids: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Run LOO retrieval for one segment and compute its conformal calibration row."""
    try:
        # Stage 1: candidate retrieval. Leave-one-out excludes the query segment itself.
        # Create a per-call searcher instance instead of sharing one across concurrent tasks.
        # This avoids bugs if MultiModalSearcher keeps mutable state or stores a connection internally.
        searcher = MultiModalSearcher(pool)
        search_result = await searcher.search_similar(
            target_id=seg_id,
            modes=list(cfg.search_modes),
            limit=cfg.k,
            metric=cfg.metric,
            exclude_ids=list(exclude_ids or [seg_id]),
        )

        seg_results_raw: List[Dict[str, Any]] = []
        for group in search_result.get('segment_similarity', []):
            if group.get('target_segment') == seg_id:
                seg_results_raw = group.get('similar_segments', {}).get('results', [])
                break

        if not seg_results_raw:
            logger.debug(f"No Stage 1 results for {seg_id}, skipping.")
            return None

        # Stage 2: load query and candidate trajectories, then rerank by DTW.
        async with pool.acquire() as conn:
            loader = TrajectoryLoader(conn)

            all_traj_ids = {traj_id, seg_id_to_traj_id(seg_id)}
            for r in seg_results_raw:
                candidate_seg_id = r['seg_id']
                all_traj_ids.add(r.get('traj_id') or seg_id_to_traj_id(candidate_seg_id))

            seg_batch = await loader.load_trajectories_batch(
                list(all_traj_ids),
                cfg.dtw_mode,
            )

        query_traj_data = seg_batch.get(seg_id_to_traj_id(seg_id)) or seg_batch.get(traj_id)
        if query_traj_data is None:
            return None

        query_arr = query_traj_data['segments'].get(seg_id)
        if query_arr is None or sequence_len(query_arr) == 0:
            return None

        query_length = sequence_len(query_arr)
        query_path_len = path_length(query_arr)

        candidates_flat: Dict[str, np.ndarray] = {}
        candidate_meta: Dict[str, Dict[str, float]] = {}

        for r in seg_results_raw:
            cand_seg_id = r['seg_id']
            cand_traj_id = r.get('traj_id') or seg_id_to_traj_id(cand_seg_id)
            cand_data = seg_batch.get(cand_traj_id)
            if not cand_data:
                continue
            arr = cand_data['segments'].get(cand_seg_id)
            if arr is None or sequence_len(arr) == 0:
                continue
            candidates_flat[cand_seg_id] = arr
            candidate_meta[cand_seg_id] = {
                'candidate_length': float(sequence_len(arr)),
                'candidate_path_length': float(path_length(arr)),
            }

        if not candidates_flat:
            return None

        dtw_results = rerank(
            query_seq=query_arr,
            candidates=candidates_flat,
            limit=cfg.k,
            mode=cfg.dtw_mode,
        )

        dtw_lookup: Dict[str, float] = {}
        for row in dtw_results:
            row_id = row.get('id') or row.get('seg_id')
            if row_id is not None and row.get('dtw_distance') is not None:
                dtw_lookup[row_id] = float(row['dtw_distance'])

        enriched: List[Dict[str, Any]] = []
        for r in seg_results_raw:
            sid = r['seg_id']
            raw_dtw_dist = dtw_lookup.get(sid)
            features = r.get('features') or {}
            mean_dist = features.get('mean_distance')
            candidate_arr = candidates_flat.get(sid)

            if raw_dtw_dist is None or mean_dist is None or candidate_arr is None:
                continue

            normalized_dtw_dist = normalize_dtw_distance(
                raw_distance=raw_dtw_dist,
                query_seq=query_arr,
                candidate_seq=candidate_arr,
                method=cfg.distance_normalization,
                query_path_len=query_path_len,
            )

            enriched.append({
                'seg_id': sid,
                'dtw_distance': normalized_dtw_dist,
                'dtw_distance_raw': raw_dtw_dist,
                'mean_distance': float(mean_dist),
                **candidate_meta.get(sid, {}),
            })

        result = compute_loo_prediction(enriched, sigma_floor=cfg.sigma_floor)
        if result is None:
            logger.debug(f"Not enough enriched neighbors for {seg_id}")
            return None

        p_hat = result['p_hat']
        sigma = result['sigma']
        neighbor_ids = result['ids']
        dtw_features = result['dtw_features']

        dtw_features.update({
            'query_length': query_length,
            'query_path_length': query_path_len,
            'distance_normalization': cfg.distance_normalization,
        })

        prediction_error = abs(p_actual - p_hat)
        log_prediction_error = math.log(prediction_error + EPSILON)
        nonconformity_score = prediction_error / max(sigma, cfg.sigma_floor, EPSILON)

        return {
            'seg_id': seg_id,
            'traj_id': traj_id,
            'split_role': split_role,
            'retrieval_strategy': 'decomposed',
            'p_actual': p_actual,
            'p_predicted': p_hat,
            'prediction_error': prediction_error,
            'log_prediction_error': log_prediction_error,
            'sigma': sigma,
            'nonconformity_score': nonconformity_score,
            'dtw_features': json.dumps(dtw_features, sort_keys=True),
            'k_neighbors': len(enriched),
            'neighbor_ids': neighbor_ids,
            'query_length': query_length,
            'query_path_length': query_path_len,
            'config_hash': cfg.hash(),
            'config': cfg.to_json(),
            'config_k': cfg.k,
            'config_dtw_mode': cfg.dtw_mode,
            'config_metric': cfg.metric,
        }

    except Exception as e:
        logger.warning(f"Failed for {seg_id}: {e}")
        return None


async def insert_segment_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    await conn.executemany("""
        INSERT INTO evaluation.confidence_calibration_seg (
            seg_id, traj_id, split_role, retrieval_strategy,
            p_actual, p_predicted, prediction_error, log_prediction_error,
            sigma, nonconformity_score,
            dtw_features,
            k_neighbors, neighbor_ids,
            query_length, query_path_length,
            config_hash, config,
            config_k, config_dtw_mode, config_metric
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8,
            $9, $10,
            $11::jsonb,
            $12, $13,
            $14, $15,
            $16, $17::jsonb,
            $18, $19, $20
        )
        ON CONFLICT (seg_id, config_hash) DO UPDATE SET
            traj_id              = EXCLUDED.traj_id,
            split_role           = EXCLUDED.split_role,
            retrieval_strategy   = EXCLUDED.retrieval_strategy,
            p_actual             = EXCLUDED.p_actual,
            p_predicted          = EXCLUDED.p_predicted,
            prediction_error     = EXCLUDED.prediction_error,
            log_prediction_error = EXCLUDED.log_prediction_error,
            sigma                = EXCLUDED.sigma,
            nonconformity_score  = EXCLUDED.nonconformity_score,
            dtw_features         = EXCLUDED.dtw_features,
            k_neighbors          = EXCLUDED.k_neighbors,
            neighbor_ids         = EXCLUDED.neighbor_ids,
            query_length         = EXCLUDED.query_length,
            query_path_length    = EXCLUDED.query_path_length,
            config               = EXCLUDED.config,
            config_k             = EXCLUDED.config_k,
            config_dtw_mode      = EXCLUDED.config_dtw_mode,
            config_metric        = EXCLUDED.config_metric,
            computed_at          = NOW()
    """, [
        (
            r['seg_id'], r['traj_id'], r['split_role'], r['retrieval_strategy'],
            r['p_actual'], r['p_predicted'], r['prediction_error'], r['log_prediction_error'],
            r['sigma'], r['nonconformity_score'],
            r['dtw_features'],
            r['k_neighbors'], r['neighbor_ids'],
            r['query_length'], r['query_path_length'],
            r['config_hash'], r['config'],
            r['config_k'], r['config_dtw_mode'], r['config_metric'],
        )
        for r in batch
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Direct trajectory-level core computation
# ═════════════════════════════════════════════════════════════════════════════


async def process_trajectory_direct(
    traj_id: str,
    p_actual: float,
    split_role: SplitRole,
    pool: asyncpg.Pool,
    cfg: CalibrationConfig,
) -> Optional[Dict[str, Any]]:
    """Run LOO retrieval for one whole trajectory and compute a direct trajectory row."""
    try:
        searcher = MultiModalSearcher(pool)
        search_result = await searcher.search_similar(
            target_id=traj_id,
            modes=list(cfg.search_modes),
            limit=cfg.k,
            metric=cfg.metric,
            exclude_ids=[traj_id],
        )

        traj_results_raw = extract_results_from_search(search_result, 'trajectory', traj_id)
        if not traj_results_raw:
            logger.debug(f"No trajectory Stage 1 results for {traj_id}, skipping.")
            return None

        candidate_traj_ids: List[str] = []
        for row in traj_results_raw:
            cid = get_candidate_id(row, 'trajectory')
            if cid is not None and cid != traj_id:
                candidate_traj_ids.append(cid)
        candidate_traj_ids = list(dict.fromkeys(candidate_traj_ids))[: cfg.k]
        if not candidate_traj_ids:
            return None

        async with pool.acquire() as conn:
            loader = TrajectoryLoader(conn)
            all_traj_ids = [traj_id] + candidate_traj_ids
            batch = await loader.load_trajectories_batch(all_traj_ids, cfg.dtw_mode)
            actual_map = await get_actual_trajectory_values(conn, candidate_traj_ids, cfg.metric)

        query_data = batch.get(traj_id)
        query_arr = get_sequence_from_loaded_trajectory(query_data, traj_id)
        if query_arr is None or sequence_len(query_arr) == 0:
            return None

        query_length = sequence_len(query_arr)
        query_path_len = path_length(query_arr)
        n_segments = count_real_segments(query_data, traj_id)

        candidates_flat: Dict[str, np.ndarray] = {}
        candidate_meta: Dict[str, Dict[str, float]] = {}
        for cid in candidate_traj_ids:
            arr = get_sequence_from_loaded_trajectory(batch.get(cid), cid)
            if arr is None or sequence_len(arr) == 0:
                continue
            candidates_flat[cid] = arr
            candidate_meta[cid] = {
                'candidate_length': float(sequence_len(arr)),
                'candidate_path_length': float(path_length(arr)),
            }

        if not candidates_flat:
            return None

        dtw_results = rerank(
            query_seq=query_arr,
            candidates=candidates_flat,
            limit=cfg.k,
            mode=cfg.dtw_mode,
        )

        dtw_lookup: Dict[str, float] = {}
        for row in dtw_results:
            row_id = row.get('id') or row.get('traj_id') or row.get('seg_id')
            if row_id is not None and row.get('dtw_distance') is not None:
                dtw_lookup[str(row_id)] = float(row['dtw_distance'])

        enriched: List[Dict[str, Any]] = []
        for cid in candidate_traj_ids:
            raw_dtw_dist = dtw_lookup.get(cid)
            mean_dist = actual_map.get(cid)
            candidate_arr = candidates_flat.get(cid)
            if raw_dtw_dist is None or mean_dist is None or candidate_arr is None:
                continue

            normalized_dtw_dist = normalize_dtw_distance(
                raw_distance=raw_dtw_dist,
                query_seq=query_arr,
                candidate_seq=candidate_arr,
                method=cfg.distance_normalization,
                query_path_len=query_path_len,
            )
            enriched.append({
                'seg_id': cid,  # generic id field consumed by compute_loo_prediction
                'dtw_distance': normalized_dtw_dist,
                'dtw_distance_raw': raw_dtw_dist,
                'mean_distance': float(mean_dist),
                **candidate_meta.get(cid, {}),
            })

        result = compute_loo_prediction(enriched, sigma_floor=cfg.sigma_floor)
        if result is None:
            return None

        p_hat = result['p_hat']
        sigma = result['sigma']
        prediction_error = abs(p_actual - p_hat)
        log_prediction_error = math.log(prediction_error + EPSILON)
        nonconformity_score = prediction_error / max(sigma, cfg.sigma_floor, EPSILON)

        traj_features = result['dtw_features']
        traj_features.update({
            'n_segments': n_segments,
            'query_length': query_length,
            'query_path_length': query_path_len,
            'total_query_length': query_length,
            'total_query_path_length': query_path_len,
            'distance_normalization': cfg.distance_normalization,
            'retrieval_strategy': 'direct',
        })

        return {
            'traj_id': traj_id,
            'split_role': split_role,
            'retrieval_strategy': 'direct',
            'p_actual': p_actual,
            'p_predicted': p_hat,
            'prediction_error': prediction_error,
            'log_prediction_error': log_prediction_error,
            'sigma': sigma,
            'nonconformity_score': nonconformity_score,
            'traj_features': json.dumps(traj_features, sort_keys=True),
            'segment_ids': [],
            'n_segments': n_segments,
            'config_hash': cfg.hash(),
            'config': cfg.to_json(),
            'config_k': cfg.k,
            'config_dtw_mode': cfg.dtw_mode,
            'config_metric': cfg.metric,
        }

    except Exception as e:
        logger.warning(f"Direct trajectory failed for {traj_id}: {e}")
        return None


async def insert_trajectory_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    await conn.executemany("""
        INSERT INTO evaluation.confidence_calibration_traj (
            traj_id, split_role, retrieval_strategy,
            p_actual, p_predicted, prediction_error, log_prediction_error,
            sigma, nonconformity_score,
            traj_features, segment_ids, n_segments,
            config_hash, config,
            config_k, config_dtw_mode, config_metric
        ) VALUES (
            $1, $2, $3,
            $4, $5, $6, $7,
            $8, $9,
            $10::jsonb, $11, $12,
            $13, $14::jsonb,
            $15, $16, $17
        )
        ON CONFLICT (traj_id, config_hash) DO UPDATE SET
            split_role           = EXCLUDED.split_role,
            retrieval_strategy   = EXCLUDED.retrieval_strategy,
            p_actual             = EXCLUDED.p_actual,
            p_predicted          = EXCLUDED.p_predicted,
            prediction_error     = EXCLUDED.prediction_error,
            log_prediction_error = EXCLUDED.log_prediction_error,
            sigma                = EXCLUDED.sigma,
            nonconformity_score  = EXCLUDED.nonconformity_score,
            traj_features        = EXCLUDED.traj_features,
            segment_ids          = EXCLUDED.segment_ids,
            n_segments           = EXCLUDED.n_segments,
            config               = EXCLUDED.config,
            config_k             = EXCLUDED.config_k,
            config_dtw_mode      = EXCLUDED.config_dtw_mode,
            config_metric        = EXCLUDED.config_metric,
            computed_at          = NOW()
    """, [
        (
            r['traj_id'], r['split_role'], r['retrieval_strategy'],
            r['p_actual'], r['p_predicted'], r['prediction_error'], r['log_prediction_error'],
            r['sigma'], r['nonconformity_score'],
            r['traj_features'], r['segment_ids'], r['n_segments'],
            r['config_hash'], r['config'],
            r['config_k'], r['config_dtw_mode'], r['config_metric'],
        )
        for r in batch
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Trajectory-level aggregation
# ═════════════════════════════════════════════════════════════════════════════


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=float)
    values = np.asarray(values, dtype=float)
    denom = float(weights.sum())
    if denom <= EPSILON:
        return float(values.mean())
    return float(np.dot(weights, values) / denom)


def build_trajectory_row(
    traj_id: str,
    rows: List[asyncpg.Record],
    actual_traj_value: Optional[float],
    cfg: CalibrationConfig,
) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

    split_roles = {r['split_role'] for r in rows}
    if len(split_roles) != 1:
        raise ValueError(f"Trajectory {traj_id} has mixed split roles: {split_roles}")
    split_role = next(iter(split_roles))

    p_actual_seg = np.array([float(r['p_actual']) for r in rows], dtype=float)
    p_pred_seg = np.array([float(r['p_predicted']) for r in rows], dtype=float)
    sigma_seg = np.array([float(r['sigma']) for r in rows], dtype=float)
    q_lengths = np.array([float(r['query_length'] or 0) for r in rows], dtype=float)
    q_path_lengths = np.array([float(r['query_path_length'] or 0.0) for r in rows], dtype=float)

    # Prefer physical path length as aggregation weight. Fallback to sample length.
    weights = np.where(q_path_lengths > EPSILON, q_path_lengths, q_lengths)
    if float(weights.sum()) <= EPSILON:
        weights = np.ones(len(rows), dtype=float)

    p_predicted = weighted_mean(p_pred_seg, weights)
    p_actual = float(actual_traj_value) if actual_traj_value is not None else weighted_mean(p_actual_seg, weights)

    # Baseline trajectory sigma. Future sigma-models can use traj_features instead.
    sigma_weighted_mean = max(weighted_mean(sigma_seg, weights), cfg.sigma_floor)
    sigma = sigma_weighted_mean

    prediction_error = abs(p_actual - p_predicted)
    log_prediction_error = math.log(prediction_error + EPSILON)
    nonconformity_score = prediction_error / max(sigma, cfg.sigma_floor, EPSILON)

    parsed_features = [stable_json_loads(r['dtw_features']) for r in rows]

    def feature_array(name: str, default: float = 0.0) -> np.ndarray:
        return np.array([float(f.get(name, default) or default) for f in parsed_features], dtype=float)

    d_min = feature_array('d_min')
    d_mean = feature_array('d_mean')
    d_spread = feature_array('d_spread')
    perf_std = feature_array('perf_std')
    weighted_perf_std = feature_array('weighted_perf_std')
    num_close = feature_array('num_close_neighbors')
    d_gap = feature_array('d_gap_2_1')

    traj_features = {
        'n_segments': len(rows),
        'total_query_length': int(q_lengths.sum()),
        'total_query_path_length': float(q_path_lengths.sum()),
        'segment_prediction_std': float(p_pred_seg.std()),
        'segment_actual_std': float(p_actual_seg.std()),
        'segment_sigma_mean': float(sigma_seg.mean()),
        'segment_sigma_max': float(sigma_seg.max()),
        'segment_sigma_weighted_mean': sigma_weighted_mean,
        'd_min_mean': float(d_min.mean()),
        'd_min_max': float(d_min.max()),
        'd_mean_mean': float(d_mean.mean()),
        'd_spread_mean': float(d_spread.mean()),
        'd_spread_max': float(d_spread.max()),
        'perf_std_mean': float(perf_std.mean()),
        'perf_std_max': float(perf_std.max()),
        'weighted_perf_std_mean': float(weighted_perf_std.mean()),
        'weighted_perf_std_max': float(weighted_perf_std.max()),
        'num_close_neighbors_mean': float(num_close.mean()),
        'num_close_neighbors_min': int(num_close.min()) if len(num_close) else 0,
        'd_gap_2_1_mean': float(d_gap.mean()),
        'd_gap_2_1_max': float(d_gap.max()),
        # Useful as a risk proxy: one badly supported segment can make a whole trajectory risky.
        'worst_segment_d_min': float(d_min.max()),
        'worst_segment_perf_std': float(perf_std.max()),
        'retrieval_strategy': 'decomposed',
    }

    return {
        'traj_id': traj_id,
        'split_role': split_role,
        'retrieval_strategy': 'decomposed',
        'p_actual': p_actual,
        'p_predicted': p_predicted,
        'prediction_error': prediction_error,
        'log_prediction_error': log_prediction_error,
        'sigma': sigma,
        'nonconformity_score': nonconformity_score,
        'traj_features': json.dumps(traj_features, sort_keys=True),
        'segment_ids': [r['seg_id'] for r in rows],
        'n_segments': len(rows),
        'config_hash': cfg.hash(),
        'config': cfg.to_json(),
        'config_k': cfg.k,
        'config_dtw_mode': cfg.dtw_mode,
        'config_metric': cfg.metric,
    }


async def build_and_store_trajectory_rows(conn: asyncpg.Connection, cfg: CalibrationConfig) -> None:
    config_hash = cfg.hash()
    rows = await conn.fetch("""
        SELECT *
        FROM evaluation.confidence_calibration_seg
        WHERE config_hash = $1
    """, config_hash)

    grouped: Dict[str, List[asyncpg.Record]] = defaultdict(list)
    for r in rows:
        grouped[r['traj_id']].append(r)

    traj_ids = list(grouped.keys())
    actual_map = await get_actual_trajectory_values(conn, traj_ids, cfg.metric)

    out_rows: List[Dict[str, Any]] = []
    for traj_id, seg_rows in grouped.items():
        row = build_trajectory_row(
            traj_id=traj_id,
            rows=seg_rows,
            actual_traj_value=actual_map.get(traj_id),
            cfg=cfg,
        )
        if row is not None:
            out_rows.append(row)

    if not out_rows:
        logger.warning("No trajectory rows built.")
        return

    await insert_trajectory_batch(conn, out_rows)

    logger.info(f"Trajectory-level rows stored: {len(out_rows):,}")




# ═════════════════════════════════════════════════════════════════════════════
# Bundled trajectory processing: one search_similar call builds both strategies
# ═════════════════════════════════════════════════════════════════════════════


def build_segment_row_from_search_group(
    seg_id: str,
    traj_id: str,
    p_actual: float,
    split_role: SplitRole,
    seg_results_raw: List[Dict[str, Any]],
    loaded_batch: Dict[str, Any],
    cfg: CalibrationConfig,
) -> Optional[Dict[str, Any]]:
    """Build one decomposed segment calibration row from an existing search result group."""
    if not seg_results_raw:
        return None

    query_traj_data = loaded_batch.get(seg_id_to_traj_id(seg_id)) or loaded_batch.get(traj_id)
    if query_traj_data is None:
        return None

    query_arr = (query_traj_data.get('segments') or {}).get(seg_id)
    if query_arr is None or sequence_len(query_arr) == 0:
        return None

    query_length = sequence_len(query_arr)
    query_path_len = path_length(query_arr)

    candidates_flat: Dict[str, np.ndarray] = {}
    candidate_meta: Dict[str, Dict[str, float]] = {}

    for r in seg_results_raw:
        cand_seg_id = get_candidate_id(r, 'segment')
        if not cand_seg_id:
            continue
        cand_traj_id = r.get('traj_id') or seg_id_to_traj_id(cand_seg_id)
        cand_data = loaded_batch.get(cand_traj_id)
        if not cand_data:
            continue
        arr = (cand_data.get('segments') or {}).get(cand_seg_id)
        if arr is None or sequence_len(arr) == 0:
            continue
        candidates_flat[cand_seg_id] = arr
        candidate_meta[cand_seg_id] = {
            'candidate_length': float(sequence_len(arr)),
            'candidate_path_length': float(path_length(arr)),
        }

    if not candidates_flat:
        return None

    dtw_results = rerank(
        query_seq=query_arr,
        candidates=candidates_flat,
        limit=cfg.k,
        mode=cfg.dtw_mode,
    )

    dtw_lookup: Dict[str, float] = {}
    for row in dtw_results:
        row_id = row.get('id') or row.get('seg_id')
        if row_id is not None and row.get('dtw_distance') is not None:
            dtw_lookup[str(row_id)] = float(row['dtw_distance'])

    enriched: List[Dict[str, Any]] = []
    for r in seg_results_raw:
        sid = get_candidate_id(r, 'segment')
        if not sid:
            continue
        raw_dtw_dist = dtw_lookup.get(sid)
        features = r.get('features') or {}
        mean_dist = features.get('mean_distance')
        candidate_arr = candidates_flat.get(sid)

        if raw_dtw_dist is None or mean_dist is None or candidate_arr is None:
            continue

        normalized_dtw_dist = normalize_dtw_distance(
            raw_distance=raw_dtw_dist,
            query_seq=query_arr,
            candidate_seq=candidate_arr,
            method=cfg.distance_normalization,
            query_path_len=query_path_len,
        )

        enriched.append({
            'seg_id': sid,
            'dtw_distance': normalized_dtw_dist,
            'dtw_distance_raw': raw_dtw_dist,
            'mean_distance': float(mean_dist),
            **candidate_meta.get(sid, {}),
        })

    result = compute_loo_prediction(enriched, sigma_floor=cfg.sigma_floor)
    if result is None:
        return None

    p_hat = result['p_hat']
    sigma = result['sigma']
    prediction_error = abs(p_actual - p_hat)
    log_prediction_error = math.log(prediction_error + EPSILON)
    nonconformity_score = prediction_error / max(sigma, cfg.sigma_floor, EPSILON)

    dtw_features = result['dtw_features']
    dtw_features.update({
        'query_length': query_length,
        'query_path_length': query_path_len,
        'distance_normalization': cfg.distance_normalization,
        'retrieval_strategy': 'decomposed',
        'bundle_search': True,
    })

    return {
        'seg_id': seg_id,
        'traj_id': traj_id,
        'split_role': split_role,
        'retrieval_strategy': 'decomposed',
        'p_actual': p_actual,
        'p_predicted': p_hat,
        'prediction_error': prediction_error,
        'log_prediction_error': log_prediction_error,
        'sigma': sigma,
        'nonconformity_score': nonconformity_score,
        'dtw_features': json.dumps(dtw_features, sort_keys=True),
        'k_neighbors': len(enriched),
        'neighbor_ids': result['ids'],
        'query_length': query_length,
        'query_path_length': query_path_len,
        'config_hash': cfg.hash(),
        'config': cfg.to_json(),
        'config_k': cfg.k,
        'config_dtw_mode': cfg.dtw_mode,
        'config_metric': cfg.metric,
    }


def build_direct_trajectory_row_from_search_result(
    traj_id: str,
    p_actual: float,
    split_role: SplitRole,
    traj_results_raw: List[Dict[str, Any]],
    loaded_batch: Dict[str, Any],
    actual_traj_map: Dict[str, float],
    cfg: CalibrationConfig,
) -> Optional[Dict[str, Any]]:
    """Build direct whole-trajectory calibration row from an existing search result."""
    if not traj_results_raw:
        return None

    query_data = loaded_batch.get(traj_id)
    query_arr = get_sequence_from_loaded_trajectory(query_data, traj_id)
    if query_arr is None or sequence_len(query_arr) == 0:
        return None

    query_length = sequence_len(query_arr)
    query_path_len = path_length(query_arr)
    n_segments = count_real_segments(query_data, traj_id)

    candidate_traj_ids: List[str] = []
    for row in traj_results_raw:
        cid = get_candidate_id(row, 'trajectory')
        if cid is None:
            continue
        cid = seg_id_to_traj_id(cid) if '_' in cid else cid
        if cid != traj_id:
            candidate_traj_ids.append(cid)
    candidate_traj_ids = list(dict.fromkeys(candidate_traj_ids))[: cfg.k]
    if not candidate_traj_ids:
        return None

    candidates_flat: Dict[str, np.ndarray] = {}
    candidate_meta: Dict[str, Dict[str, float]] = {}
    for cid in candidate_traj_ids:
        arr = get_sequence_from_loaded_trajectory(loaded_batch.get(cid), cid)
        if arr is None or sequence_len(arr) == 0:
            continue
        candidates_flat[cid] = arr
        candidate_meta[cid] = {
            'candidate_length': float(sequence_len(arr)),
            'candidate_path_length': float(path_length(arr)),
        }

    if not candidates_flat:
        return None

    dtw_results = rerank(
        query_seq=query_arr,
        candidates=candidates_flat,
        limit=cfg.k,
        mode=cfg.dtw_mode,
    )
    dtw_lookup = {
        str(row.get('id') or row.get('traj_id')): float(row['dtw_distance'])
        for row in dtw_results
        if (row.get('id') or row.get('traj_id')) is not None and row.get('dtw_distance') is not None
    }

    enriched: List[Dict[str, Any]] = []
    for cid in candidate_traj_ids:
        raw_dtw_dist = dtw_lookup.get(cid)
        mean_dist = actual_traj_map.get(cid)
        candidate_arr = candidates_flat.get(cid)
        if raw_dtw_dist is None or mean_dist is None or candidate_arr is None:
            continue

        normalized_dtw_dist = normalize_dtw_distance(
            raw_distance=raw_dtw_dist,
            query_seq=query_arr,
            candidate_seq=candidate_arr,
            method=cfg.distance_normalization,
            query_path_len=query_path_len,
        )

        enriched.append({
            'seg_id': cid,  # generic ID field consumed by compute_loo_prediction
            'dtw_distance': normalized_dtw_dist,
            'dtw_distance_raw': raw_dtw_dist,
            'mean_distance': float(mean_dist),
            **candidate_meta.get(cid, {}),
        })

    result = compute_loo_prediction(enriched, sigma_floor=cfg.sigma_floor)
    if result is None:
        return None

    p_hat = result['p_hat']
    sigma = result['sigma']
    prediction_error = abs(p_actual - p_hat)
    log_prediction_error = math.log(prediction_error + EPSILON)
    nonconformity_score = prediction_error / max(sigma, cfg.sigma_floor, EPSILON)

    traj_features = result['dtw_features']
    traj_features.update({
        'n_segments': n_segments,
        'query_length': query_length,
        'query_path_length': query_path_len,
        'total_query_length': query_length,
        'total_query_path_length': query_path_len,
        'distance_normalization': cfg.distance_normalization,
        'retrieval_strategy': 'direct',
        'bundle_search': True,
    })

    return {
        'traj_id': traj_id,
        'split_role': split_role,
        'retrieval_strategy': 'direct',
        'p_actual': p_actual,
        'p_predicted': p_hat,
        'prediction_error': prediction_error,
        'log_prediction_error': log_prediction_error,
        'sigma': sigma,
        'nonconformity_score': nonconformity_score,
        'traj_features': json.dumps(traj_features, sort_keys=True),
        'segment_ids': [],
        'n_segments': n_segments,
        'config_hash': cfg.hash(),
        'config': cfg.to_json(),
        'config_k': cfg.k,
        'config_dtw_mode': cfg.dtw_mode,
        'config_metric': cfg.metric,
    }


async def process_trajectory_bundle(
    traj_id: str,
    p_actual_traj: float,
    split_role: SplitRole,
    pool: asyncpg.Pool,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
    own_segment_ids: Sequence[str],
    segment_actuals: Dict[str, float],
    build_decomposed_trajectory: bool,
) -> Optional[Dict[str, Any]]:
    """
    Run search_similar once for a whole trajectory and derive both outputs:
      - direct trajectory calibration from trajectory_similarity
      - decomposed segment rows + decomposed trajectory aggregation from segment_similarity
    """
    cfg_for_search = decomposed_cfg or direct_cfg
    if cfg_for_search is None:
        return None

    try:
        searcher = MultiModalSearcher(pool)
        exclude_ids = list(dict.fromkeys([traj_id, *own_segment_ids]))
        search_result = await searcher.search_similar(
            target_id=traj_id,
            modes=list(cfg_for_search.search_modes),
            limit=cfg_for_search.k,
            metric=cfg_for_search.metric,
            exclude_ids=exclude_ids,
        )

        target_segment_ids = [sid for sid in own_segment_ids if sid != traj_id]
        segment_groups = extract_segment_groups_from_search(search_result, target_segment_ids)
        traj_results_raw = extract_results_from_search(search_result, 'trajectory', traj_id)

        candidate_traj_ids = [traj_id]
        candidate_traj_ids.extend(collect_candidate_traj_ids_from_search(search_result))
        for rows in segment_groups.values():
            for row in rows:
                sid = get_candidate_id(row, 'segment')
                if sid:
                    candidate_traj_ids.append(row.get('traj_id') or seg_id_to_traj_id(sid))
        for row in traj_results_raw:
            cid = get_candidate_id(row, 'trajectory')
            if cid:
                candidate_traj_ids.append(seg_id_to_traj_id(cid) if '_' in cid else cid)
        candidate_traj_ids = list(dict.fromkeys(str(x) for x in candidate_traj_ids if x))

        async with pool.acquire() as conn:
            loader = TrajectoryLoader(conn)
            loaded_batch = await loader.load_trajectories_batch(candidate_traj_ids, cfg_for_search.dtw_mode)
            actual_traj_map = await get_actual_trajectory_values(
                conn,
                [tid for tid in candidate_traj_ids if tid != traj_id],
                cfg_for_search.metric,
            )

        segment_rows: List[Dict[str, Any]] = []
        decomposed_traj_row: Optional[Dict[str, Any]] = None
        direct_traj_row: Optional[Dict[str, Any]] = None

        if decomposed_cfg is not None:
            for seg_id, rows in segment_groups.items():
                p_actual_seg = segment_actuals.get(seg_id)
                if p_actual_seg is None:
                    continue
                seg_row = build_segment_row_from_search_group(
                    seg_id=seg_id,
                    traj_id=traj_id,
                    p_actual=p_actual_seg,
                    split_role=split_role,
                    seg_results_raw=rows,
                    loaded_batch=loaded_batch,
                    cfg=decomposed_cfg,
                )
                if seg_row is not None:
                    segment_rows.append(seg_row)

            if build_decomposed_trajectory and segment_rows:
                decomposed_traj_row = build_trajectory_row(
                    traj_id=traj_id,
                    rows=segment_rows,  # dicts support the same access pattern as asyncpg.Record here
                    actual_traj_value=p_actual_traj,
                    cfg=decomposed_cfg,
                )

        if direct_cfg is not None:
            direct_traj_row = build_direct_trajectory_row_from_search_result(
                traj_id=traj_id,
                p_actual=p_actual_traj,
                split_role=split_role,
                traj_results_raw=traj_results_raw,
                loaded_batch=loaded_batch,
                actual_traj_map=actual_traj_map,
                cfg=direct_cfg,
            )

        return {
            'segment_rows': segment_rows,
            'decomposed_traj_row': decomposed_traj_row,
            'direct_traj_row': direct_traj_row,
        }

    except Exception as e:
        logger.warning(f"Bundle processing failed for {traj_id}: {e}")
        return None


async def get_done_trajectory_ids_for_bundle(
    conn: asyncpg.Connection,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
    build_decomposed_trajectory: bool,
) -> set[str]:
    """Return traj_ids that are complete for the requested bundled outputs."""
    done_sets: List[set[str]] = []

    if decomposed_cfg is not None and build_decomposed_trajectory:
        done_sets.append(await get_already_computed_trajectories(conn, decomposed_cfg.hash()))

    if direct_cfg is not None:
        done_sets.append(await get_already_computed_trajectories(conn, direct_cfg.hash()))

    if not done_sets:
        return set()
    return set.intersection(*done_sets) if done_sets else set()


async def run_bundle_calibration(
    pool: asyncpg.Pool,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
    batch_size: int,
    resume: bool,
    max_trajectories: Optional[int],
    coverages: Sequence[float],
    build_decomposed_trajectory: bool,
) -> None:
    """Process trajectories once and reuse each search_result for Direct and Decomposed."""
    cfg_for_query = decomposed_cfg or direct_cfg
    if cfg_for_query is None:
        return

    async with pool.acquire() as conn:
        all_trajs = await get_all_traj_ids(conn, cfg_for_query.metric, max_trajectories=max_trajectories)
        traj_ids = [traj_id for traj_id, _ in all_trajs]
        traj_to_seg_ids = await get_all_segments_for_trajectories(conn, traj_ids)
        segment_actuals = await get_segment_actual_values_for_trajectories(conn, traj_ids, cfg_for_query.metric)
        already_done = await get_done_trajectory_ids_for_bundle(
            conn,
            decomposed_cfg=decomposed_cfg,
            direct_cfg=direct_cfg,
            build_decomposed_trajectory=build_decomposed_trajectory,
        ) if resume else set()

    logger.info(f"Total trajectories with performance data : {len(all_trajs):,}")
    logger.info(f"Already complete for requested outputs   : {len(already_done):,}")

    todo: List[Tuple[str, float, SplitRole]] = []
    for traj_id, p_actual in all_trajs:
        if traj_id in already_done:
            continue
        role = split_role_for_traj(traj_id, cfg_for_query.test_ratio, cfg_for_query.split_seed)
        todo.append((traj_id, p_actual, role))

    n_cal = sum(1 for _, _, role in todo if role == 'calibration')
    n_test = sum(1 for _, _, role in todo if role == 'test')
    logger.info(f"Trajectories to process                  : {len(todo):,}")
    logger.info(f"  calibration split                      : {n_cal:,}")
    logger.info(f"  test split                             : {n_test:,}")

    if todo:
        seg_buffer: List[Dict[str, Any]] = []
        traj_buffer: List[Dict[str, Any]] = []
        n_ok = 0
        n_fail = 0

        with tqdm(total=len(todo), unit='traj', desc='Calibrating trajectory bundles') as pbar:
            for batch_start in range(0, len(todo), batch_size):
                batch = todo[batch_start: batch_start + batch_size]
                tasks = [
                    process_trajectory_bundle(
                        traj_id=traj_id,
                        p_actual_traj=p_actual,
                        split_role=role,
                        pool=pool,
                        decomposed_cfg=decomposed_cfg,
                        direct_cfg=direct_cfg,
                        own_segment_ids=traj_to_seg_ids.get(traj_id, []),
                        segment_actuals=segment_actuals,
                        build_decomposed_trajectory=build_decomposed_trajectory,
                    )
                    for traj_id, p_actual, role in batch
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=False)

                for res in batch_results:
                    if res is None:
                        n_fail += 1
                        continue
                    seg_buffer.extend(res.get('segment_rows') or [])
                    for key in ('decomposed_traj_row', 'direct_traj_row'):
                        row = res.get(key)
                        if row is not None:
                            traj_buffer.append(row)
                    n_ok += 1

                async with pool.acquire() as conn:
                    if seg_buffer:
                        await insert_segment_batch(conn, seg_buffer)
                        seg_buffer.clear()
                    if traj_buffer:
                        await insert_trajectory_batch(conn, traj_buffer)
                        traj_buffer.clear()

                pbar.update(len(batch))
                pbar.set_postfix(ok=n_ok, fail=n_fail)

        logger.info(f"Bundle build done. ok={n_ok:,} failed/skipped={n_fail:,}")
    else:
        logger.info("No bundle rows to process — requested outputs are up to date.")

    async with pool.acquire() as conn:
        if decomposed_cfg is not None:
            await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'segment')
            if build_decomposed_trajectory:
                await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'trajectory')
            await print_correlation_hints(conn, decomposed_cfg)

        if direct_cfg is not None:
            await compute_and_store_quantiles(conn, direct_cfg, coverages, 'trajectory')

# ═════════════════════════════════════════════════════════════════════════════
# Quantiles and coverage evaluation
# ═════════════════════════════════════════════════════════════════════════════


def conformal_quantile(scores: Sequence[float], coverage: float) -> float:
    """
    Conservative split-conformal quantile.

    For desired coverage 1-alpha, use rank ceil((n+1)*(1-alpha)). Here the
    caller passes `coverage`, e.g. 0.90. Rank is clipped to n.
    """
    if not scores:
        raise ValueError("Cannot compute conformal quantile without scores.")
    if not (0.0 < coverage < 1.0):
        raise ValueError("coverage must be in (0, 1).")

    sorted_scores = sorted(float(s) for s in scores)
    n = len(sorted_scores)
    rank = min(n, math.ceil((n + 1) * coverage))
    return float(sorted_scores[rank - 1])


async def fetch_level_rows(
    conn: asyncpg.Connection,
    level: Level,
    config_hash: str,
    split_role: SplitRole,
) -> List[asyncpg.Record]:
    table = (
        'evaluation.confidence_calibration_seg'
        if level == 'segment'
        else 'evaluation.confidence_calibration_traj'
    )
    return await conn.fetch(f"""
        SELECT
            p_actual,
            p_predicted,
            prediction_error,
            log_prediction_error,
            sigma,
            nonconformity_score
        FROM {table}
        WHERE config_hash = $1
          AND split_role = $2
        ORDER BY nonconformity_score
    """, config_hash, split_role)


def coverage_stats(rows: Sequence[asyncpg.Record], q: float) -> Dict[str, Optional[float]]:
    if not rows:
        return {
            'n': 0,
            'mae': None,
            'empirical_coverage': None,
            'mean_interval_width': None,
            'median_interval_width': None,
        }

    p_actual = np.array([float(r['p_actual']) for r in rows], dtype=float)
    p_pred = np.array([float(r['p_predicted']) for r in rows], dtype=float)
    sigma = np.array([float(r['sigma']) for r in rows], dtype=float)
    err = np.array([float(r['prediction_error']) for r in rows], dtype=float)

    lower = np.maximum(0.0, p_pred - q * sigma)
    upper = p_pred + q * sigma
    covered = (p_actual >= lower) & (p_actual <= upper)
    widths = upper - lower

    return {
        'n': int(len(rows)),
        'mae': float(err.mean()),
        'empirical_coverage': float(covered.mean()),
        'mean_interval_width': float(widths.mean()),
        'median_interval_width': float(np.median(widths)),
    }


async def compute_and_store_quantiles(
    conn: asyncpg.Connection,
    cfg: CalibrationConfig,
    coverages: Sequence[float],
    level: Level,
) -> None:
    config_hash = cfg.hash()

    calibration_rows = await fetch_level_rows(conn, level, config_hash, 'calibration')
    test_rows = await fetch_level_rows(conn, level, config_hash, 'test')

    if not calibration_rows:
        logger.warning(f"No calibration rows found for level={level}, config_hash={config_hash}")
        return

    cal_scores = [float(r['nonconformity_score']) for r in calibration_rows]
    cal_mae = float(np.mean([float(r['prediction_error']) for r in calibration_rows]))

    logger.info("=" * 72)
    logger.info(f"{level.upper()} calibration summary  config_hash={config_hash}")
    logger.info(f"  n_calibration: {len(calibration_rows):,}")
    logger.info(f"  n_test       : {len(test_rows):,}")
    logger.info(f"  MAE cal      : {cal_mae:.4f} mm")

    for coverage in coverages:
        q = conformal_quantile(cal_scores, coverage)
        test_stats = coverage_stats(test_rows, q)

        await conn.execute("""
            INSERT INTO evaluation.confidence_quantiles (
                level, config_hash, config, retrieval_strategy,
                dtw_mode, metric, config_k,
                coverage, quantile_value,
                n_calibration, n_test,
                mae_calibration, mae_test,
                empirical_coverage,
                mean_interval_width,
                median_interval_width
            ) VALUES (
                $1, $2, $3::jsonb, $4,
                $5, $6, $7,
                $8, $9,
                $10, $11,
                $12, $13,
                $14,
                $15,
                $16
            )
            ON CONFLICT (level, config_hash, coverage) DO UPDATE SET
                config                 = EXCLUDED.config,
                retrieval_strategy     = EXCLUDED.retrieval_strategy,
                dtw_mode               = EXCLUDED.dtw_mode,
                metric                 = EXCLUDED.metric,
                config_k               = EXCLUDED.config_k,
                quantile_value         = EXCLUDED.quantile_value,
                n_calibration          = EXCLUDED.n_calibration,
                n_test                 = EXCLUDED.n_test,
                mae_calibration        = EXCLUDED.mae_calibration,
                mae_test               = EXCLUDED.mae_test,
                empirical_coverage     = EXCLUDED.empirical_coverage,
                mean_interval_width    = EXCLUDED.mean_interval_width,
                median_interval_width  = EXCLUDED.median_interval_width,
                computed_at            = NOW()
        """,
            level,
            config_hash,
            cfg.to_json(),
            cfg.retrieval_strategy,
            cfg.dtw_mode,
            cfg.metric,
            cfg.k,
            float(coverage),
            float(q),
            len(calibration_rows),
            int(test_stats['n'] or 0),
            cal_mae,
            test_stats['mae'],
            test_stats['empirical_coverage'],
            test_stats['mean_interval_width'],
            test_stats['median_interval_width'],
        )

        logger.info(
            f"  q{int(coverage * 100):02d}: {q:.4f} | "
            f"test coverage={test_stats['empirical_coverage']} | "
            f"mean width={test_stats['mean_interval_width']}"
        )

    logger.info("=" * 72)


async def print_correlation_hints(conn: asyncpg.Connection, cfg: CalibrationConfig) -> None:
    """Exploratory hints for future sigma-model features."""
    config_hash = cfg.hash()
    rows = await conn.fetch("""
        SELECT
            nonconformity_score,
            prediction_error,
            log_prediction_error,
            dtw_features
        FROM evaluation.confidence_calibration_seg
        WHERE config_hash = $1
          AND split_role = 'calibration'
    """, config_hash)

    if len(rows) < 3:
        return

    candidate_features = [
        'd_min', 'd_mean', 'd_spread', 'd_rel', 'd_cv', 'd_gap_2_1',
        'num_close_neighbors', 'perf_std', 'perf_std_raw', 'perf_cv',
        'weighted_perf_std', 'query_length', 'query_path_length',
    ]

    score = np.array([float(r['nonconformity_score']) for r in rows], dtype=float)
    abs_err = np.array([float(r['prediction_error']) for r in rows], dtype=float)
    log_err_values = []
    for r in rows:
        try:
            value = r['log_prediction_error']
        except (KeyError, IndexError):
            value = None
        log_err_values.append(
            float(value) if value is not None else math.log(float(r['prediction_error']) + EPSILON)
        )
    log_err = np.array(log_err_values, dtype=float)

    logger.info("=" * 72)
    logger.info("Correlation hints for future sigma-model features (segment calibration split)")
    logger.info("  Prefer predicting prediction_error or log(prediction_error+eps),")
    logger.info("  then recalibrate score = error / sigma_hat.")

    for target_name, target in [
        ('score', score),
        ('abs_error', abs_err),
        ('log_abs_error', log_err),
    ]:
        logger.info(f"  Target: {target_name}")
        for fname in candidate_features:
            values = []
            for r in rows:
                feats = stable_json_loads(r['dtw_features'])
                values.append(float(feats.get(fname, 0.0) or 0.0))
            arr = np.array(values, dtype=float)
            if np.std(arr) <= EPSILON or np.std(target) <= EPSILON:
                corr = float('nan')
            else:
                corr = float(np.corrcoef(arr, target)[0, 1])
            logger.info(f"    {fname:24s}: {corr:+.4f}")
    logger.info("=" * 72)


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════


async def run_decomposed_calibration(
    pool: asyncpg.Pool,
    cfg: CalibrationConfig,
    batch_size: int,
    resume: bool,
    max_trajectories: Optional[int],
    coverages: Sequence[float],
    build_trajectories: bool,
) -> None:
    async with pool.acquire() as conn:
        all_segments = await get_all_seg_ids(
            conn,
            cfg.metric,
            max_trajectories=max_trajectories,
        )
        already_done = await get_already_computed_segments(conn, cfg.hash()) if resume else set()
        traj_to_seg_ids = await get_all_segments_for_trajectories(
            conn,
            list({traj_id for _, traj_id, _ in all_segments}),
        )

    logger.info(f"Total segments with performance data : {len(all_segments):,}")
    logger.info(f"Already computed for config          : {len(already_done):,}")

    todo: List[Tuple[str, str, float, SplitRole]] = []
    for seg_id, traj_id, p_actual in all_segments:
        if seg_id in already_done:
            continue
        role = split_role_for_traj(traj_id, cfg.test_ratio, cfg.split_seed)
        todo.append((seg_id, traj_id, p_actual, role))

    n_cal = sum(1 for _, _, _, role in todo if role == 'calibration')
    n_test = sum(1 for _, _, _, role in todo if role == 'test')
    logger.info(f"Segments to process                  : {len(todo):,}")
    logger.info(f"  calibration split                  : {n_cal:,}")
    logger.info(f"  test split                         : {n_test:,}")

    if todo:
        results_buffer: List[Dict[str, Any]] = []
        n_ok = 0
        n_fail = 0

        with tqdm(total=len(todo), unit='seg', desc='Calibrating decomposed segments') as pbar:
            for batch_start in range(0, len(todo), batch_size):
                batch = todo[batch_start: batch_start + batch_size]

                tasks = []
                for seg_id, traj_id, p_actual, role in batch:
                    # Important: for trajectory-level decomposed calibration, exclude all
                    # segments from the same physical trajectory, not only the current segment.
                    # This prevents same-execution leakage and better matches online usage.
                    exclude_ids = traj_to_seg_ids.get(traj_id) or [seg_id]
                    tasks.append(process_segment(
                        seg_id=seg_id,
                        traj_id=traj_id,
                        p_actual=p_actual,
                        split_role=role,
                        pool=pool,
                        cfg=cfg,
                        exclude_ids=exclude_ids,
                    ))

                batch_results = await asyncio.gather(*tasks, return_exceptions=False)

                for res in batch_results:
                    if res is not None:
                        results_buffer.append(res)
                        n_ok += 1
                    else:
                        n_fail += 1

                if results_buffer:
                    async with pool.acquire() as conn:
                        await insert_segment_batch(conn, results_buffer)
                    results_buffer.clear()

                pbar.update(len(batch))
                pbar.set_postfix(ok=n_ok, fail=n_fail)

        logger.info(f"Segment build done. ok={n_ok:,} failed/skipped={n_fail:,}")
    else:
        logger.info("No segment rows to process — current decomposed config is up to date.")

    async with pool.acquire() as conn:
        if build_trajectories:
            await conn.execute(
                "DELETE FROM evaluation.confidence_calibration_traj WHERE config_hash = $1",
                cfg.hash(),
            )
            await build_and_store_trajectory_rows(conn, cfg)

        await compute_and_store_quantiles(conn, cfg, coverages, 'segment')
        if build_trajectories:
            await compute_and_store_quantiles(conn, cfg, coverages, 'trajectory')

        await print_correlation_hints(conn, cfg)


async def run_direct_calibration(
    pool: asyncpg.Pool,
    cfg: CalibrationConfig,
    batch_size: int,
    resume: bool,
    max_trajectories: Optional[int],
    coverages: Sequence[float],
) -> None:
    async with pool.acquire() as conn:
        all_trajs = await get_all_traj_ids(
            conn,
            cfg.metric,
            max_trajectories=max_trajectories,
        )
        already_done = await get_already_computed_trajectories(conn, cfg.hash()) if resume else set()

    logger.info(f"Total trajectories with performance data : {len(all_trajs):,}")
    logger.info(f"Already computed for config              : {len(already_done):,}")

    todo: List[Tuple[str, float, SplitRole]] = []
    for traj_id, p_actual in all_trajs:
        if traj_id in already_done:
            continue
        role = split_role_for_traj(traj_id, cfg.test_ratio, cfg.split_seed)
        todo.append((traj_id, p_actual, role))

    n_cal = sum(1 for _, _, role in todo if role == 'calibration')
    n_test = sum(1 for _, _, role in todo if role == 'test')
    logger.info(f"Trajectories to process                  : {len(todo):,}")
    logger.info(f"  calibration split                      : {n_cal:,}")
    logger.info(f"  test split                             : {n_test:,}")

    if todo:
        results_buffer: List[Dict[str, Any]] = []
        n_ok = 0
        n_fail = 0

        with tqdm(total=len(todo), unit='traj', desc='Calibrating direct trajectories') as pbar:
            for batch_start in range(0, len(todo), batch_size):
                batch = todo[batch_start: batch_start + batch_size]
                tasks = [
                    process_trajectory_direct(
                        traj_id=traj_id,
                        p_actual=p_actual,
                        split_role=role,
                        pool=pool,
                        cfg=cfg,
                    )
                    for traj_id, p_actual, role in batch
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=False)

                for res in batch_results:
                    if res is not None:
                        results_buffer.append(res)
                        n_ok += 1
                    else:
                        n_fail += 1

                if results_buffer:
                    async with pool.acquire() as conn:
                        await insert_trajectory_batch(conn, results_buffer)
                    results_buffer.clear()

                pbar.update(len(batch))
                pbar.set_postfix(ok=n_ok, fail=n_fail)

        logger.info(f"Direct trajectory build done. ok={n_ok:,} failed/skipped={n_fail:,}")
    else:
        logger.info("No direct trajectory rows to process — current config is up to date.")

    async with pool.acquire() as conn:
        await compute_and_store_quantiles(conn, cfg, coverages, 'trajectory')


async def main(
    cfg: CalibrationConfig,
    batch_size: int,
    resume: bool,
    full_rebuild: bool,
    max_trajectories: Optional[int],
    coverages: Sequence[float],
    build_trajectories: bool,
) -> None:
    logger.info("Starting conformal calibration build")
    logger.info(f"  retrieval_strategy : {cfg.retrieval_strategy}")
    logger.info(f"  config_hash        : {cfg.hash()}")
    logger.info(f"  config             : {cfg.to_json()}")
    logger.info(f"  batch              : {batch_size}")
    logger.info(f"  limit              : {max_trajectories or 'all trajectories'}")

    pool = await create_pool(DATABASE_URL)

    try:
        async with pool.acquire() as conn:
            await ensure_calibration_tables(conn)
            if full_rebuild:
                await delete_config_rows(conn, cfg.hash())

        if cfg.retrieval_strategy == 'decomposed':
            await run_decomposed_calibration(
                pool=pool,
                cfg=cfg,
                batch_size=batch_size,
                resume=resume,
                max_trajectories=max_trajectories,
                coverages=coverages,
                build_trajectories=build_trajectories,
            )
        elif cfg.retrieval_strategy == 'direct':
            await run_direct_calibration(
                pool=pool,
                cfg=cfg,
                batch_size=batch_size,
                resume=resume,
                max_trajectories=max_trajectories,
                coverages=coverages,
            )
        else:
            raise ValueError(f"Unknown retrieval_strategy={cfg.retrieval_strategy}")

        logger.info("Online usage:")
        logger.info("  q = SELECT quantile_value FROM evaluation.confidence_quantiles")
        logger.info("      WHERE level = 'trajectory' AND config_hash = <active_config> AND coverage = 0.90")
        logger.info("  interval = [max(0, p_hat - q * sigma), p_hat + q * sigma]")
        logger.info("  Later sigma-model: train on prediction_error/log-error, then recompute scores and q.")

    finally:
        await pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Build conformal prediction calibration/test sets for robot trajectory performance.'
    )
    parser.add_argument('--k', type=int, default=10, help='Number of LOO neighbors for Stage 2.')
    parser.add_argument('--batch', type=int, default=10, help='Concurrent segments per batch.')
    parser.add_argument('--limit', type=int, default=None, help='Max number of trajectories to sample.')
    parser.add_argument('--metric', type=str, default='sidtw', choices=sorted(ALLOWED_METRICS))
    parser.add_argument('--dtw-mode', type=str, default='position', choices=sorted(ALLOWED_DTW_MODES))
    parser.add_argument(
        '--search-modes',
        nargs='+',
        default=DEFAULT_SEARCH_MODES,
        choices=sorted(ALLOWED_DTW_MODES),
        help='Embedding modalities used in Stage 1.',
    )
    parser.add_argument(
        '--distance-normalization',
        type=str,
        default='per_point',
        choices=['raw', 'per_point', 'per_path_length'],
        help='How raw DTW distances are normalized before weighting/features.',
    )
    parser.add_argument(
        '--sigma-floor',
        type=float,
        default=0.005,
        help='Minimum sigma in mm to avoid exploding normalized scores.',
    )
    parser.add_argument(
        '--test-ratio',
        type=float,
        default=0.2,
        help='Held-out trajectory-level test split ratio for empirical coverage.',
    )
    parser.add_argument('--split-seed', type=int, default=42)
    parser.add_argument(
        '--coverage',
        type=float,
        nargs='+',
        default=[0.80, 0.90, 0.95],
        help='Nominal coverages for conformal intervals.',
    )
    parser.add_argument('--resume', action='store_true', default=True, help='Skip segments already computed.')
    parser.add_argument('--full-rebuild', action='store_true', default=False, help='Delete and recompute active config.')
    parser.add_argument(
        '--retrieval-strategy',
        type=str,
        default='both',
        choices=['decomposed', 'direct', 'both'],
        help='Calibration strategy: decomposed segment aggregation, direct whole-trajectory retrieval, or both.',
    )
    parser.add_argument(
        '--no-trajectory-level',
        action='store_true',
        default=False,
        help='Only build segment-level rows and quantiles.',
    )

    args = parser.parse_args()

    if args.k <= 1:
        raise SystemExit('--k must be > 1')
    if args.batch <= 0:
        raise SystemExit('--batch must be > 0')
    if not (0.0 <= args.test_ratio < 1.0):
        raise SystemExit('--test-ratio must be in [0, 1)')
    if args.sigma_floor < 0:
        raise SystemExit('--sigma-floor must be >= 0')
    if any(c <= 0.0 or c >= 1.0 for c in args.coverage):
        raise SystemExit('--coverage values must be in (0, 1)')

    base_config = CalibrationConfig(
        k=args.k,
        dtw_mode=validate_dtw_mode(args.dtw_mode),
        metric=validate_metric(args.metric),
        search_modes=tuple(args.search_modes),
        distance_normalization=args.distance_normalization,
        sigma_floor=float(args.sigma_floor),
        test_ratio=float(args.test_ratio),
        split_seed=int(args.split_seed),
        retrieval_strategy='decomposed',
    )

    use_resume = bool(args.resume and not args.full_rebuild)

    async def run_selected_strategies() -> None:
        if args.retrieval_strategy == 'both':
            decomposed_cfg = replace(base_config, retrieval_strategy='decomposed')
            direct_cfg = replace(base_config, retrieval_strategy='direct')

            logger.info("Starting bundled conformal calibration build")
            logger.info("  mode               : both (one search_similar per trajectory)")
            logger.info(f"  decomposed_hash    : {decomposed_cfg.hash()}")
            logger.info(f"  direct_hash        : {direct_cfg.hash()}")
            logger.info(f"  shared config      : {base_config.to_json()}")
            logger.info(f"  batch              : {args.batch}")
            logger.info(f"  limit              : {args.limit or 'all trajectories'}")

            pool = await create_pool(DATABASE_URL)
            try:
                async with pool.acquire() as conn:
                    await ensure_calibration_tables(conn)
                    if args.full_rebuild:
                        await delete_config_rows(conn, decomposed_cfg.hash())
                        await delete_config_rows(conn, direct_cfg.hash())

                await run_bundle_calibration(
                    pool=pool,
                    decomposed_cfg=decomposed_cfg,
                    direct_cfg=direct_cfg,
                    batch_size=args.batch,
                    resume=use_resume,
                    max_trajectories=args.limit,
                    coverages=args.coverage,
                    build_decomposed_trajectory=(not args.no_trajectory_level),
                )

                logger.info("Online usage:")
                logger.info("  decomposed q = SELECT quantile_value FROM evaluation.confidence_quantiles")
                logger.info("      WHERE level = 'trajectory' AND retrieval_strategy = 'decomposed' AND config_hash = <decomposed_hash> AND coverage = 0.90")
                logger.info("  direct q = SELECT quantile_value FROM evaluation.confidence_quantiles")
                logger.info("      WHERE level = 'trajectory' AND retrieval_strategy = 'direct' AND config_hash = <direct_hash> AND coverage = 0.90")
            finally:
                await pool.close()

        else:
            cfg = replace(base_config, retrieval_strategy=args.retrieval_strategy)
            await main(
                cfg=cfg,
                batch_size=args.batch,
                resume=use_resume,
                full_rebuild=args.full_rebuild,
                max_trajectories=args.limit,
                coverages=args.coverage,
                build_trajectories=(not args.no_trajectory_level),
            )

    asyncio.run(run_selected_strategies())
