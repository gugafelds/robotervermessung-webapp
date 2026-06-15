"""
calibration_set_builder.py
==========================
Offline script to compute the Conformal Prediction calibration set
for the trajectory performance prediction framework.

For each segment in the database:
  1. Run LOO similarity search (exclude self) → Top-K neighbors via Stage 2 (DTW)
  2. Compute LOO prediction p̂_i  (inverse-DTW weighted)
  3. Compute σ_i = perf_std  (std of neighbor performance values)
  4. Compute nonconformity score α_i = |p_i - p̂_i| / (σ_i + ε)
  5. Store DTW-geometry features for later σ-model training
  6. Store everything in evaluation.confidence_calibration

DTW-geometry features stored per segment:
  d_min, d_mean, d_max, d_spread, d_rel, d_cv, perf_std, perf_cv, perf_mean

These allow us to later train a learned σ-model:
  σ(x) = f(d_min, d_spread, perf_cv, ...)
  which replaces the global quantile q with an adaptive, geometry-aware one.

Usage
-----
    python calibration_set_builder.py [--k 10] [--batch 10] [--limit 1000]
    python calibration_set_builder.py --full-rebuild

Requirements
------------
    pip install asyncpg numpy tqdm python-dotenv --break-system-packages
"""

import asyncio
import argparse
import json
import logging
import math
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

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
    'postgresql://user:password@localhost/dbname'
)

# ── Constants ─────────────────────────────────────────────────────────────────
EPSILON      = 1e-6
DTW_MODE     = 'position'
METRIC       = 'sidtw'
SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']


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
            p_actual            FLOAT       NOT NULL,
            p_predicted         FLOAT       NOT NULL,
            prediction_error    FLOAT       NOT NULL,

            -- σ = perf_std (consistent with online scorer)
            sigma               FLOAT       NOT NULL,

            -- Nonconformity score: α = prediction_error / (σ + ε)
            alpha               FLOAT       NOT NULL,

            -- DTW-geometry features for σ-model training
            dtw_features        JSONB       NOT NULL,

            -- Metadata
            k_neighbors         INT         NOT NULL,
            neighbor_ids        TEXT[]      NOT NULL,
            computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Config snapshot
            config_k            INT         NOT NULL,
            config_dtw_mode     TEXT        NOT NULL,
            config_metric       TEXT        NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_cc_traj_id
            ON evaluation.confidence_calibration (traj_id);
        CREATE INDEX IF NOT EXISTS idx_cc_alpha
            ON evaluation.confidence_calibration (alpha);
        CREATE INDEX IF NOT EXISTS idx_cc_dtw_features
            ON evaluation.confidence_calibration USING gin (dtw_features);
    """)
    logger.info("Table evaluation.confidence_calibration ready.")


async def get_all_seg_ids(
    conn: asyncpg.Connection,
    metric: str,
    max_trajectories: Optional[int] = None,
) -> List[Tuple[str, str, float]]:
    """
    Return (seg_id, traj_id, actual_mean_distance) for segments.

    If max_trajectories is set: randomly sample that many trajectories
    first, then return all their segments. This ensures representative
    sampling across the parameter space rather than always taking the
    first N segments.
    """
    if max_trajectories:
        # Random sample at trajectory level, then get all their segments
        rows = await conn.fetch(f"""
            SELECT
                m.seg_id,
                m.traj_id,
                ei.{metric}_average_distance AS mean_distance
            FROM motion.traj_metadata m
            JOIN evaluation.{metric}_info ei ON m.seg_id = ei.seg_id
            WHERE m.seg_id != m.traj_id
              AND ei.{metric}_average_distance IS NOT NULL
              AND m.traj_id = ANY(
                  SELECT traj_id
                  FROM motion.traj_metadata
                  WHERE seg_id = traj_id
                  ORDER BY RANDOM()
                  LIMIT {max_trajectories}
              )
        """)
    else:
        rows = await conn.fetch(f"""
            SELECT
                m.seg_id,
                m.traj_id,
                ei.{metric}_average_distance AS mean_distance
            FROM motion.traj_metadata m
            JOIN evaluation.{metric}_info ei ON m.seg_id = ei.seg_id
            WHERE m.seg_id != m.traj_id
              AND ei.{metric}_average_distance IS NOT NULL
        """)

    return [(r['seg_id'], r['traj_id'], float(r['mean_distance'])) for r in rows]


async def get_already_computed(conn: asyncpg.Connection) -> set:
    rows = await conn.fetch(
        "SELECT seg_id FROM evaluation.confidence_calibration"
    )
    return {r['seg_id'] for r in rows}


# ═════════════════════════════════════════════════════════════════════════════
# Core computation
# ═════════════════════════════════════════════════════════════════════════════

def compute_loo_prediction(
    neighbors: List[Dict],
) -> Optional[Dict]:
    """
    Given enriched neighbor list (dtw_distance + mean_distance),
    compute LOO prediction and all DTW-geometry features.

    Returns dict with all fields, or None if not enough neighbors.
    """
    valid = [
        n for n in neighbors
        if n.get('dtw_distance') is not None
        and n.get('mean_distance') is not None
    ]

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x['dtw_distance'])

    dtw_dists   = np.array([n['dtw_distance']  for n in valid], dtype=float)
    perf_values = np.array([n['mean_distance'] for n in valid], dtype=float)
    ids         = [n['seg_id'] for n in valid]

    # Inverse-DTW weighted prediction (Eq. 3 in paper)
    weights = 1.0 / (dtw_dists + EPSILON)
    p_hat   = float(np.dot(weights, perf_values) / weights.sum())

    # σ = perf_std — consistent with conformal_predictor.py online
    perf_std  = float(perf_values.std())
    perf_mean = float(perf_values.mean())
    perf_cv   = perf_std / (perf_mean + EPSILON)

    # DTW-geometry features for σ-model training
    d_min    = float(dtw_dists.min())
    d_mean   = float(dtw_dists.mean())
    d_max    = float(dtw_dists.max())
    d_spread = d_max - d_min
    d_rel    = d_spread / (d_max + EPSILON)      # 0–1: relative spread
    d_cv     = float(dtw_dists.std() / (d_mean + EPSILON))  # variationskoeff.

    return {
        'p_hat':      p_hat,
        'sigma':      perf_std,
        'ids':        ids,
        'dtw_features': {
            'd_min':     d_min,
            'd_mean':    d_mean,
            'd_max':     d_max,
            'd_spread':  d_spread,
            'd_rel':     d_rel,
            'd_cv':      d_cv,
            'perf_std':  perf_std,
            'perf_cv':   perf_cv,
            'perf_mean': perf_mean,
        },
    }


def seg_id_to_traj_id(seg_id: str) -> str:
    return seg_id.rsplit('_', 1)[0]


async def process_segment(
    seg_id: str,
    traj_id: str,
    p_actual: float,
    pool: asyncpg.Pool,
    k: int,
) -> Optional[Dict]:
    """
    Run LOO similarity search for one segment and compute its
    nonconformity score α plus all DTW-geometry features.
    """
    try:
        # Stage 1 — MultiModalSearcher gets the pool directly
        searcher = MultiModalSearcher(pool)
        search_result = await searcher.search_similar(
            target_id=seg_id,
            modes=SEARCH_MODES,
            limit=k,
            metric=METRIC,
            exclude_ids=[seg_id],   # LOO: exclude itself
        )

        # Extract segment-level results
        seg_results_raw = []
        for group in search_result.get('segment_similarity', []):
            if group.get('target_segment') == seg_id:
                seg_results_raw = group.get('similar_segments', {}).get('results', [])
                break

        if not seg_results_raw:
            logger.debug(f"No Stage 1 results for {seg_id}, skipping.")
            return None

        # Stage 2 — load trajectory data and DTW rerank
        async with pool.acquire() as conn:
            loader = TrajectoryLoader(conn)

            # Collect all traj_ids needed (query + candidates)
            all_traj_ids = set()
            all_traj_ids.add(seg_id_to_traj_id(seg_id))
            for r in seg_results_raw:
                all_traj_ids.add(seg_id_to_traj_id(r['seg_id']))

            # Batch load — one round trip for all
            seg_batch = await loader.load_trajectories_batch(
                list(all_traj_ids), DTW_MODE
            )

        # Query array
        query_traj_data = seg_batch.get(seg_id_to_traj_id(seg_id))
        if query_traj_data is None:
            return None

        query_arr = query_traj_data['segments'].get(seg_id)
        if query_arr is None or len(query_arr) == 0:
            return None

        # Candidate arrays
        cand_seg_ids = [r['seg_id'] for r in seg_results_raw]
        candidates_flat: Dict[str, np.ndarray] = {}
        for r in seg_results_raw:
            cand_seg_id  = r['seg_id']
            cand_traj_id = seg_id_to_traj_id(cand_seg_id)
            cand_data    = seg_batch.get(cand_traj_id)
            if cand_data:
                arr = cand_data['segments'].get(cand_seg_id)
                if arr is not None:
                    candidates_flat[cand_seg_id] = arr

        if not candidates_flat:
            return None

        # DTW reranking (in-memory, no DB)
        dtw_results = rerank(
            query_seq=query_arr,
            candidates=candidates_flat,
            limit=k,
            mode=DTW_MODE,
        )

        dtw_lookup = {r['id']: r['dtw_distance'] for r in dtw_results}

        # Enrich with performance values
        enriched = []
        for r in seg_results_raw:
            sid       = r['seg_id']
            dtw_dist  = dtw_lookup.get(sid)
            mean_dist = r.get('features', {}).get('mean_distance') if r.get('features') else None
            if dtw_dist is not None and mean_dist is not None:
                enriched.append({
                    'seg_id':        sid,
                    'dtw_distance':  dtw_dist,
                    'mean_distance': float(mean_dist),
                })

        if len(enriched) < 2:
            logger.debug(f"Not enough enriched neighbors for {seg_id}")
            return None

        # Compute LOO prediction + DTW features
        result = compute_loo_prediction(enriched)
        if result is None:
            return None

        p_hat            = result['p_hat']
        sigma            = result['sigma']
        neighbor_ids     = result['ids']
        dtw_features     = result['dtw_features']

        prediction_error = abs(p_actual - p_hat)
        alpha            = prediction_error / (sigma + EPSILON)

        return {
            'seg_id':           seg_id,
            'traj_id':          traj_id,
            'p_actual':         p_actual,
            'p_predicted':      p_hat,
            'prediction_error': prediction_error,
            'sigma':            sigma,
            'alpha':            alpha,
            'dtw_features':     json.dumps(dtw_features),
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
            sigma, alpha,
            dtw_features,
            k_neighbors, neighbor_ids,
            config_k, config_dtw_mode, config_metric
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
        )
        ON CONFLICT (seg_id) DO UPDATE SET
            p_actual         = EXCLUDED.p_actual,
            p_predicted      = EXCLUDED.p_predicted,
            prediction_error = EXCLUDED.prediction_error,
            sigma            = EXCLUDED.sigma,
            alpha            = EXCLUDED.alpha,
            dtw_features     = EXCLUDED.dtw_features,
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
            r['sigma'], r['alpha'],
            r['dtw_features'],
            r['k_neighbors'], r['neighbor_ids'],
            r['config_k'], r['config_dtw_mode'], r['config_metric'],
        )
        for r in batch
    ])


async def compute_and_store_quantiles(conn: asyncpg.Connection) -> None:
    """Compute coverage quantiles and store in confidence_quantiles."""
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
        "  σ(x)     = std(neighbor_perf)\n"
        "  interval = p̂ ± q90 × σ(x)\n"
        f"  → q90 = {r['q90']:.4f}\n"
        "Next step: run correlation analysis to check if DTW features\n"
        "predict α → then train σ-model if correlations are strong."
    )

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

    # Print correlation hints for σ-model decision
    corr_rows = await conn.fetch("""
        SELECT
            CORR(alpha, (dtw_features->>'d_min')::float)    AS corr_d_min,
            CORR(alpha, (dtw_features->>'d_spread')::float) AS corr_d_spread,
            CORR(alpha, (dtw_features->>'d_rel')::float)    AS corr_d_rel,
            CORR(alpha, (dtw_features->>'d_cv')::float)     AS corr_d_cv,
            CORR(alpha, (dtw_features->>'perf_std')::float) AS corr_perf_std,
            CORR(alpha, (dtw_features->>'perf_cv')::float)  AS corr_perf_cv
        FROM evaluation.confidence_calibration
        WHERE config_dtw_mode = $1 AND config_metric = $2
    """, DTW_MODE, METRIC)

    if corr_rows:
        c = corr_rows[0]
        logger.info("=" * 60)
        logger.info("Correlation of DTW features with α (nonconformity score):")
        logger.info(f"  d_min    : {c['corr_d_min']:+.4f}")
        logger.info(f"  d_spread : {c['corr_d_spread']:+.4f}")
        logger.info(f"  d_rel    : {c['corr_d_rel']:+.4f}")
        logger.info(f"  d_cv     : {c['corr_d_cv']:+.4f}")
        logger.info(f"  perf_std : {c['corr_perf_std']:+.4f}")
        logger.info(f"  perf_cv  : {c['corr_perf_cv']:+.4f}")
        logger.info("=" * 60)
        logger.info(
            "→ Features with |corr| > 0.3 are worth including in σ-model.\n"
            "→ If all |corr| < 0.1, σ = perf_std (global q) is sufficient."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

async def main(
    k: int,
    batch_size: int,
    resume: bool,
    max_trajectories: Optional[int],
) -> None:
    logger.info(
        f"Starting calibration build  "
        f"k={k}  batch={batch_size}  "
        f"max_trajectories={max_trajectories or 'all'}"
    )

    pool = await create_pool(DATABASE_URL)

    try:
        async with pool.acquire() as conn:
            await ensure_calibration_table(conn)
            all_segments = await get_all_seg_ids(
                conn, METRIC, max_trajectories=max_trajectories
            )
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

        results_buffer: List[Dict] = []
        n_ok   = 0
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

                if results_buffer:
                    async with pool.acquire() as conn:
                        await insert_batch(conn, results_buffer)
                    results_buffer.clear()

                pbar.update(len(batch))
                pbar.set_postfix(ok=n_ok, fail=n_fail)

        logger.info(f"Done.  ok={n_ok:,}  failed/skipped={n_fail:,}")

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
        help='Number of LOO neighbors for Stage 2 (default: 10)'
    )
    parser.add_argument(
        '--batch', type=int, default=10,
        help='Concurrent segments per batch (default: 10)'
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Max. Anzahl Trajektorien — random sampling (default: alle)'
    )
    parser.add_argument(
        '--resume', action='store_true', default=True,
        help='Skip segments already computed (default: True)'
    )
    parser.add_argument(
        '--full-rebuild', action='store_true', default=False,
        help='Recompute everything from scratch'
    )
    args = parser.parse_args()

    resume = args.resume and not args.full_rebuild

    asyncio.run(main(
        k=args.k,
        batch_size=args.batch,
        resume=resume,
        max_trajectories=args.limit,
    ))