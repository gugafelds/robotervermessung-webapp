"""
calibration_set_builder.py
===========================
Conformal calibration builder — Stage 1 (RRF) and Stage 2 (DTW).

DB lookup key for confidence_quantiles
----------------------------------------
metric + dtw_mode + retrieval_strategy + level + k + search_modes + calibration_tag + config_stage

config_stage = 1  →  Stage 1 RRF (no DTW), dtw_mode = 'none'
                      d_min_per_path_length = 1 / rrf_best,  d_normalized = 1 / rrf_mean,  d_max = 1 / rrf_worst
config_stage = 2  →  Stage 2 DTW (default)
                      d_min_per_path_length = dtw_min / path_length
                      d_normalized          = dtw_mean / path_length
                      d_max_per_path_length = dtw_max / path_length

calibration_tag allows separate calibration per DB subset (e.g. 'all', 'bandit_v1').
Online lookup falls back from specific tag to 'all' if no row found.

Usage
-----
  # Stage 2 (default):
  python calibration_set_builder.py --tag all
  python calibration_set_builder.py --tag bandit_v1 --include-tags bandit_v1 --full-rebuild

  # Stage 1:
  python calibration_set_builder.py --stage1 --tag all
  python calibration_set_builder.py --stage1 --tag bandit_v1 --include-tags bandit_v1
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import math
import os
import sys
from dataclasses import replace
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import asyncpg
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app'))

from utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline
from utils.feature_prediction.conformal_config import CalibrationConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

DATABASE_URL         = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
EPSILON              = 1e-6
DEFAULT_SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']
ALLOWED_METRICS      = {'sidtw', 'qdtw'}
ALLOWED_DTW_MODES    = {'position', 'joint', 'none'}   # 'none' for Stage 1

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
        'p_actual':            float(p_actual),
        'p_predicted':         p_hat,
        'prediction_error':    err,
        'sigma':               sigma,
        'nonconformity_score': err / sigma,
    }


# ═════════════════════════════════════════════════════════════════════════════
# DB schema
# ═════════════════════════════════════════════════════════════════════════════

async def ensure_calibration_tables(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS prognosis;

        CREATE TABLE IF NOT EXISTS prognosis.confidence_calibration (
            level                  TEXT        NOT NULL CHECK (level IN ('segment', 'trajectory')),
            entity_id              TEXT        NOT NULL,
            traj_id                TEXT        NOT NULL,
            split_role             TEXT        NOT NULL CHECK (split_role IN ('calibration', 'test')),
            retrieval_strategy     TEXT        NOT NULL DEFAULT 'decomposed',
            calibration_tag        TEXT        NOT NULL DEFAULT 'all',
            config_stage           INT         NOT NULL DEFAULT 2 CHECK (config_stage IN (1, 2)),

            p_actual               FLOAT       NOT NULL,
            p_predicted            FLOAT       NOT NULL,
            prediction_error       FLOAT       NOT NULL,
            sigma                  FLOAT       NOT NULL,
            nonconformity_score    FLOAT       NOT NULL,

            d_min                  FLOAT,
            d_max                  FLOAT,
            d_normalized           FLOAT,
            query_path_length      FLOAT,
            neighbor_ids           TEXT[]      NOT NULL DEFAULT '{}',

            config_hash            TEXT        NOT NULL,
            config_k               INT         NOT NULL,
            config_dtw_mode        TEXT        NOT NULL,
            config_metric          TEXT        NOT NULL,
            search_modes           TEXT        NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            PRIMARY KEY (level, entity_id, config_hash, calibration_tag, config_stage)
        );

        CREATE INDEX IF NOT EXISTS idx_cc_lookup
            ON prognosis.confidence_calibration
            (config_hash, calibration_tag, split_role, config_stage, level);

        CREATE TABLE IF NOT EXISTS prognosis.confidence_quantiles (
            id                     SERIAL      PRIMARY KEY,
            level                  TEXT        NOT NULL,
            metric                 TEXT        NOT NULL,
            dtw_mode               TEXT        NOT NULL,
            retrieval_strategy     TEXT        NOT NULL,
            config_k               INT         NOT NULL,
            search_modes           TEXT        NOT NULL,
            calibration_tag        TEXT        NOT NULL DEFAULT 'all',
            config_stage           INT         NOT NULL DEFAULT 2,
            coverage               FLOAT       NOT NULL,

            quantile_value         FLOAT       NOT NULL,
            n_calibration          INT         NOT NULL,
            n_test                 INT,
            mae_calibration        FLOAT,
            mae_test               FLOAT,
            empirical_coverage     FLOAT,
            mean_interval_width    FLOAT,
            median_interval_width  FLOAT,

            config_hash            TEXT        NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (metric, dtw_mode, retrieval_strategy, level,
                    config_k, search_modes, calibration_tag, coverage, config_stage)
        );

        CREATE INDEX IF NOT EXISTS idx_cq_lookup
            ON prognosis.confidence_quantiles
            (metric, dtw_mode, retrieval_strategy, level,
             config_k, search_modes, calibration_tag, coverage, config_stage);
    """)
    logger.info("Calibration tables ready.")


# ═════════════════════════════════════════════════════════════════════════════
# DB query helpers
# ═════════════════════════════════════════════════════════════════════════════

async def create_pool(url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        url, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )


async def get_all_tags(conn: asyncpg.Connection) -> List[str]:
    rows = await conn.fetch("SELECT tag FROM motion.tag_info ORDER BY tag")
    return [r['tag'] for r in rows]


async def get_all_traj_ids(
    conn: asyncpg.Connection,
    metric: str,
    max_trajectories: Optional[int] = None,
    include_tags: Optional[List[str]] = None,
) -> List[Tuple[str, float]]:
    metric     = validate_metric(metric)
    table_name = f"evaluation.{metric}_info"
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
    result: Dict[str, List[str]] = {}
    for r in rows:
        result.setdefault(r['traj_id'], []).append(r['seg_id'])
    return result


async def get_segment_actual_values_for_trajectories(
    conn: asyncpg.Connection, traj_ids: List[str], metric: str,
) -> Dict[str, float]:
    table_name = f"evaluation.{metric}_info"
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
    conn: asyncpg.Connection, config_hash: str, calibration_tag: str, config_stage: int,
) -> set:
    rows = await conn.fetch("""
        SELECT entity_id FROM prognosis.confidence_calibration
        WHERE config_hash = $1 AND calibration_tag = $2 AND config_stage = $3
          AND level = 'trajectory'
    """, config_hash, calibration_tag, config_stage)
    return {r['entity_id'] for r in rows}


async def delete_config_rows(
    conn: asyncpg.Connection, config_hash: str, calibration_tag: str, config_stage: int,
) -> None:
    await conn.execute(
        "DELETE FROM prognosis.confidence_quantiles WHERE config_hash=$1 AND calibration_tag=$2 AND config_stage=$3",
        config_hash, calibration_tag, config_stage,
    )
    await conn.execute(
        "DELETE FROM prognosis.confidence_calibration WHERE config_hash=$1 AND calibration_tag=$2 AND config_stage=$3",
        config_hash, calibration_tag, config_stage,
    )
    logger.info(f"Deleted rows for config_hash={config_hash} tag={calibration_tag} stage={config_stage}")


# ═════════════════════════════════════════════════════════════════════════════
# DB inserts
# ═════════════════════════════════════════════════════════════════════════════

async def insert_calibration_batch(conn: asyncpg.Connection, batch: List[Dict[str, Any]]) -> None:
    if not batch:
        return
    await conn.executemany("""
        INSERT INTO prognosis.confidence_calibration (
            level, entity_id, traj_id, split_role, retrieval_strategy, calibration_tag, config_stage,
            p_actual, p_predicted, prediction_error, sigma, nonconformity_score,
            d_min, d_max, d_normalized, query_path_length, neighbor_ids,
            config_hash, config_k, config_dtw_mode, config_metric, search_modes
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,
            $8,$9,$10,$11,$12,
            $13,$14,$15,$16,$17,
            $18,$19,$20,$21,$22
        )
        ON CONFLICT (level, entity_id, config_hash, calibration_tag, config_stage) DO UPDATE SET
            split_role          = EXCLUDED.split_role,
            retrieval_strategy  = EXCLUDED.retrieval_strategy,
            traj_id             = EXCLUDED.traj_id,
            p_actual            = EXCLUDED.p_actual,
            p_predicted         = EXCLUDED.p_predicted,
            prediction_error    = EXCLUDED.prediction_error,
            sigma               = EXCLUDED.sigma,
            nonconformity_score = EXCLUDED.nonconformity_score,
            d_min               = EXCLUDED.d_min,
            d_max               = EXCLUDED.d_max,
            d_normalized        = EXCLUDED.d_normalized,
            query_path_length   = EXCLUDED.query_path_length,
            neighbor_ids        = EXCLUDED.neighbor_ids,
            config_k            = EXCLUDED.config_k,
            config_dtw_mode     = EXCLUDED.config_dtw_mode,
            config_metric       = EXCLUDED.config_metric,
            search_modes        = EXCLUDED.search_modes,
            computed_at         = NOW()
    """, [
        (
            r['level'], r['entity_id'], r['traj_id'], r['split_role'], r['retrieval_strategy'],
            r['calibration_tag'], r['config_stage'],
            r['p_actual'], r['p_predicted'], r['prediction_error'],
            r['sigma'], r['nonconformity_score'],
            r.get('d_min'), r.get('d_max'), r.get('d_normalized'),
            r.get('query_path_length'), r['neighbor_ids'],
            r['config_hash'], r['config_k'],
            r['config_dtw_mode'], r['config_metric'], r['search_modes'],
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
    config_hash: str, calibration_tag: str, split_role: SplitRole, config_stage: int,
) -> List[asyncpg.Record]:
    return await conn.fetch("""
        SELECT p_actual, p_predicted, prediction_error, sigma, nonconformity_score
        FROM prognosis.confidence_calibration
        WHERE level = $1 AND config_hash = $2 AND calibration_tag = $3
          AND split_role = $4 AND config_stage = $5
        ORDER BY nonconformity_score
    """, level, config_hash, calibration_tag, split_role, config_stage)


def coverage_stats(rows: Sequence[asyncpg.Record], q: float) -> Dict[str, Any]:
    if not rows:
        return {'n': 0, 'mae': None, 'empirical_coverage': None,
                'mean_interval_width': None, 'median_interval_width': None}
    p_actual = np.array([float(r['p_actual'])        for r in rows])
    p_pred   = np.array([float(r['p_predicted'])     for r in rows])
    sigma    = np.array([float(r['sigma'])            for r in rows])
    err      = np.array([float(r['prediction_error']) for r in rows])
    lower    = np.maximum(0.0, p_pred - q * sigma)
    upper    = p_pred + q * sigma
    covered  = (p_actual >= lower) & (p_actual <= upper)
    widths   = upper - lower
    return {
        'n':                     int(len(rows)),
        'mae':                   float(err.mean()),
        'empirical_coverage':    float(covered.mean()),
        'mean_interval_width':   float(widths.mean()),
        'median_interval_width': float(np.median(widths)),
    }


async def compute_and_store_quantiles(
    conn: asyncpg.Connection, cfg: CalibrationConfig,
    coverages: Sequence[float], level: Level, config_stage: int,
) -> None:
    cal_rows  = await fetch_level_rows(conn, level, cfg.hash(), cfg.calibration_tag, 'calibration', config_stage)
    test_rows = await fetch_level_rows(conn, level, cfg.hash(), cfg.calibration_tag, 'test', config_stage)

    if not cal_rows:
        logger.warning(
            f"No calibration rows for level={level} hash={cfg.hash()} "
            f"tag={cfg.calibration_tag} stage={config_stage}"
        )
        return

    scores  = [float(r['nonconformity_score']) for r in cal_rows]
    cal_mae = float(np.mean([float(r['prediction_error']) for r in cal_rows]))

    logger.info(
        f"{level.upper()} stage={config_stage} — tag={cfg.calibration_tag} "
        f"n_cal={len(cal_rows):,}  n_test={len(test_rows):,}"
    )

    for cov in coverages:
        q       = conformal_quantile(scores, cov)
        t_stats = coverage_stats(test_rows, q)

        await conn.execute("""
            INSERT INTO prognosis.confidence_quantiles (
                level, metric, dtw_mode, retrieval_strategy,
                config_k, search_modes, calibration_tag, config_stage, coverage,
                quantile_value, n_calibration, n_test,
                mae_calibration, mae_test, empirical_coverage,
                mean_interval_width, median_interval_width,
                config_hash
            ) VALUES (
                $1,$2,$3,$4,
                $5,$6,$7,$8,$9,
                $10,$11,$12,
                $13,$14,$15,
                $16,$17,
                $18
            )
            ON CONFLICT (metric, dtw_mode, retrieval_strategy, level,
                         config_k, search_modes, calibration_tag, coverage, config_stage)
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
                computed_at           = NOW()
        """,
            level, cfg.metric, cfg.dtw_mode, cfg.retrieval_strategy,
            cfg.k, cfg.search_modes_str(), cfg.calibration_tag, config_stage, float(cov),
            q, len(cal_rows), t_stats['n'],
            cal_mae, t_stats['mae'], t_stats['empirical_coverage'],
            t_stats['mean_interval_width'], t_stats['median_interval_width'],
            cfg.hash(),
        )
        logger.info(
            f"  q{int(cov*100):02d}: {q:.4f} | "
            f"test_cov={t_stats['empirical_coverage']:.3f} | "
            f"mean_width={t_stats['mean_interval_width']:.4f}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Row builders — Stage 2 (DTW)
# ═════════════════════════════════════════════════════════════════════════════

def build_segment_rows_stage2(
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
        rows.append({
            'level':                'segment',
            'entity_id':            seg_id,
            'traj_id':              traj_id,
            'split_role':           split_role,
            'retrieval_strategy':   'decomposed',
            'calibration_tag':      cfg.calibration_tag,
            'config_stage':         2,
            **values,
            'd_min':             seg_pred.get('d_min'),
            'd_max':             seg_pred.get('d_max'),
            'd_normalized':      seg_pred.get('d_normalized'),
            'query_path_length': seg_pred.get('query_path_length'),
            'neighbor_ids':      list(seg_pred.get('neighbor_ids') or []),
            'config_hash':       cfg.hash(),
            'config_k':          cfg.k,
            'config_dtw_mode':   cfg.dtw_mode,
            'config_metric':     cfg.metric,
            'search_modes':      cfg.search_modes_str(),
        })
    return rows


def build_trajectory_row_stage2(
    *, traj_id: str, split_role: SplitRole, p_actual: float,
    prediction: Optional[Dict[str, Any]], retrieval_strategy: RetrievalStrategy,
    cfg: CalibrationConfig, segment_rows: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if prediction is None:
        return None
    values = prediction_to_row_values(
        p_actual=p_actual, prediction=prediction, sigma_floor=cfg.sigma_floor,
    )
    if values is None:
        return None

    # neighbor_ids: for direct = from prediction, for decomposed = union of segment neighbor_ids
    if retrieval_strategy == 'direct':
        neighbor_ids = list(prediction.get('neighbor_ids') or [])
    else:
        seen: Dict[str, None] = {}
        for r in (segment_rows or []):
            for nid in (r.get('neighbor_ids') or []):
                seen[nid] = None
        neighbor_ids = list(seen.keys())

    return {
        'level':                'trajectory',
        'entity_id':            traj_id,
        'traj_id':              traj_id,
        'split_role':           split_role,
        'retrieval_strategy':   retrieval_strategy,
        'calibration_tag':      cfg.calibration_tag,
        'config_stage':         2,
        **values,
        'd_min':               prediction.get('d_min'),
        'd_max':               prediction.get('d_max'),
        'd_normalized':        prediction.get('d_normalized'),
        'query_path_length':   None,
        'neighbor_ids':        neighbor_ids,
        'config_hash':         cfg.with_strategy(retrieval_strategy).hash(),
        'config_k':            cfg.k,
        'config_dtw_mode':     cfg.dtw_mode,
        'config_metric':       cfg.metric,
        'search_modes':        cfg.search_modes_str(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Row builders — Stage 1 (RRF)
# ═════════════════════════════════════════════════════════════════════════════

def _rrf_d_min(results: List[Dict[str, Any]]) -> Optional[float]:
    """
    d_min_per_path_length proxy for Stage 1:  1 / rrf_score_of_best_candidate.
    High RRF score → small "distance" → good match quality.
    Returns None if no valid candidates.
    """
    best_rrf = None
    for r in results:
        score = r.get('rrf_score')
        if score is not None and float(score) > EPSILON:
            s = float(score)
            if best_rrf is None or s > best_rrf:
                best_rrf = s
    if best_rrf is None:
        return None
    return round(1.0 / best_rrf, 6)


def build_segment_rows_stage1(
    *, traj_id: str, split_role: SplitRole, prognosis: Dict[str, Any],
    segment_actuals: Dict[str, float], cfg: CalibrationConfig,
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build segment calibration rows for Stage 1 (strategy='decomposed').
    These are the per-segment RRF predictions used for:
      - conformal quantile calibration at segment level
      - aggregation into s1_decomposed trajectory prediction
    """
    seg_results_map: Dict[str, List[Dict]] = {}
    for group in result.get('segment_similarity', []) or []:
        sid = group.get('target_segment')
        if sid:
            seg_results_map[sid] = (
                group.get('similar_segments', {}).get('results', []) or []
            )

    cfg_s1_decomposed = cfg.with_stage(1).with_strategy('decomposed')
    rows: List[Dict[str, Any]] = []
    for seg_pred in prognosis.get('s1_segments', []) or []:
        seg_id   = seg_pred.get('seg_id')
        p_actual = segment_actuals.get(seg_id) if seg_id else None
        if not seg_id or p_actual is None:
            continue
        values = prediction_to_row_values(
            p_actual=p_actual, prediction=seg_pred, sigma_floor=cfg.sigma_floor,
        )
        if values is None:
            continue

        seg_results  = seg_results_map.get(seg_id, [])
        d_min        = _rrf_d_min(seg_results)
        neighbor_ids = [
            str(r.get('seg_id') or r.get('traj_id'))
            for r in seg_results
            if r.get('seg_id') or r.get('traj_id')
        ]

        rows.append({
            'level':             'segment',
            'entity_id':         seg_id,
            'traj_id':           traj_id,
            'split_role':        split_role,
            'retrieval_strategy': 'decomposed',
            'calibration_tag':   cfg.calibration_tag,
            'config_stage':      1,
            **values,
            'd_min':             seg_pred.get('d_min') or d_min,
            'd_max':             seg_pred.get('d_max'),
            'd_normalized':      seg_pred.get('d_normalized'),
            'query_path_length': seg_pred.get('query_path_length'),
            'neighbor_ids':      neighbor_ids,
            'config_hash':       cfg_s1_decomposed.hash(),
            'config_k':          cfg.k,
            'config_dtw_mode':   'none',
            'config_metric':     cfg.metric,
            'search_modes':      cfg.search_modes_str(),
        })
    return rows


def build_trajectory_rows_stage1(
    *, traj_id: str, split_role: SplitRole, p_actual: float,
    prognosis: Dict[str, Any], cfg: CalibrationConfig,
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build trajectory calibration rows for Stage 1:
      - strategy='direct'     — trajectory-level RRF prediction (p̂_g from paper eq. 3)
      - strategy='decomposed' — segment-aggregated RRF prediction (p̂_gs from paper eq. 3)
    """
    traj_results = result.get('traj_similarity', {}).get('results', []) or []
    d_min_traj   = _rrf_d_min(traj_results)
    traj_nids    = [
        str(r.get('seg_id') or r.get('traj_id'))
        for r in traj_results
        if r.get('seg_id') or r.get('traj_id')
    ]

    rows: List[Dict[str, Any]] = []
    cfg_s1 = cfg.with_stage(1)

    for strategy, pred_key in [('direct', 's1_direct'), ('decomposed', 's1_decomposed')]:
        pred = prognosis.get(pred_key)
        if pred is None:
            continue
        values = prediction_to_row_values(
            p_actual=p_actual, prediction=pred, sigma_floor=cfg.sigma_floor,
        )
        if values is None:
            continue
        cfg_s1_strat = cfg_s1.with_strategy(strategy)
        neighbor_ids = list(pred.get('neighbor_ids') or traj_nids)
        rows.append({
            'level':              'trajectory',
            'entity_id':          traj_id,
            'traj_id':            traj_id,
            'split_role':         split_role,
            'retrieval_strategy': strategy,
            'calibration_tag':    cfg.calibration_tag,
            'config_stage':       1,
            **values,
            'd_min':             pred.get('d_min') or d_min_traj,
            'd_max':             pred.get('d_max'),
            'd_normalized':      pred.get('d_normalized'),
            'query_path_length': None,
            'neighbor_ids':      neighbor_ids,
            'config_hash':       cfg_s1_strat.hash(),
            'config_k':          cfg.k,
            'config_dtw_mode':   'none',
            'config_metric':     cfg.metric,
            'search_modes':      cfg.search_modes_str(),
        })
    return rows


# ═════════════════════════════════════════════════════════════════════════════
# Pipeline processing
# ═════════════════════════════════════════════════════════════════════════════

async def process_trajectory_bundle(
    *, traj_id: str, p_actual_traj: float, split_role: SplitRole,
    pool: asyncpg.Pool, cfg: CalibrationConfig,
    stage1_mode: bool,
    own_segment_ids: Sequence[str],
    segment_actuals: Dict[str, float],
    include_tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    exclude_ids = list(dict.fromkeys([traj_id, *own_segment_ids]))

    try:
        async with pool.acquire() as conn:
            result = await run_similarity_pipeline(
                target_id=traj_id,
                pool=pool,
                conn=conn,
                modes=list(cfg.search_modes),
                weights={m: 1.0 for m in cfg.search_modes},
                limit=cfg.k,
                buffer_factor=5,
                prefilter_features=[],
                metric=cfg.metric,
                include_tags=include_tags,
                exclude_ids=exclude_ids,
                stage2_active=not stage1_mode,
                dtw_mode=cfg.dtw_mode if not stage1_mode else 'position',  # dtw_mode irrelevant for stage1
                prognosis_active=True,
                coverage=0.90,
                conformal_active=False,
            )

        if result.get('error'):
            return None

        prognosis = result.get('prognosis') or {}
        if not prognosis:
            return None

        # ── Stage 1 rows — always built (RRF results always available) ──
        s1_seg_rows  = build_segment_rows_stage1(
            traj_id=traj_id, split_role=split_role,
            prognosis=prognosis, segment_actuals=segment_actuals,
            cfg=cfg, result=result,
        )
        s1_traj_rows = build_trajectory_rows_stage1(
            traj_id=traj_id, split_role=split_role, p_actual=p_actual_traj,
            prognosis=prognosis, cfg=cfg, result=result,
        )

        if stage1_mode:
            return {
                'segment_rows': s1_seg_rows,
                'traj_rows':    s1_traj_rows,
            }

        # ── Stage 2 rows — decomposed + direct ───────────────────────────
        decomposed_rows = build_segment_rows_stage2(
            traj_id=traj_id, split_role=split_role,
            prognosis=prognosis, segment_actuals=segment_actuals, cfg=cfg,
        )
        decomposed_traj = build_trajectory_row_stage2(
            traj_id=traj_id, split_role=split_role, p_actual=p_actual_traj,
            prediction=prognosis.get('decomposed'), retrieval_strategy='decomposed',
            cfg=cfg, segment_rows=decomposed_rows,
        )
        direct_traj = build_trajectory_row_stage2(
            traj_id=traj_id, split_role=split_role, p_actual=p_actual_traj,
            prediction=prognosis.get('direct'), retrieval_strategy='direct',
            cfg=cfg,
        )

        return {
            'segment_rows': s1_seg_rows + decomposed_rows,
            'traj_rows':    s1_traj_rows + [r for r in [decomposed_traj, direct_traj] if r is not None],
        }

    except Exception as e:
        logger.warning(f"Bundle failed for {traj_id}: {e}", exc_info=False)
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Main runner
# ═════════════════════════════════════════════════════════════════════════════

async def run_calibration(
    *, pool: asyncpg.Pool, cfg: CalibrationConfig,
    stage1_mode: bool, batch_size: int,
    resume: bool, max_trajectories: Optional[int],
    coverages: Sequence[float],
    include_tags: Optional[List[str]] = None,
) -> None:
    # Stage 2 runs also write stage 1 rows, so resume tracks stage 2 as
    # the source of truth. A stage-1-only run tracks stage 1 separately.
    resume_stage = 1 if stage1_mode else 2

    async with pool.acquire() as conn:
        await ensure_calibration_tables(conn)

        if not resume:
            await delete_config_rows(conn, cfg.hash(), cfg.calibration_tag, resume_stage)
            if not stage1_mode:
                # Stage 1 rows use different hashes (dtw_mode='none', separate per strategy)
                for s1_strat in ('direct', 'decomposed'):
                    cfg_s1 = cfg.with_stage(1).with_strategy(s1_strat)
                    await delete_config_rows(conn, cfg_s1.hash(), cfg.calibration_tag, 1)

        all_trajs = await get_all_traj_ids(
            conn, cfg.metric,
            max_trajectories=max_trajectories,
            include_tags=include_tags,
        )
        traj_ids        = [t for t, _ in all_trajs]
        traj_to_seg_ids = await get_all_segments_for_trajectories(conn, traj_ids)
        segment_actuals = await get_segment_actual_values_for_trajectories(
            conn, traj_ids, cfg.metric,
        )
        already_done = (
            await get_already_computed_trajectories(conn, cfg.hash(), cfg.calibration_tag, resume_stage)
            if resume else set()
        )

    todo = [
        (tid, p, split_role_for_traj(tid, cfg.test_ratio, cfg.split_seed))
        for tid, p in all_trajs if tid not in already_done
    ]
    n_cal  = sum(1 for _, _, r in todo if r == 'calibration')
    n_test = sum(1 for _, _, r in todo if r == 'test')
    logger.info(
        f"Total: {len(all_trajs):,} | already done: {len(already_done):,} | "
        f"to process: {len(todo):,} (cal={n_cal:,} test={n_test:,})"
    )

    n_ok = n_fail = 0

    stage_label = 'stage1_rrf' if stage1_mode else 'stage2_dtw'
    with tqdm(total=len(todo), unit='traj', desc=f'Calibrating [{cfg.calibration_tag}] {stage_label}') as pbar:
        for batch_start in range(0, len(todo), batch_size):
            batch = todo[batch_start: batch_start + batch_size]
            tasks = [
                process_trajectory_bundle(
                    traj_id=tid, p_actual_traj=p, split_role=role,
                    pool=pool, cfg=cfg, stage1_mode=stage1_mode,
                    own_segment_ids=traj_to_seg_ids.get(tid, []),
                    segment_actuals=segment_actuals,
                    include_tags=include_tags,
                )
                for tid, p, role in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            buffer: List[Dict[str, Any]] = []
            for res in results:
                if res is None:
                    n_fail += 1
                    continue
                buffer.extend(res.get('segment_rows') or [])
                buffer.extend(res.get('traj_rows') or [])
                n_ok += 1

            async with pool.acquire() as conn:
                if buffer:
                    await insert_calibration_batch(conn, buffer)

            pbar.update(len(batch))
            pbar.set_postfix(ok=n_ok, fail=n_fail)

    logger.info(f"Done. ok={n_ok:,} fail={n_fail:,}")

    # Compute and store quantiles — each (strategy, stage) has its own config_hash
    cfg_s1_direct   = cfg.with_stage(1).with_strategy('direct')
    cfg_s1_decomp   = cfg.with_stage(1).with_strategy('decomposed')
    cfg_s2_decomp   = cfg.with_strategy('decomposed')   # stage2, cfg already has stage=2
    cfg_s2_direct   = cfg.with_strategy('direct')

    async with pool.acquire() as conn:
        # Stage 1: direct (traj) + decomposed (seg + traj)
        await compute_and_store_quantiles(conn, cfg_s1_direct,  coverages, 'trajectory', 1)
        await compute_and_store_quantiles(conn, cfg_s1_decomp,  coverages, 'segment',    1)
        await compute_and_store_quantiles(conn, cfg_s1_decomp,  coverages, 'trajectory', 1)

        if not stage1_mode:
            # Stage 2: decomposed (seg + traj) + direct (traj)
            await compute_and_store_quantiles(conn, cfg_s2_decomp, coverages, 'segment',    2)
            await compute_and_store_quantiles(conn, cfg_s2_decomp, coverages, 'trajectory', 2)
            await compute_and_store_quantiles(conn, cfg_s2_direct,  coverages, 'trajectory', 2)


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(description='Conformal calibration builder')
    parser.add_argument('--k',             type=int,   default=10)
    parser.add_argument('--batch',         type=int,   default=10)
    parser.add_argument('--limit',         type=int,   default=None)
    parser.add_argument('--metric',        type=str,   default='sidtw', choices=sorted(ALLOWED_METRICS))
    parser.add_argument('--dtw-mode',      type=str,   default='position', choices=['position', 'joint'],
                        help='DTW mode for Stage 2 (ignored for --stage1)')
    parser.add_argument('--search-modes',  nargs='+',  default=DEFAULT_SEARCH_MODES)
    parser.add_argument('--sigma-floor',   type=float, default=0.005)
    parser.add_argument('--test-ratio',    type=float, default=0.2)
    parser.add_argument('--split-seed',    type=int,   default=42)
    parser.add_argument('--coverage',      type=float, nargs='+', default=[0.80, 0.90, 0.95])
    parser.add_argument('--tag',           type=str,   default='all',
                        help='Calibration tag, e.g. "all", "bandit_v1"')
    parser.add_argument('--include-tags',  nargs='+',  default=None,
                        help='Only calibrate on trajectories with these DB tags')
    parser.add_argument('--all-tags',      action='store_true', default=False,
                        help='Run calibration for every tag found in motion.tag_info')
    parser.add_argument('--stage1',        action='store_true', default=False,
                        help='Calibrate Stage 1 (RRF, no DTW). Default: Stage 2 (DTW).')
    parser.add_argument('--resume',        action='store_true', default=True)
    parser.add_argument('--full-rebuild',  action='store_true', default=False)
    args = parser.parse_args()

    stage1_mode  = args.stage1
    dtw_mode_val = 'none' if stage1_mode else validate_dtw_mode(args.dtw_mode)

    base_config = CalibrationConfig(
        k=args.k,
        dtw_mode=dtw_mode_val,
        metric=validate_metric(args.metric),
        search_modes=tuple(sorted(args.search_modes)),
        retrieval_strategy='direct' if stage1_mode else 'decomposed',
        calibration_tag=args.tag,
        config_stage=1 if stage1_mode else 2,
        sigma_floor=float(args.sigma_floor),
        test_ratio=float(args.test_ratio),
        split_seed=int(args.split_seed),
    )

    resume = args.resume and not args.full_rebuild
    pool   = await create_pool(DATABASE_URL)

    try:
        if args.all_tags:
            async with pool.acquire() as conn:
                all_tags = await get_all_tags(conn)
            logger.info(f"--all-tags: found {len(all_tags)} tags: {all_tags}")

            for i, tag in enumerate(all_tags, 1):
                logger.info(f"=== [{i}/{len(all_tags)}] tag='{tag}' ===")
                tag_cfg = replace(base_config, calibration_tag=tag)
                await run_calibration(
                    pool=pool, cfg=tag_cfg, stage1_mode=stage1_mode,
                    batch_size=args.batch, resume=resume,
                    max_trajectories=args.limit, coverages=args.coverage,
                    include_tags=[tag],
                )
        else:
            logger.info(
                f"Starting calibration — tag='{args.tag}' "
                f"stage={'1 (RRF)' if stage1_mode else '2 (DTW)'}"
            )
            await run_calibration(
                pool=pool, cfg=base_config, stage1_mode=stage1_mode,
                batch_size=args.batch, resume=resume,
                max_trajectories=args.limit, coverages=args.coverage,
                include_tags=args.include_tags,
            )
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())