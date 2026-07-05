"""
match_quality_builder.py
=========================
Builds prognosis.confidence_match_quality (empirical match-quality
buckets: d_min_per_path_length -> typical prediction_error), from the
existing confidence_calibration_seg/traj tables.

Complements calibration_set_builder.py's conformal quantiles with a
descriptive (non-guaranteed) match-quality signal — see quality_match.py
for the online lookup side.

Buckets are built ONLY on split_role='calibration' rows and validated
against split_role='test' rows — never on the same data (reliability
diagram / calibration-curve best practice: never validate on the data
used to build the bins). Validation results are persisted so quality
can be tracked across rebuilds.

Usage
-----
  python match_quality_builder.py
  python match_quality_builder.py --n-buckets 8 --tag bandit_v1
  python match_quality_builder.py --validate
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
SCHEMA       = 'prognosis'


# ═════════════════════════════════════════════════════════════════════════════
# Table setup
# ═════════════════════════════════════════════════════════════════════════════

async def ensure_match_quality_table(conn: asyncpg.Connection) -> None:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.confidence_match_quality (
            id                  SERIAL      PRIMARY KEY,

            metric              TEXT        NOT NULL,
            dtw_mode            TEXT        NOT NULL,
            retrieval_strategy  TEXT        NOT NULL DEFAULT 'decomposed',
            level               TEXT        NOT NULL CHECK (level IN ('segment', 'trajectory')),
            config_k            INT         NOT NULL,
            search_modes        TEXT        NOT NULL,
            calibration_tag     TEXT        NOT NULL DEFAULT 'all',
            bucket              INT         NOT NULL CHECK (bucket >= 1),
            n_buckets           INT         NOT NULL DEFAULT 10,

            d_min_lower         FLOAT       NOT NULL,
            d_min_upper         FLOAT       NOT NULL,

            mean_error          FLOAT       NOT NULL,
            median_error        FLOAT       NOT NULL,
            std_error           FLOAT,
            n_samples           INT         NOT NULL,

            config_hash         TEXT        NOT NULL,
            config               JSONB       NOT NULL,
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (metric, dtw_mode, retrieval_strategy, level,
                    config_k, search_modes, calibration_tag, bucket)
        );

        CREATE INDEX IF NOT EXISTS idx_cmq_lookup
            ON {SCHEMA}.confidence_match_quality
            (metric, dtw_mode, retrieval_strategy, level, config_k, search_modes, calibration_tag);
    """)
    logger.info("confidence_match_quality table ready.")


async def ensure_validation_table(conn: asyncpg.Connection) -> None:
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.confidence_match_quality_validation (
            id                     SERIAL      PRIMARY KEY,

            metric                 TEXT        NOT NULL,
            dtw_mode               TEXT        NOT NULL,
            retrieval_strategy     TEXT        NOT NULL,
            level                  TEXT        NOT NULL CHECK (level IN ('segment', 'trajectory')),
            config_k               INT         NOT NULL,
            search_modes           TEXT        NOT NULL,
            calibration_tag        TEXT        NOT NULL,
            bucket                 INT         NOT NULL,

            bucket_predicted_error FLOAT       NOT NULL,
            test_actual_error      FLOAT       NOT NULL,
            error_delta            FLOAT       NOT NULL,
            n_test                 INT         NOT NULL,

            validated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (metric, dtw_mode, retrieval_strategy, level,
                    config_k, search_modes, calibration_tag, bucket, validated_at)
        );
    """)
    logger.info("confidence_match_quality_validation table ready.")


# ═════════════════════════════════════════════════════════════════════════════
# Bucket computation — built ONLY on split_role='calibration'
# ═════════════════════════════════════════════════════════════════════════════

async def build_buckets_for_level(
    conn:      asyncpg.Connection,
    level:     str,           # 'segment' | 'trajectory'
    n_buckets: int,
    tag_filter: Optional[str] = None,
) -> int:
    source_table = f"{SCHEMA}.confidence_calibration_seg" if level == 'segment' \
        else f"{SCHEMA}.confidence_calibration_traj"

    tag_clause = "AND calibration_tag = $2" if tag_filter else ""
    params: List = [n_buckets]
    if tag_filter:
        params.append(tag_filter)

    rows = await conn.fetch(f"""
        WITH ranked AS (
            SELECT
                config_hash, config,
                config_metric   AS metric,
                config_dtw_mode AS dtw_mode,
                config_k,
                search_modes,
                calibration_tag,
                retrieval_strategy,
                d_min_per_path_length,
                prediction_error,
                NTILE($1) OVER (
                    PARTITION BY config_metric, config_dtw_mode, retrieval_strategy,
                                 config_k, search_modes, calibration_tag
                    ORDER BY d_min_per_path_length
                ) AS bucket
            FROM {source_table}
            WHERE split_role = 'calibration'
              AND d_min_per_path_length IS NOT NULL
              {tag_clause}
        )
        SELECT
            (array_agg(config_hash))[1] AS config_hash,
            (array_agg(config))[1]      AS config,
            metric, dtw_mode, config_k, search_modes, calibration_tag,
            retrieval_strategy,
            bucket,
            MIN(d_min_per_path_length) AS d_min_lower,
            MAX(d_min_per_path_length) AS d_min_upper,
            AVG(prediction_error)      AS mean_error,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prediction_error) AS median_error,
            STDDEV(prediction_error)   AS std_error,
            COUNT(*)                   AS n_samples
        FROM ranked
        GROUP BY metric, dtw_mode, config_k, search_modes, calibration_tag,
                 retrieval_strategy, bucket
    """, *params)

    if not rows:
        logger.warning(f"No calibration rows found for level='{level}' — skipping.")
        return 0

    await conn.executemany(f"""
        INSERT INTO {SCHEMA}.confidence_match_quality (
            metric, dtw_mode, retrieval_strategy, level, config_k, search_modes,
            calibration_tag, bucket, n_buckets,
            d_min_lower, d_min_upper, mean_error, median_error, std_error, n_samples,
            config_hash, config
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17
        )
        ON CONFLICT (metric, dtw_mode, retrieval_strategy, level,
                     config_k, search_modes, calibration_tag, bucket)
        DO UPDATE SET
            d_min_lower   = EXCLUDED.d_min_lower,
            d_min_upper   = EXCLUDED.d_min_upper,
            mean_error    = EXCLUDED.mean_error,
            median_error  = EXCLUDED.median_error,
            std_error     = EXCLUDED.std_error,
            n_samples     = EXCLUDED.n_samples,
            config_hash   = EXCLUDED.config_hash,
            config        = EXCLUDED.config,
            computed_at   = NOW()
    """, [
        (
            r['metric'], r['dtw_mode'], r['retrieval_strategy'], level, r['config_k'],
            r['search_modes'], r['calibration_tag'], r['bucket'], n_buckets,
            r['d_min_lower'], r['d_min_upper'], r['mean_error'], r['median_error'],
            r['std_error'], r['n_samples'], r['config_hash'], r['config'],
        )
        for r in rows
    ])

    logger.info(f"level='{level}': wrote {len(rows)} bucket rows.")
    return len(rows)


# ═════════════════════════════════════════════════════════════════════════════
# Validation — reliability-diagram style: bucket mean_error (from calibration
# split) vs. actual mean error of unseen test-split rows falling in that
# bucket's d_min range. Results are persisted, never overwritten, so quality
# can be tracked across rebuilds.
# ═════════════════════════════════════════════════════════════════════════════

async def validate_buckets_for_level(
    conn:       asyncpg.Connection,
    level:      str,
    tag_filter: Optional[str] = None,
) -> int:
    source_table = f"{SCHEMA}.confidence_calibration_seg" if level == 'segment' \
        else f"{SCHEMA}.confidence_calibration_traj"

    tag_clause = "AND t.calibration_tag = $2" if tag_filter else ""
    params: List = [level]
    if tag_filter:
        params.append(tag_filter)

    rows = await conn.fetch(f"""
        SELECT
            b.metric, b.dtw_mode, b.retrieval_strategy, b.config_k, b.search_modes,
            b.calibration_tag, b.bucket, b.mean_error AS bucket_predicted_error,
            AVG(t.prediction_error) AS test_actual_error,
            COUNT(*) AS n_test
        FROM {SCHEMA}.confidence_match_quality b
        JOIN {source_table} t
          ON  t.config_metric        = b.metric
          AND t.config_dtw_mode      = b.dtw_mode
          AND t.retrieval_strategy   = b.retrieval_strategy
          AND t.config_k             = b.config_k
          AND t.search_modes         = b.search_modes
          AND t.calibration_tag      = b.calibration_tag
          AND t.d_min_per_path_length BETWEEN b.d_min_lower AND b.d_min_upper
        WHERE b.level = $1
          AND t.split_role = 'test'
          {tag_clause}
        GROUP BY b.metric, b.dtw_mode, b.retrieval_strategy, b.config_k, b.search_modes,
                 b.calibration_tag, b.bucket, b.mean_error
        ORDER BY b.calibration_tag, b.retrieval_strategy, b.bucket
    """, *params)

    if not rows:
        logger.warning(f"No test-split rows found to validate level='{level}'.")
        return 0

    logger.info(f"── Validation ({level}) ─────────────────────────────")
    insert_values = []
    for r in rows:
        diff = r['test_actual_error'] - r['bucket_predicted_error']
        logger.info(
            f"  tag={r['calibration_tag']:<16} strategy={r['retrieval_strategy']:<10} "
            f"bucket={r['bucket']:>2}  predicted={r['bucket_predicted_error']:.4f}  "
            f"test_actual={r['test_actual_error']:.4f}  Δ={diff:+.4f}  (n={r['n_test']})"
        )
        insert_values.append((
            r['metric'], r['dtw_mode'], r['retrieval_strategy'], level, r['config_k'],
            r['search_modes'], r['calibration_tag'], r['bucket'],
            r['bucket_predicted_error'], r['test_actual_error'], diff, r['n_test'],
        ))

    await conn.executemany(f"""
        INSERT INTO {SCHEMA}.confidence_match_quality_validation (
            metric, dtw_mode, retrieval_strategy, level, config_k, search_modes,
            calibration_tag, bucket, bucket_predicted_error, test_actual_error,
            error_delta, n_test
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    """, insert_values)

    logger.info(f"Saved {len(insert_values)} validation rows for level='{level}'.")
    return len(insert_values)


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(description='Match-quality bucket builder')
    parser.add_argument('--n-buckets', type=int, default=10)
    parser.add_argument('--tag',       type=str, default=None,
                        help='Only build buckets for this calibration_tag (default: all tags present)')
    parser.add_argument('--validate',  action='store_true', default=False,
                        help='After building, validate bucket mean_error against the held-out test split')
    args = parser.parse_args()

    pool = await asyncpg.create_pool(DATABASE_URL)
    try:
        async with pool.acquire() as conn:
            await ensure_match_quality_table(conn)
            await ensure_validation_table(conn)

            n_seg  = await build_buckets_for_level(conn, 'segment',    args.n_buckets, args.tag)
            n_traj = await build_buckets_for_level(conn, 'trajectory', args.n_buckets, args.tag)
            logger.info(f"Done building — segment buckets: {n_seg}, trajectory buckets: {n_traj}")

            if args.validate:
                v_seg  = await validate_buckets_for_level(conn, 'segment',    args.tag)
                v_traj = await validate_buckets_for_level(conn, 'trajectory', args.tag)
                logger.info(f"Done validating — segment rows: {v_seg}, trajectory rows: {v_traj}")
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())