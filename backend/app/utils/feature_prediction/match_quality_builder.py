"""
match_quality_builder.py
=========================
Builds prognosis.confidence_match_quality (empirical match-quality
buckets: d_min_per_path_length -> typical prediction_error), from the
existing confidence_calibration_seg/traj tables.

Complements calibration_set_builder.py's conformal quantiles with a
descriptive (non-guaranteed) match-quality signal — see quality_match.py
for the online lookup side.

Why no validation step?
-----------------------
Match quality is a purely descriptive signal: "matches like this one
historically had this error." It carries no statistical coverage
guarantee — that role belongs to the conformal quantiles in
confidence_quantiles (built by calibration_set_builder.py).
A reliability-diagram validation against the test split would only make
sense if we were asserting a guarantee, which we are not.  Bucket
stability can be judged directly from n_samples per bucket in the table.

Buckets are built on ALL rows regardless of split_role — both
'calibration' and 'test' rows are included.  Unlike conformal quantiles
(which need a held-out test split for coverage guarantees), match quality
is a purely descriptive signal with no guarantee to invalidate.  Using
all available data produces more stable bucket boundaries and higher
n_samples per bucket, which is especially important for small tags.

Usage
-----
  # Build for every tag found in confidence_calibration_seg/traj:
  python match_quality_builder.py

  # Build for a specific tag only:
  python match_quality_builder.py --tag bandit_v1

  # Build for every tag listed in motion.tag_info (mirrors --all-tags
  # in calibration_set_builder.py):
  python match_quality_builder.py --all-tags

  # Custom bucket count:
  python match_quality_builder.py --n-buckets 8

Run this script once after every calibration_set_builder.py run,
using the same --tag (or --all-tags) you used there.
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
            config_stage        INT         NOT NULL DEFAULT 2,
            bucket              INT         NOT NULL CHECK (bucket >= 1),
            n_buckets           INT         NOT NULL DEFAULT 10,

            d_min_lower         FLOAT       NOT NULL,
            d_min_upper         FLOAT       NOT NULL,

            mean_error          FLOAT       NOT NULL,
            median_error        FLOAT       NOT NULL,
            std_error           FLOAT,
            n_samples           INT         NOT NULL,

            config_hash         TEXT        NOT NULL,
            computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE (metric, dtw_mode, retrieval_strategy, level,
                    config_k, search_modes, calibration_tag, bucket, config_stage)
        );

        ALTER TABLE {SCHEMA}.confidence_match_quality
            ADD COLUMN IF NOT EXISTS config_stage INT NOT NULL DEFAULT 2;

        CREATE INDEX IF NOT EXISTS idx_cmq_lookup
            ON {SCHEMA}.confidence_match_quality
            (metric, dtw_mode, retrieval_strategy, level, config_k, search_modes, calibration_tag, config_stage);
    """)
    logger.info("confidence_match_quality table ready.")


# ═════════════════════════════════════════════════════════════════════════════
# Tag discovery
# ═════════════════════════════════════════════════════════════════════════════

async def get_all_tags_from_motion(conn: asyncpg.Connection) -> List[str]:
    """Return every tag from motion.tag_info — mirrors calibration_set_builder behaviour."""
    rows = await conn.fetch("SELECT tag FROM motion.tag_info ORDER BY tag")
    return [r['tag'] for r in rows]


async def get_distinct_tags_from_calibration(conn: asyncpg.Connection) -> List[str]:
    """
    Return every calibration_tag that actually has data in the calibration
    tables (split_role='calibration').  Used when neither --tag nor
    --all-tags is given so we process whatever is present.
    """
    rows = await conn.fetch(f"""
        SELECT DISTINCT calibration_tag
        FROM (
            SELECT calibration_tag FROM {SCHEMA}.confidence_calibration_seg
            UNION
            SELECT calibration_tag FROM {SCHEMA}.confidence_calibration_traj
        ) t
        ORDER BY calibration_tag
    """)
    return [r['calibration_tag'] for r in rows]


# ═════════════════════════════════════════════════════════════════════════════
# Bucket computation — uses ALL rows (calibration + test)
# ═════════════════════════════════════════════════════════════════════════════

async def build_buckets_for_level(
    conn:       asyncpg.Connection,
    level:      str,            # 'segment' | 'trajectory'
    n_buckets:  int,
    tag_filter: Optional[str] = None,
) -> int:
    """
    Build (or refresh) match-quality buckets for one level and one tag.

    All rows are used regardless of split_role — more data means more
    stable bucket boundaries and higher n_samples per bucket.

    tag_filter=None means "all tags present in the table at once" — the
    PARTITION BY already includes calibration_tag so each tag gets its own
    independent set of buckets.  Passing a specific tag restricts the rows
    and is faster when you only need to refresh one tag.
    """
    source_table = (
        f"{SCHEMA}.confidence_calibration_seg"
        if level == 'segment'
        else f"{SCHEMA}.confidence_calibration_traj"
    )

    tag_clause = "AND calibration_tag = $2" if tag_filter else ""
    params: List = [n_buckets]
    if tag_filter:
        params.append(tag_filter)

    rows = await conn.fetch(f"""
        WITH ranked AS (
            SELECT
                config_hash,
                config_metric   AS metric,
                config_dtw_mode AS dtw_mode,
                config_k,
                search_modes,
                calibration_tag,
                config_stage,
                retrieval_strategy,
                d_min_per_path_length,
                prediction_error,
                NTILE($1) OVER (
                    PARTITION BY config_metric, config_dtw_mode, retrieval_strategy,
                                 config_k, search_modes, calibration_tag, config_stage
                    ORDER BY d_min_per_path_length
                ) AS bucket
            FROM {source_table}
            WHERE d_min_per_path_length IS NOT NULL
              {tag_clause}
        )
        SELECT
            (array_agg(config_hash))[1] AS config_hash,
            metric, dtw_mode, config_k, search_modes, calibration_tag,
            config_stage, retrieval_strategy,
            bucket,
            MIN(d_min_per_path_length) AS d_min_lower,
            MAX(d_min_per_path_length) AS d_min_upper,
            AVG(prediction_error)      AS mean_error,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prediction_error) AS median_error,
            STDDEV(prediction_error)   AS std_error,
            COUNT(*)                   AS n_samples
        FROM ranked
        GROUP BY metric, dtw_mode, config_k, search_modes, calibration_tag,
                 config_stage, retrieval_strategy, bucket
    """, *params)

    if not rows:
        logger.warning(
            f"No rows found for level='{level}'"
            + (f", tag='{tag_filter}'" if tag_filter else "")
            + " — skipping."
        )
        return 0

    await conn.executemany(f"""
        INSERT INTO {SCHEMA}.confidence_match_quality (
            metric, dtw_mode, retrieval_strategy, level, config_k, search_modes,
            calibration_tag, config_stage, bucket, n_buckets,
            d_min_lower, d_min_upper, mean_error, median_error, std_error, n_samples,
            config_hash
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17
        )
        ON CONFLICT (metric, dtw_mode, retrieval_strategy, level,
                     config_k, search_modes, calibration_tag, bucket, config_stage)
        DO UPDATE SET
            d_min_lower  = EXCLUDED.d_min_lower,
            d_min_upper  = EXCLUDED.d_min_upper,
            mean_error   = EXCLUDED.mean_error,
            median_error = EXCLUDED.median_error,
            std_error    = EXCLUDED.std_error,
            n_samples    = EXCLUDED.n_samples,
            config_hash  = EXCLUDED.config_hash,
            computed_at  = NOW()
    """, [
        (
            r['metric'], r['dtw_mode'], r['retrieval_strategy'], level, r['config_k'],
            r['search_modes'], r['calibration_tag'], r['config_stage'], r['bucket'], n_buckets,
            r['d_min_lower'], r['d_min_upper'], r['mean_error'], r['median_error'],
            r['std_error'], r['n_samples'], r['config_hash'],
        )
        for r in rows
    ])

    # Log a brief summary per tag so it's easy to spot thin buckets.
    tags_seen = sorted({r['calibration_tag'] for r in rows})
    for tag in tags_seen:
        tag_rows  = [r for r in rows if r['calibration_tag'] == tag]
        min_n     = min(r['n_samples'] for r in tag_rows)
        total_n   = sum(r['n_samples'] for r in tag_rows)
        strategies = sorted({r['retrieval_strategy'] for r in tag_rows})
        logger.info(
            f"  level='{level}' tag='{tag}' strategies={strategies} "
            f"buckets={len(tag_rows)} total_samples={total_n} min_per_bucket={min_n}"
            + (" ⚠ thin buckets — consider fewer --n-buckets" if min_n < 30 else "")
        )

    logger.info(f"level='{level}': wrote {len(rows)} bucket rows.")
    return len(rows)


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Match-quality bucket builder. '
            'Run after every calibration_set_builder.py invocation '
            'using the same --tag / --all-tags.'
        )
    )
    parser.add_argument(
        '--n-buckets', type=int, default=10,
        help='Number of NTILE buckets (default: 10)',
    )
    parser.add_argument(
        '--tag', type=str, default=None,
        help=(
            'Build buckets for this calibration_tag only '
            '(e.g. "bandit_v1").  '
            'Omit to process every tag present in the calibration tables.'
        ),
    )
    parser.add_argument(
        '--all-tags', action='store_true', default=False,
        help=(
            'Build buckets for every tag in motion.tag_info '
            '(mirrors --all-tags in calibration_set_builder.py). '
            'Tags with no calibration data are silently skipped.'
        ),
    )
    args = parser.parse_args()

    pool = await asyncpg.create_pool(DATABASE_URL)
    try:
        async with pool.acquire() as conn:
            await ensure_match_quality_table(conn)

            # ── Determine which tags to process ──────────────────────────
            if args.tag:
                tags_to_process = [args.tag]
                logger.info(f"Building buckets for tag='{args.tag}'")
            elif args.all_tags:
                tags_to_process = await get_all_tags_from_motion(conn)
                logger.info(
                    f"--all-tags: found {len(tags_to_process)} tags in motion.tag_info: "
                    f"{tags_to_process}"
                )
            else:
                # Default: whatever is actually present in the calibration tables.
                tags_to_process = await get_distinct_tags_from_calibration(conn)
                logger.info(
                    f"No --tag / --all-tags given — processing {len(tags_to_process)} "
                    f"tag(s) found in calibration tables: {tags_to_process}"
                )

            if not tags_to_process:
                logger.warning(
                    "No tags found. Run calibration_set_builder.py first, "
                    "then re-run this script."
                )
                return

            # ── Build buckets per tag ─────────────────────────────────────
            total_seg = total_traj = 0
            for i, tag in enumerate(tags_to_process, 1):
                logger.info(f"=== [{i}/{len(tags_to_process)}] tag='{tag}' ===")
                n_seg  = await build_buckets_for_level(conn, 'segment',    args.n_buckets, tag)
                n_traj = await build_buckets_for_level(conn, 'trajectory', args.n_buckets, tag)
                total_seg  += n_seg
                total_traj += n_traj

            logger.info(
                f"Done — segment bucket rows: {total_seg}, "
                f"trajectory bucket rows: {total_traj}"
            )
    finally:
        await pool.close()


if __name__ == '__main__':
    asyncio.run(main())