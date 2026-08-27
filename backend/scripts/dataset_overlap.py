# backend/scripts/dataset_overlap.py
"""
Quantifies how "close" a validation set is to each candidate dataset in
DTW/embedding space — i.e. whether the validation set was generated the
same way as one of the datasets (and is therefore biased toward it).

For every trajectory in the validation tag, runs a Stage-2 DTW search
restricted to a single target dataset and takes the nearest-neighbor
dtw_distance (not the error prediction). Lower mean distance = validation
set "looks like" that dataset more.

Usage:
    python dataset_overlap.py --datasets rv2-dataset-1 rv2-dataset-7 rv2-dataset-8 rv2-dataset-9
    python dataset_overlap.py --datasets rv2-dataset-1 rv2-dataset-7 --validation-tag rv2-dataset-validation
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
from typing import Dict, List, Optional

import asyncpg
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.multimodal_framework.similarity_pipeline import run_similarity_pipeline

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
SEARCH_MODES = ['position', 'joint', 'orientation', 'velocity', 'metadata']


async def fetch_tag_ids(conn: asyncpg.Connection, tag: str) -> List[str]:
    rows = await conn.fetch("SELECT traj_id FROM motion.traj_info WHERE tag = $1", tag)
    return [r['traj_id'] for r in rows]


async def nearest_neighbor_distance(
    pool: asyncpg.Pool, traj_id: str, target_tag: str, limit: int,
) -> Optional[float]:
    try:
        async with pool.acquire() as conn:
            result = await run_similarity_pipeline(
                target_id=traj_id,
                pool=pool,
                conn=conn,
                modes=SEARCH_MODES,
                limit=limit,
                metric='sidtw',
                include_tags=[target_tag],
                exclude_ids=[traj_id],  # in case validation and target tag overlap
                stage2_active=True,
                prognosis_active=False,
            )
        results = (result.get('traj_similarity') or {}).get('results') or []
        if not results:
            return None
        return float(results[0]['dtw_distance'])
    except Exception:
        return None


async def run(validation_tag: str, datasets: List[str], limit: int, concurrency: int) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        val_ids = await fetch_tag_ids(conn, validation_tag)
        print(f'{validation_tag}: {len(val_ids)} trajectories\n')
        for ds in datasets:
            print(f'  {ds}: {len(await fetch_tag_ids(conn, ds))} trajectories')
    print()

    if not val_ids:
        print('No validation trajectories found — aborting.')
        await pool.close()
        return

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(traj_id: str, ds: str) -> Optional[float]:
        async with sem:
            return await nearest_neighbor_distance(pool, traj_id, ds, limit)

    distances: Dict[str, List[float]] = {ds: [] for ds in datasets}

    for ds in datasets:
        tasks = [_bounded(tid, ds) for tid in val_ids]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f'{validation_tag} -> {ds}'):
            d = await coro
            if d is not None:
                distances[ds].append(d)

    await pool.close()

    print(f'\n{"=" * 70}')
    print(f'Nearest-neighbor DTW distance: {validation_tag} -> each dataset')
    print(f'(lower = validation set looks more like that dataset)')
    print(f'{"=" * 70}')
    print(f'  {"dataset":20s} {"n":>5s} {"mean":>12s} {"median":>12s} {"std":>12s}')
    for ds, vals in distances.items():
        if not vals:
            print(f'  {ds:20s}   no results')
            continue
        print(f'  {ds:20s} {len(vals):5d} {statistics.mean(vals):12.1f} '
              f'{statistics.median(vals):12.1f} {statistics.stdev(vals) if len(vals) > 1 else 0.0:12.1f}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--validation-tag', default='rv2-dataset-validation')
    parser.add_argument('--datasets', nargs='+', required=True)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--concurrency', type=int, default=8)
    args = parser.parse_args()

    asyncio.run(run(args.validation_tag, args.datasets, args.limit, args.concurrency))


if __name__ == '__main__':
    main()
