"""
calibration_set_builder.py
===========================
Conformal calibration builder.

DB lookup key for confidence_quantiles
----------------------------------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag

calibration_tag allows separate calibration per DB subset (e.g. 'all', 'bandit_v1').
Online lookup falls back from specific tag to 'all' if no row found.

Usage
-----
  python calibration_set_builder.py --tag all
  python calibration_set_builder.py --tag bandit_v1 --include-tags bandit_v1 --full-rebuild
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
from collections import defaultdict
from dataclasses import replace
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import asyncpg
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app'))

from utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline
from utils.feature_prediction.conformal_config import (
    CalibrationConfig,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

DATABASE_URL      = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
EPSILON           = 1e-6
DEFAULT_SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']
ALLOWED_METRICS   = {'sidtw', 'qdtw'}
ALLOWED_DTW_MODES = {'position', 'joint'}

SplitRole         = Literal['calibration', 'test']
Level             = Literal['segment', 'trajectory']
RetrievalStrategy = Literal['decomposed', 'direct']


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
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
    import hashlib
    if test_ratio <= 0:
        return 'calibration'
    if test_ratio >= 1:
        return 'test'
    digest = hashlib.sha256(f'{split_seed}:{traj_id}'.encode()).hexdigest()
    value  = int(digest[:12], 16) / float(16**12 - 1)
    return 'test' if value < test_ratio else 'calibration'


def prediction_to_row_values(
    *, p_actual: float, prediction: Dict[str, Any], sigma_floor: float,
) -> Optional[Dict[str, float]]:
    p_hat = prediction.get('p_hat')
    sigma = prediction.get('sigma')
    if p_hat is None or sigma is None:
        return None
    p_hat = float(p_hat)
    sigma = max(float(sigma), sigma_floor, EPSILON)
    err   = abs(float(p_actual) - p_hat)
    return {
        'p_actual':             float(p_actual),
        'p_predicted':          p_hat,
        'prediction_error':     err,
        'log_prediction_error': math.log(err + EPSILON),
        'sigma':                sigma,
        'nonconformity_score':  err / sigma,
    }


# ═════════════════════════════════════════════════════════════════════════════
# DB schema
# ═════════════════════════════════════════════════════════════════════════════

async def ensure_calibration_tables(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS prognosis;

        CREATE TABLE IF NOT EXISTS prognosis.confidence_calibration_seg (
            seg_id                 TEXT        NOT NULL,
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed',
            calibration_tag        TEXT        NOT NULL DEFAULT 'all',

            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            d_min                  FLOAT,
            d_min_per_path_length  FLOAT,
            d_mean                 FLOAT,

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
            search_modes           TEXT        NOT NULL,

            PRIMARY KEY (seg_id, config_hash, calibration_tag)
        );

        CREATE TABLE IF NOT EXISTS prognosis.confidence_calibration_traj (
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed',
            calibration_tag        TEXT        NOT NULL DEFAULT 'all',

            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            log_prediction_error   FLOAT       NOT NULL,
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            d_min_per_path_length  FLOAT,

            traj_features          JSONB       NOT NULL,
            segment_ids            TEXT[]      NOT NULL,
            n_segments             INT         NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            config_k               INT         NOT NULL,
            config_dtw_mode        TEXT        NOT NULL,
            config_metric          TEXT        NOT NULL,
            search_modes           TEXT        NOT NULL,

            PRIMARY KEY (traj_id, config_hash, calibration_tag)
        );

        -- Quantiles table: lookup key = metric+dtw_mode+retrieval_strategy+level+k+search_modes+tag
        CREATE TABLE IF NOT EXISTS prognosis.confidence_quantiles (
            id                     SERIAL      PRIMARY KEY,
            level                  TEXT        NOT NULL CHECK (level IN ('segment', 'trajectory')),

            -- Lookup key columns
            metric                 TEXT        NOT NULL,
            dtw_mode               TEXT        NOT NULL,
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed',
            config_k               INT         NOT NULL,
            search_modes           TEXT        NOT NULL,
            calibration_tag        TEXT        NOT NULL DEFAULT 'all',
            coverage               FLOAT       NOT NULL,

            -- Result
            quantile_value         FLOAT       NOT NULL,
            n_calibration          INT         NOT NULL,
            n_test                 INT,
            mae_calibration        FLOAT,
            mae_test               FLOAT,
            empirical_coverage     FLOAT,
            mean_interval_width    FLOAT,
            median_interval_width  FLOAT,

            -- Audit only
            config_hash            TEXT        NOT NULL,
            config                 JSONB       NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (metric, dtw_mode, retrieval_strategy, level,
                    config_k, search_modes, calibration_tag, coverage)
        );

        CREATE INDEX IF NOT EXISTS idx_ccs_config_tag
            ON prognosis.confidence_calibration_seg (config_hash, calibration_tag, split_role);
        CREATE INDEX IF NOT EXISTS idx_cct_config_tag
            ON prognosis.confidence_calibration_traj (config_hash, calibration_tag, split_role);
        CREATE INDEX IF NOT EXISTS idx_cq_lookup
            ON prognosis.confidence_quantiles
            (metric, dtw_mode, retrieval_strategy, level, config_k, search_modes, calibration_tag, coverage);
    """)

    # Migrations for existing tables
    await conn.execute("""
        ALTER TABLE prognosis.confidence_calibration_seg
            ADD COLUMN IF NOT EXISTS calibration_tag   TEXT NOT NULL DEFAULT 'all',
            ADD COLUMN IF NOT EXISTS search_modes      TEXT,
            ADD COLUMN IF NOT EXISTS d_min             FLOAT,
            ADD COLUMN IF NOT EXISTS d_min_per_path_length FLOAT,
            ADD COLUMN IF NOT EXISTS d_mean            FLOAT;

        ALTER TABLE prognosis.confidence_calibration_traj
            ADD COLUMN IF NOT EXISTS calibration_tag   TEXT NOT NULL DEFAULT 'all',
            ADD COLUMN IF NOT EXISTS search_modes      TEXT,
            ADD COLUMN IF NOT EXISTS d_min_per_path_length FLOAT;

        ALTER TABLE prognosis.confidence_quantiles
            ADD COLUMN IF NOT EXISTS search_modes      TEXT,
            ADD COLUMN IF NOT EXISTS calibration_tag   TEXT NOT NULL DEFAULT 'all';
    """)

    logger.info("Calibration tables ready.")


async def delete_config_rows(
    conn: asyncpg.Connection, config_hash: str, calibration_tag: str,
) -> None:
    await conn.execute(
        "DELETE FROM prognosis.confidence_quantiles WHERE config_hash=$1 AND calibration_tag=$2",
        config_hash, calibration_tag,
    )
    await conn.execute(
        "DELETE FROM prognosis.confidence_calibration_traj WHERE config_hash=$1 AND calibration_tag=$2",
        config_hash, calibration_tag,
    )
    await conn.execute(
        "DELETE FROM prognosis.confidence_calibration_seg WHERE config_hash=$1 AND calibration_tag=$2",
        config_hash, calibration_tag,
    )
    logger.info(f"Deleted rows for config_hash={config_hash} tag={calibration_tag}")


# ═════════════════════════════════════════════════════════════════════════════
# DB query helpers
# ═════════════════════════════════════════════════════════════════════════════

async def create_pool(url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        url, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )


async def get_all_traj_ids(
    conn: asyncpg.Connection, metric: str,
    max_trajectories: Optional[int] = None,
    include_tags: Optional[List[str]] = None,
) -> List[Tuple[str, float]]:
    metric     = validate_metric(metric)
    table_name = f"prognosis.{metric}_info"
    value_col  = f"{metric}_average_distance"

    tag_join  = ""
    tag_where = ""
    args: List[Any] = []

    if include_tags:
        tag_join  = "JOIN motion.traj_info tt ON m.traj_id = tt.traj_id"
        tag_where = f"AND tt.tag = ANY(${len(args)+1}::text[])"
        args.append(include_tags)

    limit_sql = ""
    if max_trajectories:
        limit_sql = f"ORDER BY RANDOM() LIMIT ${len(args)+1}"
        args.append(max_trajectories)
    else:
        limit_sql = "ORDER BY m.traj_id"

    rows = await conn.fetch(f"""
        SELECT m.traj_id, ei.{value_col} AS mean_distance
        FROM motion.traj_metadata m
        JOIN {table_name} ei ON m.seg_id = ei.seg_id
        {tag_join}
        WHERE m.seg_id = m.traj_id
          AND ei.{value_col} IS NOT NULL
          {tag_where}
        GROUP BY m.traj_id, ei.{value_col}
        {limit_sql}
    """, *args)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows]


async def get_all_segments_for_trajectories(
    conn: asyncpg.Connection, traj_ids: List[str],
) -> Dict[str, List[str]]:
    rows = await conn.fetch("""
        SELECT traj_id, seg_id FROM motion.traj_metadata
        WHERE traj_id = ANY($1::text[]) AND seg_id != traj_id
    """, traj_ids)
    result: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        result[r['traj_id']].append(r['seg_id'])
    return dict(result)


async def get_segment_actual_values_for_trajectories(
    conn: asyncpg.Connection, traj_ids: List[str], metric: str,
) -> Dict[str, float]:
    metric     = validate_metric(metric)
    table_name = f"prognosis.{metric}_info"
    value_col  = f"{metric}_average_distance"
    rows = await conn.fetch(f"""
        SELECT m.seg_id, ei.{value_col} AS mean_distance
        FROM motion.traj_metadata m
        JOIN {table_name} ei ON m.seg_id = ei.seg_id
        WHERE m.seg_id != m.traj_id
          AND m.traj_id = ANY($1::text[])
          AND ei.{value_col} IS NOT NULL
    """, list(traj_ids))
    return {r['seg_id']: float(r['mean_distance']) for r in rows}


async def get_already_computed_trajectories(
    conn: asyncpg.Connection, config_hash: str, calibration_tag: str,
) -> set:
    rows = await conn.fetch("""
        SELECT traj_id FROM prognosis.confidence_calibration_traj
        WHERE config_hash = $1 AND calibration_tag = $2
    """, config_hash, calibration_tag)
    return {r['traj_id'] for r in rows}


# ═════════════════════════════════════════════════════════════════════════════
# Row builders
# ═════════════════════════════════════════════════════════════════════════════

def build_segment_rows_from_prognosis(
    *, traj_id: str, split_role: SplitRole, prognosis: Dict[str, Any],
    segment_actuals: Dict[str, float], cfg: CalibrationConfig,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for seg_pred in prognosis.get('segments', []) or []:
        seg_id   = seg_pred.get('seg_id')
        p_actual = segment_actuals.get(seg_id) if seg_id else None
        if not seg_id or p_actual is None:
            continue
        values = prediction_to_row_values(
            p_actual=p_actual, prediction=seg_pred, sigma_floor=cfg.sigma_floor,
        )
        if values is None:
            continue

        d_min                 = seg_pred.get('d_min')
        d_min_per_path_length = seg_pred.get('d_min_per_path_length')
        d_mean                = seg_pred.get('d_mean')

        dtw_features = {
            'source':                'similarity_pipeline',
            'retrieval_strategy':    'decomposed',
            'stage':                 'stage2_dtw',
            'query_path_length':     seg_pred.get('query_path_length'),
            'n_neighbors':           seg_pred.get('n_neighbors'),
            'neighbor_ids':          seg_pred.get('neighbor_ids') or [],
            'd_min':                 d_min,
            'd_min_per_path_length': d_min_per_path_length,
            'd_mean':                d_mean,
        }

        rows.append({
            'seg_id':                seg_id,
            'traj_id':               traj_id,
            'split_role':            split_role,
            'retrieval_strategy':    'decomposed',
            'calibration_tag':       cfg.calibration_tag,
            **values,
            'd_min':                 d_min,
            'd_min_per_path_length': d_min_per_path_length,
            'd_mean':                d_mean,
            'dtw_features':          json.dumps(dtw_features, sort_keys=True),
            'k_neighbors':           int(seg_pred.get('n_neighbors') or 0),
            'neighbor_ids':          list(seg_pred.get('neighbor_ids') or []),
            'query_length':          None,
            'query_path_length':     seg_pred.get('query_path_length'),
            'config_hash':           cfg.hash(),
            'config':                cfg.to_json(),
            'config_k':              cfg.k,
            'config_dtw_mode':       cfg.dtw_mode,
            'config_metric':         cfg.metric,
            'search_modes':          cfg.search_modes_str(),
        })
    return rows


def build_trajectory_row_from_prediction(
    *, traj_id: str, split_role: SplitRole, p_actual: float,
    prediction: Optional[Dict[str, Any]], retrieval_strategy: RetrievalStrategy,
    cfg: CalibrationConfig, segment_ids: Optional[List[str]] = None,
    segment_rows: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if prediction is None:
        return None
    values = prediction_to_row_values(
        p_actual=p_actual, prediction=prediction, sigma_floor=cfg.sigma_floor,
    )
    if values is None:
        return None

    segment_ids  = segment_ids  or []
    segment_rows = segment_rows or []
    d_min_per_path_length = prediction.get('d_min_per_path_length')

    traj_features: Dict[str, Any] = {
        'source':                'similarity_pipeline',
        'retrieval_strategy':    retrieval_strategy,
        'stage':                 'stage2_dtw',
        'n_segments':            int(prediction.get('n_segments') or len(segment_ids) or 0),
        'd_min_per_path_length': d_min_per_path_length,
    }

    if retrieval_strategy == 'direct':
        traj_features.update({
            'n_neighbors':  prediction.get('n_neighbors'),
            'neighbor_ids': prediction.get('neighbor_ids') or [],
            'd_min':        prediction.get('d_min'),
            'd_mean':       prediction.get('d_mean'),
        })
    else:
        seg_n_neighbors = [
            int(r.get('k_neighbors') or 0)
            for r in segment_rows if int(r.get('k_neighbors') or 0) > 0
        ]
        traj_features.update({
            'segment_neighbor_count_mean': float(np.mean(seg_n_neighbors)) if seg_n_neighbors else None,
            'segment_neighbor_count_min':  int(min(seg_n_neighbors))       if seg_n_neighbors else None,
            'segment_neighbor_count_max':  int(max(seg_n_neighbors))       if seg_n_neighbors else None,
            'segment_neighbor_ids_by_segment': {
                str(r['seg_id']): list(r.get('neighbor_ids') or [])
                for r in segment_rows if r.get('seg_id')
            },
        })

    return {
        'traj_id':             traj_id,
        'split_role':          split_role,
        'retrieval_strategy':  retrieval_strategy,
        'calibration_tag':     cfg.calibration_tag,
        **values,
        'd_min_per_path_length': d_min_per_path_length,
        'traj_features':       json.dumps(traj_features, sort_keys=True),
        'segment_ids':         segment_ids,
        'n_segments':          int(prediction.get('n_segments') or len(segment_ids) or 0),
        'config_hash':         cfg.hash(),
        'config':              cfg.to_json(),
        'config_k':            cfg.k,
        'config_dtw_mode':     cfg.dtw_mode,
        'config_metric':       cfg.metric,
        'search_modes':        cfg.search_modes_str(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# DB inserts
# ═════════════════════════════════════════════════════════════════════════════

async def insert_segment_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    if not batch:
        return
    await conn.executemany("""
        INSERT INTO prognosis.confidence_calibration_seg (
            seg_id, traj_id, split_role, retrieval_strategy, calibration_tag,
            p_actual, p_predicted, prediction_error, log_prediction_error,
            sigma, nonconformity_score,
            d_min, d_min_per_path_length, d_mean,
            dtw_features, k_neighbors, neighbor_ids,
            query_length, query_path_length,
            config_hash, config, config_k, config_dtw_mode, config_metric, search_modes
        ) VALUES (
            $1,$2,$3,$4,$5,
            $6,$7,$8,$9,
            $10,$11,
            $12,$13,$14,
            $15::jsonb,$16,$17,
            $18,$19,
            $20,$21::jsonb,$22,$23,$24,$25
        )
        ON CONFLICT (seg_id, config_hash, calibration_tag) DO UPDATE SET
            split_role            = EXCLUDED.split_role,
            retrieval_strategy    = EXCLUDED.retrieval_strategy,
            p_actual              = EXCLUDED.p_actual,
            p_predicted           = EXCLUDED.p_predicted,
            prediction_error      = EXCLUDED.prediction_error,
            log_prediction_error  = EXCLUDED.log_prediction_error,
            sigma                 = EXCLUDED.sigma,
            nonconformity_score   = EXCLUDED.nonconformity_score,
            d_min                 = EXCLUDED.d_min,
            d_min_per_path_length = EXCLUDED.d_min_per_path_length,
            d_mean                = EXCLUDED.d_mean,
            dtw_features          = EXCLUDED.dtw_features,
            k_neighbors           = EXCLUDED.k_neighbors,
            neighbor_ids          = EXCLUDED.neighbor_ids,
            query_length          = EXCLUDED.query_length,
            query_path_length     = EXCLUDED.query_path_length,
            config                = EXCLUDED.config,
            config_k              = EXCLUDED.config_k,
            config_dtw_mode       = EXCLUDED.config_dtw_mode,
            config_metric         = EXCLUDED.config_metric,
            search_modes          = EXCLUDED.search_modes,
            computed_at           = NOW()
    """, [
        (
            r['seg_id'], r['traj_id'], r['split_role'], r['retrieval_strategy'], r['calibration_tag'],
            r['p_actual'], r['p_predicted'], r['prediction_error'], r['log_prediction_error'],
            r['sigma'], r['nonconformity_score'],
            r.get('d_min'), r.get('d_min_per_path_length'), r.get('d_mean'),
            r['dtw_features'], r['k_neighbors'], r['neighbor_ids'],
            r.get('query_length'), r.get('query_path_length'),
            r['config_hash'], r['config'], r['config_k'], r['config_dtw_mode'],
            r['config_metric'], r['search_modes'],
        )
        for r in batch
    ])


async def insert_trajectory_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    if not batch:
        return
    await conn.executemany("""
        INSERT INTO prognosis.confidence_calibration_traj (
            traj_id, split_role, retrieval_strategy, calibration_tag,
            p_actual, p_predicted, prediction_error, log_prediction_error,
            sigma, nonconformity_score,
            d_min_per_path_length,
            traj_features, segment_ids, n_segments,
            config_hash, config, config_k, config_dtw_mode, config_metric, search_modes
        ) VALUES (
            $1,$2,$3,$4,
            $5,$6,$7,$8,
            $9,$10,
            $11,
            $12::jsonb,$13,$14,
            $15,$16::jsonb,$17,$18,$19,$20
        )
        ON CONFLICT (traj_id, config_hash, calibration_tag) DO UPDATE SET
            split_role            = EXCLUDED.split_role,
            retrieval_strategy    = EXCLUDED.retrieval_strategy,
            p_actual              = EXCLUDED.p_actual,
            p_predicted           = EXCLUDED.p_predicted,
            prediction_error      = EXCLUDED.prediction_error,
            log_prediction_error  = EXCLUDED.log_prediction_error,
            sigma                 = EXCLUDED.sigma,
            nonconformity_score   = EXCLUDED.nonconformity_score,
            d_min_per_path_length = EXCLUDED.d_min_per_path_length,
            traj_features         = EXCLUDED.traj_features,
            segment_ids           = EXCLUDED.segment_ids,
            n_segments            = EXCLUDED.n_segments,
            config                = EXCLUDED.config,
            config_k              = EXCLUDED.config_k,
            config_dtw_mode       = EXCLUDED.config_dtw_mode,
            config_metric         = EXCLUDED.config_metric,
            search_modes          = EXCLUDED.search_modes,
            computed_at           = NOW()
    """, [
        (
            r['traj_id'], r['split_role'], r['retrieval_strategy'], r['calibration_tag'],
            r['p_actual'], r['p_predicted'], r['prediction_error'], r['log_prediction_error'],
            r['sigma'], r['nonconformity_score'],
            r.get('d_min_per_path_length'),
            r['traj_features'], r['segment_ids'], r['n_segments'],
            r['config_hash'], r['config'], r['config_k'], r['config_dtw_mode'],
            r['config_metric'], r['search_modes'],
        )
        for r in batch
    ])


# ═════════════════════════════════════════════════════════════════════════════
# Quantile computation
# ═════════════════════════════════════════════════════════════════════════════

def conformal_quantile(scores: Sequence[float], coverage: float) -> float:
    if not scores:
        raise ValueError("Cannot compute conformal quantile without scores.")
    sorted_scores = sorted(float(s) for s in scores)
    n    = len(sorted_scores)
    rank = min(n, math.ceil((n + 1) * coverage))
    return float(sorted_scores[rank - 1])


async def fetch_level_rows(
    conn: asyncpg.Connection, level: Level,
    config_hash: str, calibration_tag: str, split_role: SplitRole,
) -> List[asyncpg.Record]:
    table = (
        'prognosis.confidence_calibration_seg'
        if level == 'segment'
        else 'prognosis.confidence_calibration_traj'
    )
    return await conn.fetch(f"""
        SELECT p_actual, p_predicted, prediction_error,
               log_prediction_error, sigma, nonconformity_score
        FROM {table}
        WHERE config_hash = $1 AND calibration_tag = $2 AND split_role = $3
        ORDER BY nonconformity_score
    """, config_hash, calibration_tag, split_role)


def coverage_stats(rows: Sequence[asyncpg.Record], q: float) -> Dict[str, Any]:
    if not rows:
        return {'n': 0, 'mae': None, 'empirical_coverage': None,
                'mean_interval_width': None, 'median_interval_width': None}
    p_actual = np.array([float(r['p_actual'])   for r in rows])
    p_pred   = np.array([float(r['p_predicted']) for r in rows])
    sigma    = np.array([float(r['sigma'])       for r in rows])
    err      = np.array([float(r['prediction_error']) for r in rows])
    lower    = np.maximum(0.0, p_pred - q * sigma)
    upper    = p_pred + q * sigma
    covered  = (p_actual >= lower) & (p_actual <= upper)
    widths   = upper - lower
    return {
        'n':                    int(len(rows)),
        'mae':                  float(err.mean()),
        'empirical_coverage':   float(covered.mean()),
        'mean_interval_width':  float(widths.mean()),
        'median_interval_width': float(np.median(widths)),
    }


async def compute_and_store_quantiles(
    conn: asyncpg.Connection, cfg: CalibrationConfig,
    coverages: Sequence[float], level: Level,
) -> None:
    cal_rows  = await fetch_level_rows(conn, level, cfg.hash(), cfg.calibration_tag, 'calibration')
    test_rows = await fetch_level_rows(conn, level, cfg.hash(), cfg.calibration_tag, 'test')

    if not cal_rows:
        logger.warning(f"No calibration rows for level={level} hash={cfg.hash()} tag={cfg.calibration_tag}")
        return

    scores  = [float(r['nonconformity_score']) for r in cal_rows]
    cal_mae = float(np.mean([float(r['prediction_error']) for r in cal_rows]))

    logger.info(f"{level.upper()} — tag={cfg.calibration_tag}  n_cal={len(cal_rows):,}  n_test={len(test_rows):,}")

    for cov in coverages:
        q        = conformal_quantile(scores, cov)
        t_stats  = coverage_stats(test_rows, q)

        await conn.execute("""
            INSERT INTO prognosis.confidence_quantiles (
                level, metric, dtw_mode, retrieval_strategy,
                config_k, search_modes, calibration_tag, coverage,
                quantile_value, n_calibration, n_test,
                mae_calibration, mae_test, empirical_coverage,
                mean_interval_width, median_interval_width,
                config_hash, config
            ) VALUES (
                $1,$2,$3,$4,
                $5,$6,$7,$8,
                $9,$10,$11,
                $12,$13,$14,
                $15,$16,
                $17,$18::jsonb
            )
            ON CONFLICT (metric, dtw_mode, retrieval_strategy, level,
                         config_k, search_modes, calibration_tag, coverage)
            DO UPDATE SET
                quantile_value        = EXCLUDED.quantile_value,
                n_calibration         = EXCLUDED.n_calibration,
                n_test                = EXCLUDED.n_test,
                mae_calibration       = EXCLUDED.mae_calibration,
                mae_test              = EXCLUDED.mae_test,
                empirical_coverage    = EXCLUDED.empirical_coverage,
                mean_interval_width   = EXCLUDED.mean_interval_width,
                median_interval_width = EXCLUDED.median_interval_width,
                config_hash           = EXCLUDED.config_hash,
                config                = EXCLUDED.config,
                computed_at           = NOW()
        """,
            level, cfg.metric, cfg.dtw_mode, cfg.retrieval_strategy,
            cfg.k, cfg.search_modes_str(), cfg.calibration_tag, float(cov),
            q, len(cal_rows), t_stats['n'],
            cal_mae, t_stats['mae'], t_stats['empirical_coverage'],
            t_stats['mean_interval_width'], t_stats['median_interval_width'],
            cfg.hash(), cfg.to_json(),
        )
        logger.info(
            f"  q{int(cov*100):02d}: {q:.4f} | "
            f"test_cov={t_stats['empirical_coverage']:.3f} | "
            f"mean_width={t_stats['mean_interval_width']:.4f}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Pipeline processing
# ═════════════════════════════════════════════════════════════════════════════

async def process_trajectory_bundle(
    *, traj_id: str, p_actual_traj: float, split_role: SplitRole,
    pool: asyncpg.Pool, decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig], own_segment_ids: Sequence[str],
    segment_actuals: Dict[str, float],
    include_tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
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
                weights={m: 1.0 for m in cfg_for_pipeline.search_modes},
                limit=cfg_for_pipeline.k,
                buffer_factor=5,
                prefilter_features=[],
                metric=cfg_for_pipeline.metric,
                include_tags=include_tags,
                exclude_ids=exclude_ids,
                stage2_active=True,
                dtw_mode=cfg_for_pipeline.dtw_mode,
                prognosis_active=True,
                coverage=0.90,
                conformal_active=False,
            )

        if result.get('error'):
            return None

        prognosis = result.get('prognosis') or {}
        if not prognosis:
            return None

        segment_rows:        List[Dict[str, Any]] = []
        decomposed_traj_row: Optional[Dict[str, Any]] = None
        direct_traj_row:     Optional[Dict[str, Any]] = None

        if decomposed_cfg is not None:
            segment_rows = build_segment_rows_from_prognosis(
                traj_id=traj_id, split_role=split_role,
                prognosis=prognosis, segment_actuals=segment_actuals,
                cfg=decomposed_cfg,
            )
            decomposed_traj_row = build_trajectory_row_from_prediction(
                traj_id=traj_id, split_role=split_role, p_actual=p_actual_traj,
                prediction=prognosis.get('decomposed'), retrieval_strategy='decomposed',
                cfg=decomposed_cfg,
                segment_ids=[r['seg_id'] for r in segment_rows],
                segment_rows=segment_rows,
            )

        if direct_cfg is not None:
            direct_traj_row = build_trajectory_row_from_prediction(
                traj_id=traj_id, split_role=split_role, p_actual=p_actual_traj,
                prediction=prognosis.get('direct'), retrieval_strategy='direct',
                cfg=direct_cfg, segment_ids=[],
            )

        return {
            'segment_rows':        segment_rows,
            'decomposed_traj_row': decomposed_traj_row,
            'direct_traj_row':     direct_traj_row,
        }

    except Exception as e:
        logger.warning(f"Bundle failed for {traj_id}: {e}", exc_info=False)
        return None


async def get_done_trajectory_ids_for_bundle(
    conn: asyncpg.Connection, decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig],
) -> set:
    done_sets = []
    if decomposed_cfg:
        done_sets.append(await get_already_computed_trajectories(
            conn, decomposed_cfg.hash(), decomposed_cfg.calibration_tag,
        ))
    if direct_cfg:
        done_sets.append(await get_already_computed_trajectories(
            conn, direct_cfg.hash(), direct_cfg.calibration_tag,
        ))
    return set.intersection(*done_sets) if done_sets else set()


# ═════════════════════════════════════════════════════════════════════════════
# Main runner
# ═════════════════════════════════════════════════════════════════════════════

async def run_calibration(
    *, pool: asyncpg.Pool, decomposed_cfg: Optional[CalibrationConfig],
    direct_cfg: Optional[CalibrationConfig], batch_size: int,
    resume: bool, max_trajectories: Optional[int], coverages: Sequence[float],
    include_tags: Optional[List[str]] = None,
) -> None:
    cfg_for_query = decomposed_cfg or direct_cfg
    if cfg_for_query is None:
        return

    async with pool.acquire() as conn:
        await ensure_calibration_tables(conn)

        if not resume:
            if decomposed_cfg:
                await delete_config_rows(conn, decomposed_cfg.hash(), decomposed_cfg.calibration_tag)
            if direct_cfg and (not decomposed_cfg or direct_cfg.hash() != decomposed_cfg.hash()):
                await delete_config_rows(conn, direct_cfg.hash(), direct_cfg.calibration_tag)

        all_trajs = await get_all_traj_ids(
            conn, cfg_for_query.metric,
            max_trajectories=max_trajectories,
            include_tags=include_tags,
        )
        traj_ids        = [t for t, _ in all_trajs]
        traj_to_seg_ids = await get_all_segments_for_trajectories(conn, traj_ids)
        segment_actuals = await get_segment_actual_values_for_trajectories(
            conn, traj_ids, cfg_for_query.metric,
        )
        already_done = (
            await get_done_trajectory_ids_for_bundle(conn, decomposed_cfg, direct_cfg)
            if resume else set()
        )

    todo = [
        (tid, p, split_role_for_traj(tid, cfg_for_query.test_ratio, cfg_for_query.split_seed))
        for tid, p in all_trajs if tid not in already_done
    ]
    n_cal  = sum(1 for _, _, r in todo if r == 'calibration')
    n_test = sum(1 for _, _, r in todo if r == 'test')

    logger.info(f"Total: {len(all_trajs):,} | already done: {len(already_done):,} | "
                f"to process: {len(todo):,} (cal={n_cal:,} test={n_test:,})")

    seg_buffer:  List[Dict[str, Any]] = []
    traj_buffer: List[Dict[str, Any]] = []
    n_ok = n_fail = 0

    with tqdm(total=len(todo), unit='traj', desc=f'Calibrating [{cfg_for_query.calibration_tag}]') as pbar:
        for batch_start in range(0, len(todo), batch_size):
            batch = todo[batch_start: batch_start + batch_size]
            tasks = [
                process_trajectory_bundle(
                    traj_id=tid, p_actual_traj=p, split_role=role,
                    pool=pool, decomposed_cfg=decomposed_cfg, direct_cfg=direct_cfg,
                    own_segment_ids=traj_to_seg_ids.get(tid, []),
                    segment_actuals=segment_actuals,
                    include_tags=include_tags,
                )
                for tid, p, role in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            for res in results:
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

    logger.info(f"Done. ok={n_ok:,} fail={n_fail:,}")

    async with pool.acquire() as conn:
        if decomposed_cfg:
            await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'segment')
            await compute_and_store_quantiles(conn, decomposed_cfg, coverages, 'trajectory')
        if direct_cfg:
            await compute_and_store_quantiles(conn, direct_cfg, coverages, 'trajectory')


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(description='Conformal calibration builder')
    parser.add_argument('--k',                  type=int,   default=10)
    parser.add_argument('--batch',              type=int,   default=10)
    parser.add_argument('--limit',              type=int,   default=None)
    parser.add_argument('--metric',             type=str,   default='sidtw', choices=sorted(ALLOWED_METRICS))
    parser.add_argument('--dtw-mode',           type=str,   default='position', choices=sorted(ALLOWED_DTW_MODES))
    parser.add_argument('--search-modes',       nargs='+',  default=DEFAULT_SEARCH_MODES)
    parser.add_argument('--sigma-floor',        type=float, default=0.005)
    parser.add_argument('--test-ratio',         type=float, default=0.2)
    parser.add_argument('--split-seed',         type=int,   default=42)
    parser.add_argument('--coverage',           type=float, nargs='+', default=[0.80, 0.90, 0.95])
    parser.add_argument('--tag',                type=str,   default='all',
                        help='Calibration tag, e.g. "all", "bandit_v1", "workspace_A"')
    parser.add_argument('--include-tags',       nargs='+',  default=None,
                        help='Only calibrate on trajectories with these DB tags')
    parser.add_argument('--resume',             action='store_true', default=True)
    parser.add_argument('--full-rebuild',       action='store_true', default=False)
    parser.add_argument('--retrieval-strategy', type=str,   default='both',
                        choices=['decomposed', 'direct', 'both'])
    args = parser.parse_args()

    base_config = CalibrationConfig(
        k=args.k,
        dtw_mode=validate_dtw_mode(args.dtw_mode),
        metric=validate_metric(args.metric),
        search_modes=tuple(sorted(args.search_modes)),
        retrieval_strategy='decomposed',
        calibration_tag=args.tag,
        sigma_floor=float(args.sigma_floor),
        test_ratio=float(args.test_ratio),
        split_seed=int(args.split_seed),
    )

    decomposed_cfg = direct_cfg = None
    if args.retrieval_strategy in ('decomposed', 'both'):
        decomposed_cfg = replace(base_config, retrieval_strategy='decomposed')
    if args.retrieval_strategy in ('direct', 'both'):
        direct_cfg = replace(base_config, retrieval_strategy='direct')

    logger.info(f"Starting calibration — tag='{args.tag}'")
    if decomposed_cfg:
        logger.info(f"  decomposed hash: {decomposed_cfg.hash()}")
    if direct_cfg:
        logger.info(f"  direct    hash: {direct_cfg.hash()}")

    pool = await create_pool(DATABASE_URL)
    try:
        await run_calibration(
            pool=pool,
            decomposed_cfg=decomposed_cfg,
            direct_cfg=direct_cfg,
            batch_size=args.batch,
            resume=args.resume and not args.full_rebuild,
            max_trajectories=args.limit,
            coverages=args.coverage,
            include_tags=args.include_tags,
        )
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())
