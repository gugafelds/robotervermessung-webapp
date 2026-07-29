# backend/scripts/validation_rv2.py
"""
Validation: compare rv2-dataset-1/2/3/4 as knowledge bases against rv2-dataset-validation.

For each validation trajectory, runs similarity search directly (no HTTP) against each
dataset tag in parallel, then computes NCS = |p_actual - p_hat| / sigma.

Usage:
    python validation_rv2.py
    python validation_rv2.py --limit 5 --no-stage2
    python validation_rv2.py --datasets rv2-dataset-1,rv2-dataset-4
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

import asyncpg
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline

load_dotenv()
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL   = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
VALIDATION_TAG = 'rv2-dataset-validation'
DATASETS       = ['rv2-dataset-1', 'rv2-dataset-2', 'rv2-dataset-3', 'rv2-dataset-4']
SEARCH_MODES   = ['position', 'joint', 'orientation', 'velocity', 'metadata']
EPSILON        = 1e-9


async def fetch_first_n_traj_ids(conn: asyncpg.Connection, tag: str, n: int) -> List[str]:
    rows = await conn.fetch("""
        SELECT tm.traj_id
        FROM motion.traj_metadata tm
        JOIN motion.traj_info tt ON tt.traj_id = tm.traj_id
        WHERE tt.tag = $1
        ORDER BY tm.traj_id
        LIMIT $2
    """, tag, n)
    return [r['traj_id'] for r in rows]


async def fetch_validation_trajs(conn: asyncpg.Connection) -> List[Tuple[str, float]]:
    rows = await conn.fetch("""
        SELECT DISTINCT ON (tt.traj_id) tt.traj_id, mi.sidtw_average_distance AS mean_distance
        FROM motion.traj_info tt
        LEFT JOIN evaluation.sidtw_info mi ON mi.seg_id = tt.traj_id
        WHERE tt.tag = $1
        ORDER BY tt.traj_id
    """, VALIDATION_TAG)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows if r['mean_distance'] is not None]


def extract_pred(result: dict, stage: int) -> Optional[Tuple[float, float]]:
    prog = result.get('prognosis') or {}
    key  = 'decomposed' if stage == 2 else 's1_decomposed'
    pred = prog.get(key) or {}
    p_hat, sigma = pred.get('p_hat'), pred.get('sigma')
    if p_hat is None or sigma is None:
        return None
    return float(p_hat), float(sigma)


async def search_dataset(
    pool: asyncpg.Pool, traj_id: str, include_ids: List[str], limit: int, stages: List[int]
) -> Dict[int, Optional[Tuple[float, float]]]:
    out: Dict[int, Optional[Tuple[float, float]]] = {}
    for stage in stages:
        try:
            async with pool.acquire() as conn:
                result = await run_similarity_pipeline(
                    target_id=traj_id,
                    pool=pool,
                    conn=conn,
                    modes=SEARCH_MODES,
                    limit=limit,
                    metric='sidtw',
                    include_ids=include_ids,
                    stage2_active=(stage == 2),
                    prognosis_active=True,
                    calibration_tag='all',
                )
            out[stage] = extract_pred(result, stage)
        except Exception as e:
            logger.warning('failed traj=%s stage=%d: %s', traj_id, stage, e)
            out[stage] = None
    return out


async def run(n: int, limit: int, datasets: List[str], stages: List[int], batch_size: int) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=4,
        max_size=batch_size * len(datasets) + 2,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        dataset_ids: Dict[str, List[str]] = {}
        for tag in datasets:
            ids = await fetch_first_n_traj_ids(conn, tag, n)
            dataset_ids[tag] = ids
            print(f'  {tag}: {len(ids)} trajectories (capped at {n})')

        val_trajs = await fetch_validation_trajs(conn)

    print(f'  {VALIDATION_TAG}: {len(val_trajs)} validation trajectories')
    print()

    if not val_trajs:
        print('No validation trajectories found.')
        await pool.close()
        return

    # store (p_hat, p_actual, sigma) per tag/stage
    results: Dict[str, Dict[int, List[Tuple[float, float, float]]]] = {
        tag: {s: [] for s in stages} for tag in datasets
    }

    with tqdm(total=len(val_trajs), desc='Validating') as pbar:
        for batch_start in range(0, len(val_trajs), batch_size):
            batch = val_trajs[batch_start: batch_start + batch_size]
            tasks = [
                search_dataset(pool, traj_id, dataset_ids[tag], limit, stages)
                for traj_id, _ in batch
                for tag in datasets
            ]
            batch_results = await asyncio.gather(*tasks)

            for i, (traj_id, p_actual) in enumerate(batch):
                for j, tag in enumerate(datasets):
                    preds = batch_results[i * len(datasets) + j]
                    for stage, pred in preds.items():
                        if pred is not None:
                            p_hat, sigma = pred
                            results[tag][stage].append((p_hat, p_actual, sigma))

            pbar.update(len(batch))

    await pool.close()

    import math
    import statistics

    def mae(rows):   return statistics.mean(abs(h - a) for h, a, _ in rows)
    def rmse(rows):  return math.sqrt(statistics.mean((h - a) ** 2 for h, a, _ in rows))
    def ncs(rows):   return [abs(h - a) / max(s, EPSILON) for h, a, s in rows]

    print(f'\n{"="*80}')
    print(f'Validation Results — first {n} trajectories per dataset, limit={limit}')
    print(f'Validation set: {len(val_trajs)} trajectories ({VALIDATION_TAG})')
    print(f'{"="*80}')

    for stage in stages:
        print(f'\nStage {stage} ({"RRF" if stage == 1 else "DTW"}):')
        print(f'  {"Dataset":<22} {"n":>5}  {"MAE (mm)":>10}  {"RMSE (mm)":>10}  {"Mean NCS":>10}  {"Median NCS":>10}')
        print(f'  {"-"*72}')
        for tag in datasets:
            rows = results[tag][stage]
            if not rows:
                print(f'  {tag:<22} {"—":>5}')
                continue
            nc = ncs(rows)
            print(f'  {tag:<22} {len(rows):>5}  '
                  f'{mae(rows):>10.4f}  '
                  f'{rmse(rows):>10.4f}  '
                  f'{statistics.mean(nc):>10.4f}  '
                  f'{statistics.median(nc):>10.4f}')
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n',         type=int, default=400,                   help='First N trajectories per dataset (default: 400)')
    parser.add_argument('--limit',     type=int, default=10,                    help='Similarity search k (default: 10)')
    parser.add_argument('--batch',     type=int, default=10,                    help='Trajectories per parallel batch (default: 10)')
    parser.add_argument('--datasets',  type=str, default=','.join(DATASETS),    help='Comma-separated dataset tags')
    parser.add_argument('--no-stage2', action='store_true',                     help='Skip Stage 2 (DTW)')
    args = parser.parse_args()

    stages = [1] if args.no_stage2 else [1, 2]

    asyncio.run(run(
        n          = args.n,
        limit      = args.limit,
        datasets   = [d.strip() for d in args.datasets.split(',')],
        stages     = stages,
        batch_size = args.batch,
    ))
