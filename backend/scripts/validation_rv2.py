# backend/scripts/validation_rv2.py
"""
Validation: compare rv2-dataset-1/2/3/4 as knowledge bases against rv2-dataset-validation.

For each validation trajectory, runs similarity search using the first N trajectories
of each dataset as include_ids, then computes NCS = |p_actual - p_hat| / sigma.

Usage:
    python validation_rv2.py
    python validation_rv2.py --n 200 --limit 5
    python validation_rv2.py --datasets rv2-dataset-1,rv2-dataset-4 --n 400
    python validation_rv2.py --backend http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

import asyncpg
import httpx
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')

VALIDATION_TAG = 'rv2-dataset-validation'
DATASETS       = ['rv2-dataset-1', 'rv2-dataset-2', 'rv2-dataset-3', 'rv2-dataset-4']
EPSILON        = 1e-9


# ── DB helpers ────────────────────────────────────────────────────────────────

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
    """Returns list of (traj_id, p_actual=mean_distance)."""
    rows = await conn.fetch("""
        SELECT tm.traj_id, mi.sidtw_average_distance AS mean_distance
        FROM motion.traj_metadata tm
        JOIN motion.traj_info tt ON tt.traj_id = tm.traj_id
        LEFT JOIN evaluation.sidtw_info mi ON mi.seg_id = tm.traj_id
        WHERE tt.tag = $1
        ORDER BY tm.traj_id
    """, VALIDATION_TAG)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows if r['mean_distance'] is not None]


# ── HTTP search ───────────────────────────────────────────────────────────────

async def search_one(
    client:      httpx.AsyncClient,
    traj_id:     str,
    include_ids: List[str],
    stage:       int,
    limit:       int,
    backend:     str,
) -> Optional[Dict]:
    """GET /api/similarity/search/{traj_id} with include_ids and stage."""
    params = {
        'modes':          'position,joint,orientation,velocity,metadata',
        'limit':          limit,
        'metric':         'sidtw',
        'stage2_active':  'true' if stage == 2 else 'false',
        'prognosis_active': 'true',
        'include_ids':    ','.join(include_ids),
    }
    try:
        r = await client.get(f'{backend}/api/similarity/search/{traj_id}', params=params, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning('search failed traj=%s stage=%d: %s', traj_id, stage, e)
        return None


def extract_pred(response: dict, stage: int) -> Optional[Tuple[float, float]]:
    """Returns (p_hat, sigma) for the given stage."""
    prog = response.get('prognosis') or {}
    key  = 'decomposed' if stage == 2 else 's1_decomposed'
    pred = prog.get(key) or {}
    p_hat = pred.get('p_hat')
    sigma = pred.get('sigma')
    if p_hat is None or sigma is None:
        return None
    return float(p_hat), float(sigma)


# ── Core ──────────────────────────────────────────────────────────────────────

async def run(n: int, limit: int, datasets: List[str], backend: str) -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=4)

    async with pool.acquire() as conn:
        # 1. First N traj_ids per dataset
        dataset_ids: Dict[str, List[str]] = {}
        for tag in datasets:
            ids = await fetch_first_n_traj_ids(conn, tag, n)
            dataset_ids[tag] = ids
            print(f'  {tag}: {len(ids)} trajectories as knowledge base')

        # 2. Validation trajectories
        val_trajs = await fetch_validation_trajs(conn)
        print(f'  {VALIDATION_TAG}: {len(val_trajs)} validation trajectories\n')

    if not val_trajs:
        print('No validation trajectories found.')
        await pool.close()
        return

    # 3. For each validation traj: search against all datasets × both stages in parallel
    # results[tag][stage] = list of NCS values
    results: Dict[str, Dict[int, List[float]]] = {
        tag: {1: [], 2: []} for tag in datasets
    }

    async with httpx.AsyncClient() as client:
        for traj_id, p_actual in tqdm(val_trajs, desc='Validating'):
            tasks = {
                (tag, stage): search_one(client, traj_id, dataset_ids[tag], stage, limit, backend)
                for tag in datasets
                for stage in (1, 2)
            }
            responses = await asyncio.gather(*tasks.values())

            for (tag, stage), response in zip(tasks.keys(), responses):
                if response is None:
                    continue
                pred = extract_pred(response, stage)
                if pred is None:
                    continue
                p_hat, sigma = pred
                ncs = abs(p_actual - p_hat) / max(sigma, EPSILON)
                results[tag][stage].append(ncs)

    await pool.close()

    # 4. Print results
    import statistics

    print(f'\n{"="*70}')
    print(f'Validation Results — first {n} trajectories per dataset, limit={limit}')
    print(f'Validation set: {len(val_trajs)} trajectories ({VALIDATION_TAG})')
    print(f'{"="*70}')

    for stage in (1, 2):
        print(f'\nStage {stage} ({"RRF" if stage == 1 else "DTW"}):')
        print(f'  {"Dataset":<22} {"n":>5}  {"MAE (mean NCS)":>14}  {"Median NCS":>10}  {"Q90 NCS":>9}')
        print(f'  {"-"*65}')
        for tag in datasets:
            vals = results[tag][stage]
            if not vals:
                print(f'  {tag:<22} {"—":>5}')
                continue
            print(f'  {tag:<22} {len(vals):>5}  '
                  f'{statistics.mean(vals):>14.4f}  '
                  f'{statistics.median(vals):>10.4f}  '
                  f'{sorted(vals)[int(len(vals)*0.9)]:>9.4f}')
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate rv2 datasets against validation set.')
    parser.add_argument('--n',        type=int,   default=400,                   help='First N trajectories per dataset (default: 400)')
    parser.add_argument('--limit',    type=int,   default=10,                    help='Similarity search limit/k (default: 10)')
    parser.add_argument('--datasets', type=str,   default=','.join(DATASETS),    help='Comma-separated dataset tags')
    parser.add_argument('--backend',  type=str,   default='http://localhost:8000', help='Backend URL')
    args = parser.parse_args()

    asyncio.run(run(
        n        = args.n,
        limit    = args.limit,
        datasets = [d.strip() for d in args.datasets.split(',')],
        backend  = args.backend,
    ))
