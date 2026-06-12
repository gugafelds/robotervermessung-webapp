"""
calibration_set_builder.py
==========================
Offline script to compute the Conformal Prediction calibration set
for the trajectory performance prediction framework.

For each segment in the database:
  1. Run LOO similarity search (exclude self) → Top-K neighbors via Stage 2 (DTW)
  2. Compute LOO prediction p̂_i  (length-weighted, inverse-DTW)
  3. Compute local spread σ_i     (d_min × std of neighbor performance values)
  4. Compute nonconformity score  α_i = |p_i - p̂_i| / (σ_i + ε)
  5. Store everything in evaluation.confidence_calibration

The stored calibration set is then used online to produce valid
prediction intervals:
    interval = [p̂ ± q · σ(x_new)]
where q is the (1-α)-quantile of the stored α_i values.

Usage
-----
    python calibration_set_builder.py [--k 10] [--batch 100] [--coverage 0.90]

Requirements
------------
    pip install asyncpg numpy tqdm --break-system-packages
"""

import asyncio
import argparse
import logging
import math
import json
import os
import sys
import numpy as np
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
# Adjust this to point at your backend app folder so imports work
sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', '..', 'app')
)

import asyncpg
from utils.multimodal_framework.dtw_reranker import rerank
from utils.metadata_embeddings.trajectory_loader import TrajectoryLoader
from utils.multimodal_framework.multi_modal_searcher import MultiModalSearcher

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost/dbname'
)

# ── Constants ─────────────────────────────────────────────────────────────────
EPSILON        = 1e-6   # avoid division by zero in σ and weighting
DTW_MODE       = 'position'   # 'position' | 'joint'  — matches paper best result
METRIC         = 'sidtw'      # performance metric stored in evaluation schema
SEARCH_MODES   = ['position', 'joint', 'orientation', 'velocity', 'metadata']


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


async def ensure_calibration_table(conn: asyncpg.Connection) -> None:
    """Create evaluation.confidence_calibration if it doesn't exist yet."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation.confidence_calibration (
            seg_id              TEXT        PRIMARY KEY,
            traj_id             TEXT        NOT NULL,

            -- LOO prediction
            p_actual            FLOAT       NOT NULL,   -- measured mean_distance
            p_predicted         FLOAT       NOT NULL,   -- LOO weighted prediction
            prediction_error    FLOAT       NOT NULL,   -- |p_actual - p_predicted|

            -- Local spread
            d_min               FLOAT       NOT NULL,   -- min DTW distance among neighbors
            perf_std            FLOAT       NOT NULL,   -- std of neighbor mean_distances
            sigma               FLOAT       NOT NULL,   -- d_min * perf_std  (normalizer)

            -- Nonconformity score
            alpha               FLOAT       NOT NULL,   -- prediction_error / (sigma + eps)

            -- Metadata for diagnostics
            k_neighbors         INT         NOT NULL,   -- actual number of valid neighbors
            neighbor_ids        TEXT[]      NOT NULL,   -- seg_ids of neighbors used
            computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Config snapshot (so you know which run produced this row)
            config_k            INT         NOT NULL,
            config_dtw_mode     TEXT        NOT NULL,
            config_metric       TEXT        NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cc_traj_id
            ON evaluation.confidence_calibration (traj_id);
        CREATE INDEX IF NOT EXISTS idx_cc_alpha
            ON evaluation.confidence_calibration (alpha);
    """)
    logger.info("Table evaluation.confidence_calibration ready.")


async def get_all_seg_ids(conn, metric, limit=None):
    rows = await conn.fetch(f"""
        SELECT
            m.seg_id,
            m.traj_id,
            ei.{metric}_average_distance AS mean_distance
        FROM motion.traj_metadata m
        JOIN evaluation.{metric}_info ei ON m.seg_id = ei.seg_id
        WHERE m.seg_id != m.traj_id
          AND ei.{metric}_average_distance IS NOT NULL
        ORDER BY m.seg_id
        {'LIMIT $1' if limit else ''}
    """, *([limit] if limit else []))
    return [(r['seg_id'], r['traj_id'], float(r['mean_distance'])) for r in rows]


async def get_already_computed(conn: asyncpg.Connection) -> set:
    """Return set of seg_ids already in the calibration table."""
    rows = await conn.fetch(
        "SELECT seg_id FROM evaluation.confidence_calibration"
    )
    return {r['seg_id'] for r in rows}


# ═════════════════════════════════════════════════════════════════════════════
# Core computation
# ═════════════════════════════════════════════════════════════════════════════

def compute_loo_prediction(
    neighbors: List[Dict],
) -> Tuple[float, float, float, List[str]]:
    """
    Given a list of neighbor dicts (each with 'dtw_distance' and
    'mean_distance'), compute:

    Returns
    -------
    p_hat    : inverse-DTW weighted prediction
    d_min    : minimum DTW distance
    perf_std : std of neighbor performance values (unweighted)
    ids      : list of seg_ids used
    """
    # Filter out neighbors without both fields
    valid = [
        n for n in neighbors
        if n.get('dtw_distance') is not None
        and n.get('mean_distance') is not None
    ]

    if len(valid) < 2:
        return None, None, None, []

    dtw_dists   = np.array([n['dtw_distance']  for n in valid], dtype=float)
    perf_values = np.array([n['mean_distance'] for n in valid], dtype=float)
    ids         = [n['seg_id'] for n in valid]

    # Inverse-DTW weights (Eq. 3 in paper)
    weights  = 1.0 / (dtw_dists + EPSILON)
    p_hat    = float(np.dot(weights, perf_values) / weights.sum())

    d_min    = float(dtw_dists.min())
    perf_std = float(perf_values.std())

    return p_hat, d_min, perf_std, ids


async def process_segment(
    seg_id: str,
    traj_id: str,
    p_actual: float,
    pool: asyncpg.Pool,
    k: int,
) -> Optional[Dict]:
    """
    Run LOO similarity search for one segment and compute its
    nonconformity score α.

    Returns a dict ready to INSERT, or None on failure.
    """
    try:
        async with pool.acquire() as conn:
            searcher = MultiModalSearcher(conn)

            # Stage 1: embedding search, exclude self
            search_result = await searcher.search_similar(
                target_id=seg_id,
                modes=SEARCH_MODES,
                limit=k,
                metric=METRIC,
                exclude_ids=[seg_id],   # LOO: exclude itself
            )

            # Extract segment-level results for this seg_id
            seg_results_raw = []
            for group in search_result.get('segment_similarity', []):
                if group.get('target_segment') == seg_id:
                    seg_results_raw = group.get('similar_segments', {}).get('results', [])
                    break

            if not seg_results_raw:
                logger.debug(f"No Stage 1 results for {seg_id}, skipping.")
                return None

            # Stage 2: DTW reranking
            loader = TrajectoryLoader(conn)
            query_data = await loader.load_trajectory_data(seg_id, mode=DTW_MODE)
            if query_data is None:
                return None

            query_arr = query_data['segments'].get(seg_id)
            if query_arr is None or len(query_arr) == 0:
                return None

            # Build candidate arrays
            cand_seg_ids = [r['seg_id'] for r in seg_results_raw]
            cand_traj_ids = list({r.get('traj_id', r['seg_id']) for r in seg_results_raw})

            cand_data_map: Dict[str, np.ndarray] = {}
            for cand_traj_id in cand_traj_ids:
                traj_data = await loader.load_trajectory_data(cand_traj_id, mode=DTW_MODE)
                if traj_data:
                    for s_id, arr in traj_data['segments'].items():
                        if s_id in cand_seg_ids:
                            cand_data_map[s_id] = arr

            if not cand_data_map:
                return None

            dtw_results = rerank(
                query_seq=query_arr,
                candidates=cand_data_map,
                limit=k,
                mode=DTW_MODE,
            )

            # Build lookup: seg_id → dtw_distance
            dtw_lookup = {r['id']: r['dtw_distance'] for r in dtw_results}

            # Enrich Stage 1 results with DTW distances + performance values
            enriched = []
            for r in seg_results_raw:
                sid = r['seg_id']
                dtw_dist = dtw_lookup.get(sid)
                mean_dist = r.get('features', {}).get('mean_distance') if r.get('features') else None
                if dtw_dist is not None and mean_dist is not None:
                    enriched.append({
                        'seg_id':       sid,
                        'dtw_distance': dtw_dist,
                        'mean_distance': mean_dist,
                    })

            if len(enriched) < 2:
                logger.debug(f"Not enough enriched neighbors for {seg_id}")
                return None

            # Sort by DTW distance ascending (best first)
            enriched.sort(key=lambda x: x['dtw_distance'])

        # Compute LOO prediction and nonconformity score
        p_hat, d_min, perf_std, neighbor_ids = compute_loo_prediction(enriched)

        if p_hat is None:
            return None

        prediction_error = abs(p_actual - p_hat)
        sigma            = d_min * perf_std           # local spread normalizer
        alpha            = prediction_error / (sigma + EPSILON)

        return {
            'seg_id':           seg_id,
            'traj_id':          traj_id,
            'p_actual':         p_actual,
            'p_predicted':      p_hat,
            'prediction_error': prediction_error,
            'd_min':            d_min,
            'perf_std':         perf_std,
            'sigma':            sigma,
            'alpha':            alpha,
            'k_neighbors':      len(enriched),
            'neighbor_ids':     neighbor_ids,
            'config_k':         k,
            'config_dtw_mode':  DTW_MODE,
            'config_metric':    METRIC,
        }

    except Exception as e:
        logger.warning(f"Failed for {seg_id}: {e}")
        return None


async def insert_batch(conn: asyncpg.Connection, batch: List[Dict]) -> None:
    """Bulk upsert a batch of calibration rows."""
    await conn.executemany("""
        INSERT INTO evaluation.confidence_calibration (
            seg_id, traj_id,
            p_actual, p_predicted, prediction_error,
            d_min, perf_std, sigma, alpha,
            k_neighbors, neighbor_ids,
            config_k, config_dtw_mode, config_metric
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
        )
        ON CONFLICT (seg_id) DO UPDATE SET
            p_actual         = EXCLUDED.p_actual,
            p_predicted      = EXCLUDED.p_predicted,
            prediction_error = EXCLUDED.prediction_error,
            d_min            = EXCLUDED.d_min,
            perf_std         = EXCLUDED.perf_std,
            sigma            = EXCLUDED.sigma,
            alpha            = EXCLUDED.alpha,
            k_neighbors      = EXCLUDED.k_neighbors,
            neighbor_ids     = EXCLUDED.neighbor_ids,
            computed_at      = NOW(),
            config_k         = EXCLUDED.config_k,
            config_dtw_mode  = EXCLUDED.config_dtw_mode,
            config_metric    = EXCLUDED.config_metric
    """, [
        (
            r['seg_id'], r['traj_id'],
            r['p_actual'], r['p_predicted'], r['prediction_error'],
            r['d_min'], r['perf_std'], r['sigma'], r['alpha'],
            r['k_neighbors'], r['neighbor_ids'],
            r['config_k'], r['config_dtw_mode'], r['config_metric'],
        )
        for r in batch
    ])


async def compute_and_store_quantiles(conn: asyncpg.Connection) -> None:
    """
    After the full calibration run, compute and log coverage quantiles.
    Also stores a summary row in a small metadata table.
    """
    rows = await conn.fetch("""
        SELECT
            percentile_cont(0.80) WITHIN GROUP (ORDER BY alpha) AS q80,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY alpha) AS q90,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY alpha) AS q95,
            avg(prediction_error)                                AS mae,
            stddev(prediction_error)                             AS std_err,
            count(*)                                             AS n
        FROM evaluation.confidence_calibration
        WHERE config_dtw_mode = $1
          AND config_metric   = $2
    """, DTW_MODE, METRIC)

    if not rows or rows[0]['n'] == 0:
        logger.warning("No rows found to compute quantiles.")
        return

    r = rows[0]
    logger.info("=" * 60)
    logger.info(f"Calibration complete  (n={r['n']:,})")
    logger.info(f"  MAE  prediction error : {r['mae']:.4f} mm")
    logger.info(f"  Std  prediction error : {r['std_err']:.4f} mm")
    logger.info(f"  q80 (80% coverage)    : α = {r['q80']:.4f}")
    logger.info(f"  q90 (90% coverage)    : α = {r['q90']:.4f}")
    logger.info(f"  q95 (95% coverage)    : α = {r['q95']:.4f}")
    logger.info("=" * 60)
    logger.info(
        "Online usage:\n"
        "  σ(x)     = d_min(x) * std(neighbor_perf)\n"
        "  interval = p̂ ± q90 * σ(x)\n"
        f"  → q90 = {r['q90']:.4f}"
    )

    # Upsert metadata table so the online service can read q without
    # querying all rows every time.
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation.confidence_quantiles (
            id              SERIAL      PRIMARY KEY,
            dtw_mode        TEXT        NOT NULL,
            metric          TEXT        NOT NULL,
            coverage        FLOAT       NOT NULL,
            quantile_value  FLOAT       NOT NULL,
            n_calibration   INT         NOT NULL,
            mae             FLOAT,
            computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (dtw_mode, metric, coverage)
        );
    """)

    for coverage, q_val in [
        (0.80, float(r['q80'])),
        (0.90, float(r['q90'])),
        (0.95, float(r['q95'])),
    ]:
        await conn.execute("""
            INSERT INTO evaluation.confidence_quantiles
                (dtw_mode, metric, coverage, quantile_value, n_calibration, mae)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (dtw_mode, metric, coverage) DO UPDATE SET
                quantile_value = EXCLUDED.quantile_value,
                n_calibration  = EXCLUDED.n_calibration,
                mae            = EXCLUDED.mae,
                computed_at    = NOW()
        """, DTW_MODE, METRIC, coverage, q_val, int(r['n']), float(r['mae']))

    logger.info("Quantiles saved to evaluation.confidence_quantiles.")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

async def main(k: int, batch_size: int, resume: bool) -> None:
    logger.info(f"Starting calibration build  k={k}  batch={batch_size}")

    pool = await create_pool(DATABASE_URL)

    try:
        async with pool.acquire() as conn:
            await ensure_calibration_table(conn)
            all_segments = await get_all_seg_ids(conn, METRIC)
            already_done = await get_already_computed(conn) if resume else set()

        logger.info(f"Total segments with performance data : {len(all_segments):,}")
        logger.info(f"Already computed (resume mode)       : {len(already_done):,}")

        todo = [
            (seg_id, traj_id, p_actual)
            for seg_id, traj_id, p_actual in all_segments
            if seg_id not in already_done
        ]
        logger.info(f"Segments to process                  : {len(todo):,}")

        if not todo:
            logger.info("Nothing to do — calibration set is up to date.")
            async with pool.acquire() as conn:
                await compute_and_store_quantiles(conn)
            return

        # Process in batches with concurrency
        # We process batch_size segments concurrently.  Keep this moderate
        # (50–100) to avoid saturating the DB connection pool.
        results_buffer: List[Dict] = []
        n_ok = 0
        n_fail = 0

        with tqdm(total=len(todo), unit='seg', desc='Calibrating') as pbar:
            for batch_start in range(0, len(todo), batch_size):
                batch = todo[batch_start : batch_start + batch_size]

                tasks = [
                    process_segment(seg_id, traj_id, p_actual, pool, k)
                    for seg_id, traj_id, p_actual in batch
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=False)

                for res in batch_results:
                    if res is not None:
                        results_buffer.append(res)
                        n_ok += 1
                    else:
                        n_fail += 1

                # Flush to DB every batch
                if results_buffer:
                    async with pool.acquire() as conn:
                        await insert_batch(conn, results_buffer)
                    results_buffer.clear()

                pbar.update(len(batch))
                pbar.set_postfix(ok=n_ok, fail=n_fail)

        logger.info(f"Done.  ok={n_ok:,}  failed/skipped={n_fail:,}")

        # Compute and store quantiles
        async with pool.acquire() as conn:
            await compute_and_store_quantiles(conn)

    finally:
        await pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Build conformal prediction calibration set.'
    )
    parser.add_argument(
        '--k', type=int, default=10,
        help='Number of LOO neighbors for Stage 2 (default: 10, paper optimum)'
    )
    parser.add_argument(
        '--batch', type=int, default=50,
        help='Concurrent segments per batch (default: 50)'
    )
    parser.add_argument(
        '--resume', action='store_true', default=True,
        help='Skip segments already in the calibration table (default: True)'
    )
    parser.add_argument(
        '--full-rebuild', action='store_true', default=False,
        help='Ignore existing rows and recompute everything'
    )
    args = parser.parse_args()

    resume = args.resume and not args.full_rebuild

    asyncio.run(main(k=args.k, batch_size=args.batch, resume=resume))