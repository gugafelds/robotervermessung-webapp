"""
calibration_set_builder_v5.py
================================

Simplified conformal calibration builder.

Main idea:
    The online/API pipeline already computes:
      - Stage 1 retrieval
      - optional Stage 2 DTW reranking
      - prognosis p_hat / sigma

    Therefore this builder only:
      1. samples trajectories
      2. calls the same similarity pipeline with Stage 2 + prognosis
      3. stores p_actual, p_predicted, sigma, nonconformity_score
      4. computes conformal quantiles and empirical coverage

Important:
    This builder calibrates Stage-2 predictions only.
    Stage-1 prognosis is intentionally not conformal-calibrated.
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
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import asyncpg
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app'))

from utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline

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

EPSILON = 1e-6

DEFAULT_SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']

ALLOWED_METRICS = {'sidtw', 'qdtw'}
ALLOWED_DTW_MODES = {'position', 'joint'}

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
        raise ValueError(f"Unsupported DTW mode '{mode}'. Allowed: {sorted(ALLOWED_DTW_MODES)}")
    return mode


def split_role_for_traj(traj_id: str, test_ratio: float, split_seed: int) -> SplitRole:
    """Deterministic trajectory-level split; prevents segment leakage."""
    if test_ratio <= 0:
        return 'calibration'
    if test_ratio >= 1:
        return 'test'

    digest = hashlib.sha256(f'{split_seed}:{traj_id}'.encode('utf-8')).hexdigest()
    value = int(digest[:12], 16) / float(16**12 - 1)

    return 'test' if value < test_ratio else 'calibration'


def prediction_to_row_values(
    *,
    p_actual: float,
    prediction: Dict[str, Any],
    sigma_floor: float,
) -> Optional[Dict[str, float]]:
    p_hat = prediction.get('p_hat')
    sigma = prediction.get('sigma')

    if p_hat is None or sigma is None:
        return None

    p_hat = float(p_hat)
    sigma = max(float(sigma), sigma_floor, EPSILON)

    prediction_error = abs(float(p_actual) - p_hat)
    log_prediction_error = math.log(prediction_error + EPSILON)
    nonconformity_score = prediction_error / sigma

    return {
        'p_actual': float(p_actual),
        'p_predicted': p_hat,
        'prediction_error': prediction_error,
        'log_prediction_error': log_prediction_error,
        'sigma': sigma,
        'nonconformity_score': nonconformity_score,
    }


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
    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS evaluation;

        CREATE TABLE IF NOT EXISTS evaluation.confidence_calibration_seg (
            seg_id                 TEXT        NOT NULL,
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed'
                                      CHECK (retrieval_strategy IN ('decomposed', 'direct')),

            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,

            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            dtw_features           JSONB       NOT NULL,

            k_neighbors            INT         NOT NULL,
            neighbor_ids           TEXT[]      NOT NULL,
            query_length           INT,
            query_path_length      FLOAT,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

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

            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            traj_features          JSONB       NOT NULL,
            segment_ids            TEXT[]      NOT NULL,
            n_segments             INT         NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            config_k               INT         NOT NULL,
            config_dtw_mode        TEXT        NOT NULL,
            config_metric          TEXT        NOT NULL,

            PRIMARY KEY (traj_id, config_hash)
        );

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

        CREATE INDEX IF NOT EXISTS idx_ccs_config_role
            ON evaluation.confidence_calibration_seg (config_hash, split_role);

        CREATE INDEX IF NOT EXISTS idx_cct_config_role
            ON evaluation.confidence_calibration_traj (config_hash, split_role);

        CREATE INDEX IF NOT EXISTS idx_cq_config
            ON evaluation.confidence_quantiles (config_hash, level, coverage);
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


async def get_all_traj_ids(
    conn: asyncpg.Connection,
    metric: str,
    max_trajectories: Optional[int] = None,
) -> List[Tuple[str, float]]:
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


async def get_already_computed_trajectories(
    conn: asyncpg.Connection,
    config_hash: str,
) -> set[str]:
    rows = await conn.fetch("""
        SELECT traj_id
        FROM evaluation.confidence_calibration_traj
        WHERE config_hash = $1
    """, config_hash)

    return {r['traj_id'] for r in rows}


# ═════════════════════════════════════════════════════════════════════════════
# Row builders from API prognosis
# ═════════════════════════════════════════════════════════════════════════════

def build_segment_rows_from_prognosis(
    *,
    traj_id: str,
    split_role: SplitRole,
    prognosis: Dict[str, Any],
    segment_actuals: Dict[str, float],
    cfg: CalibrationConfig,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for seg_pred in prognosis.get('segments', []) or []:
        seg_id = seg_pred.get('seg_id')
        if not seg_id:
            continue

        p_actual = segment_actuals.get(seg_id)
        if p_actual is None:
            continue

        values = prediction_to_row_values(
            p_actual=p_actual,
            prediction=seg_pred,
            sigma_floor=cfg.sigma_floor,
        )
        if values is None:
            continue

        dtw_features = {
            'source': 'similarity_pipeline',
            'retrieval_strategy': 'decomposed',
            'stage': 'stage2_dtw',
            'query_length': seg_pred.get('query_n_points'),
            'query_path_length': seg_pred.get('query_path_length'),
            'n_neighbors': seg_pred.get('n_neighbors'),
            'neighbor_ids': seg_pred.get('neighbor_ids') or [],
            'distance_normalization': cfg.distance_normalization,
        }

        rows.append({
            'seg_id': seg_id,
            'traj_id': traj_id,
            'split_role': split_role,
            'retrieval_strategy': 'decomposed',

            **values,

            'dtw_features': json.dumps(dtw_features, sort_keys=True),
            'k_neighbors': int(seg_pred.get('n_neighbors') or 0),
            'neighbor_ids': list(seg_pred.get('neighbor_ids') or []),
            'query_length': seg_pred.get('query_n_points'),
            'query_path_length': seg_pred.get('query_path_length'),

            'config_hash': cfg.hash(),
            'config': cfg.to_json(),
            'config_k': cfg.k,
            'config_dtw_mode': cfg.dtw_mode,
            'config_metric': cfg.metric,
        })

    return rows


def build_trajectory_row_from_prediction(
    *,
    traj_id: str,
    split_role: SplitRole,
    p_actual: float,
    prediction: Optional[Dict[str, Any]],
    retrieval_strategy: RetrievalStrategy,
    cfg: CalibrationConfig,
    segment_ids: Optional[List[str]] = None,
    segment_rows: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if prediction is None:
        return None

    values = prediction_to_row_values(
        p_actual=p_actual,
        prediction=prediction,
        sigma_floor=cfg.sigma_floor,
    )
    if values is None:
        return None

    segment_ids = segment_ids or []
    segment_rows = segment_rows or []

    segment_neighbor_counts = [
        int(r.get('k_neighbors') or 0)
        for r in segment_rows
        if int(r.get('k_neighbors') or 0) > 0
    ]

    segment_neighbor_ids_by_segment = {
        str(r['seg_id']): list(r.get('neighbor_ids') or [])
        for r in segment_rows
        if r.get('seg_id') is not None
    }

    traj_features = {
    'source': 'similarity_pipeline',
    'retrieval_strategy': retrieval_strategy,
    'stage': 'stage2_dtw',
    'n_segments': int(prediction.get('n_segments') or len(segment_ids) or 0),
    'distance_normalization': cfg.distance_normalization,
    }

    if retrieval_strategy == 'direct':
        traj_features.update({
            'n_neighbors': prediction.get('n_neighbors'),
            'neighbor_ids': prediction.get('neighbor_ids') or [],
        })
    else:
        traj_features.update({
            'segment_neighbor_count_mean': (
                float(np.mean(segment_neighbor_counts))
                if segment_neighbor_counts else None
            ),
            'segment_neighbor_count_min': (
                int(min(segment_neighbor_counts))
                if segment_neighbor_counts else None
            ),
            'segment_neighbor_count_max': (
                int(max(segment_neighbor_counts))
                if segment_neighbor_counts else None
            ),
            'segment_neighbor_ids_by_segment': segment_neighbor_ids_by_segment,
        })

    return {
        'traj_id': traj_id,
        'split_role': split_role,
        'retrieval_strategy': retrieval_strategy,

        **values,

        'traj_features': json.dumps(traj_features, sort_keys=True),
        'segment_ids': segment_ids,
        'n_segments': int(prediction.get('n_segments') or len(segment_ids) or 0),

        'config_hash': cfg.hash(),
        'config': cfg.to_json(),
        'config_k': cfg.k,
        'config_dtw_mode': cfg.dtw_mode,
        'config_metric': cfg.metric,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Inserts
# ═════════════════════════════════════════════════════════════════════════════

async def insert_segment_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    if not batch:
        return

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


async def insert_trajectory_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    if not batch:
        return

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
# Pipeline processing
# ═════════════════════════════════════════════════════════════════════════════

async def process_trajectory_bundle(
    *,
    traj_id: str,
    p_actual_traj: float,
    split_role: SplitRole,
    pool: asyncpg.Pool,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
    own_segment_ids: Sequence[str],
    segment_actuals: Dict[str, float],
) -> Optional[Dict[str, Any]]:
    """
    One trajectory -> call the same online similarity pipeline.

    Calibration always uses Stage 2, because conformal intervals are defined
    only for DTW-refined predictions.
    """
    cfg_for_pipeline = decomposed_cfg or direct_cfg
    if cfg_for_pipeline is None:
        return None

    exclude_ids = list(dict.fromkeys([traj_id, *own_segment_ids]))

    try:
        async with pool.acquire() as conn:
            result = await run_similarity_pipeline(
                target_id=traj_id,
                pool=pool,
                conn=conn,

                modes=list(cfg_for_pipeline.search_modes),
                weights={
                    'joint': 1.0,
                    'position': 1.0,
                    'orientation': 1.0,
                    'velocity': 1.0,
                    'metadata': 1.0,
                },
                limit=cfg_for_pipeline.k,
                buffer_factor=5,
                prefilter_features=[],
                metric=cfg_for_pipeline.metric,

                exclude_ids=exclude_ids,

                stage2_active=True,
                dtw_mode=cfg_for_pipeline.dtw_mode,

                prognosis_active=True,
                conformal_active=False,
            )

        if result.get('error'):
            logger.debug(f"Pipeline error for {traj_id}: {result['error']}")
            return None

        prognosis = result.get('prognosis') or {}
        if not prognosis:
            return None

        segment_rows: List[Dict[str, Any]] = []
        decomposed_traj_row: Optional[Dict[str, Any]] = None
        direct_traj_row: Optional[Dict[str, Any]] = None

        if decomposed_cfg is not None:
            segment_rows = build_segment_rows_from_prognosis(
                traj_id=traj_id,
                split_role=split_role,
                prognosis=prognosis,
                segment_actuals=segment_actuals,
                cfg=decomposed_cfg,
            )

            decomposed_traj_row = build_trajectory_row_from_prediction(
                traj_id=traj_id,
                split_role=split_role,
                p_actual=p_actual_traj,
                prediction=prognosis.get('decomposed'),
                retrieval_strategy='decomposed',
                cfg=decomposed_cfg,
                segment_ids=[r['seg_id'] for r in segment_rows],
                segment_rows=segment_rows,
            )

        if direct_cfg is not None:
            direct_traj_row = build_trajectory_row_from_prediction(
                traj_id=traj_id,
                split_role=split_role,
                p_actual=p_actual_traj,
                prediction=prognosis.get('direct'),
                retrieval_strategy='direct',
                cfg=direct_cfg,
                segment_ids=[],
            )

        return {
            'segment_rows': segment_rows,
            'decomposed_traj_row': decomposed_traj_row,
            'direct_traj_row': direct_traj_row,
        }

    except Exception as e:
        logger.warning(f"Bundle processing failed for {traj_id}: {e}", exc_info=False)
        return None


async def get_done_trajectory_ids_for_bundle(
    conn: asyncpg.Connection,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
) -> set[str]:
    done_sets: List[set[str]] = []

    if decomposed_cfg is not None:
        done_sets.append(await get_already_computed_trajectories(conn, decomposed_cfg.hash()))

    if direct_cfg is not None:
        done_sets.append(await get_already_computed_trajectories(conn, direct_cfg.hash()))

    if not done_sets:
        return set()

    return set.intersection(*done_sets)


async def run_calibration(
    *,
    pool: asyncpg.Pool,
    decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
    batch_size: int,
    resume: bool,
    max_trajectories: Optional[int],
    coverages: Sequence[float],
) -> None:
    cfg_for_query = decomposed_cfg or direct_cfg
    if cfg_for_query is None:
        return

    async with pool.acquire() as conn:
        all_trajs = await get_all_traj_ids(
            conn,
            cfg_for_query.metric,
            max_trajectories=max_trajectories,
        )
        traj_ids = [traj_id for traj_id, _ in all_trajs]

        traj_to_seg_ids = await get_all_segments_for_trajectories(conn, traj_ids)
        segment_actuals = await get_segment_actual_values_for_trajectories(
            conn,
            traj_ids,
            cfg_for_query.metric,
        )

        already_done = await get_done_trajectory_ids_for_bundle(
            conn,
            decomposed_cfg=decomposed_cfg,
            direct_cfg=direct_cfg,
        ) if resume else set()

    logger.info(f"Total trajectories with performance data : {len(all_trajs):,}")
    logger.info(f"Already complete                         : {len(already_done):,}")

    todo: List[Tuple[str, float, SplitRole]] = []
    for traj_id, p_actual in all_trajs:
        if traj_id in already_done:
            continue

        role = split_role_for_traj(
            traj_id,
            cfg_for_query.test_ratio,
            cfg_for_query.split_seed,
        )
        todo.append((traj_id, p_actual, role))

    n_cal = sum(1 for _, _, role in todo if role == 'calibration')
    n_test = sum(1 for _, _, role in todo if role == 'test')

    logger.info(f"Trajectories to process                  : {len(todo):,}")
    logger.info(f"  calibration split                      : {n_cal:,}")
    logger.info(f"  test split                             : {n_test:,}")

    seg_buffer: List[Dict[str, Any]] = []
    traj_buffer: List[Dict[str, Any]] = []

    n_ok = 0
    n_fail = 0

    with tqdm(total=len(todo), unit='traj', desc='Calibrating via similarity pipeline') as pbar:
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

    logger.info(f"Calibration build done. ok={n_ok:,} failed/skipped={n_fail:,}")

    async with pool.acquire() as conn:
        if decomposed_cfg is not None:
            await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'segment')
            await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'trajectory')

        if direct_cfg is not None:
            await compute_and_store_quantiles(conn, direct_cfg, coverages, 'trajectory')


# ═════════════════════════════════════════════════════════════════════════════
# Quantiles and coverage
# ═════════════════════════════════════════════════════════════════════════════

def conformal_quantile(scores: Sequence[float], coverage: float) -> float:
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
    logger.info(f"  strategy     : {cfg.retrieval_strategy}")
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


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build conformal calibration/test sets using the shared similarity pipeline.'
    )

    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--batch', type=int, default=10)
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--metric', type=str, default='sidtw', choices=sorted(ALLOWED_METRICS))
    parser.add_argument('--dtw-mode', type=str, default='position', choices=sorted(ALLOWED_DTW_MODES))
    parser.add_argument(
        '--search-modes',
        nargs='+',
        default=DEFAULT_SEARCH_MODES,
        choices=['joint', 'position', 'orientation', 'velocity', 'metadata'],
    )
    parser.add_argument(
        '--distance-normalization',
        type=str,
        default='per_path_length',
        choices=['raw', 'per_point', 'per_path_length'],
    )
    parser.add_argument('--sigma-floor', type=float, default=0.005)
    parser.add_argument('--test-ratio', type=float, default=0.2)
    parser.add_argument('--split-seed', type=int, default=42)
    parser.add_argument('--coverage', type=float, nargs='+', default=[0.80, 0.90, 0.95])
    parser.add_argument('--resume', action='store_true', default=True)
    parser.add_argument('--full-rebuild', action='store_true', default=False)
    parser.add_argument(
        '--retrieval-strategy',
        type=str,
        default='both',
        choices=['decomposed', 'direct', 'both'],
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

    decomposed_cfg: Optional[CalibrationConfig] = None
    direct_cfg: Optional[CalibrationConfig] = None

    if args.retrieval_strategy in ('decomposed', 'both'):
        decomposed_cfg = replace(base_config, retrieval_strategy='decomposed')

    if args.retrieval_strategy in ('direct', 'both'):
        direct_cfg = replace(base_config, retrieval_strategy='direct')

    logger.info("Starting simplified conformal calibration build")
    if decomposed_cfg is not None:
        logger.info(f"  decomposed_hash: {decomposed_cfg.hash()}")
    if direct_cfg is not None:
        logger.info(f"  direct_hash    : {direct_cfg.hash()}")

    logger.info(f"  batch          : {args.batch}")
    logger.info(f"  limit          : {args.limit or 'all trajectories'}")
    logger.info(f"  config         : {base_config.to_json()}")

    pool = await create_pool(DATABASE_URL)

    try:
        async with pool.acquire() as conn:
            await ensure_calibration_tables(conn)

            if args.full_rebuild:
                if decomposed_cfg is not None:
                    await delete_config_rows(conn, decomposed_cfg.hash())
                if direct_cfg is not None:
                    await delete_config_rows(conn, direct_cfg.hash())

        use_resume = bool(args.resume and not args.full_rebuild)

        await run_calibration(
            pool=pool,
            decomposed_cfg=decomposed_cfg,
            direct_cfg=direct_cfg,
            batch_size=args.batch,
            resume=use_resume,
            max_trajectories=args.limit,
            coverages=args.coverage,
        )

        logger.info("Online usage:")
        logger.info("  interval = [max(0, p_hat - q * sigma), p_hat + q * sigma]")
        logger.info("  q is read from evaluation.confidence_quantiles using the active config_hash.")

    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())