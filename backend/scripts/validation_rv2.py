# backend/scripts/validation_rv2.py
"""
Validation: compare rv2-dataset-1/2/3/4 as knowledge bases against rv2-dataset-validation.

Usage:
    python validation_rv2.py
    python validation_rv2.py --no-stage2
    python validation_rv2.py --datasets rv2-dataset-1,rv2-dataset-4
    python validation_rv2.py --learning-curve
    python validation_rv2.py --learning-curve --steps 50,100,200,300,400
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import os
import statistics
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
DATASETS       = ['rv2-dataset-1', 'rv2-dataset-2', 'rv2-dataset-3', 'rv2-dataset-4', 'rv2-dataset-5']
SEARCH_MODES   = ['position', 'joint', 'orientation', 'velocity', 'metadata']
EPSILON        = 1e-9
DEFAULT_STEPS  = [50, 100, 150]


# ── DB ────────────────────────────────────────────────────────────────────────

async def fetch_tag_count(conn: asyncpg.Connection, tag: str) -> int:
    row = await conn.fetchrow("SELECT COUNT(*) FROM motion.traj_info WHERE tag = $1", tag)
    return row[0]


async def fetch_first_n_ids(conn: asyncpg.Connection, tag: str, n: int) -> List[str]:
    rows = await conn.fetch("""
        SELECT traj_id FROM motion.traj_info
        WHERE tag = $1
        ORDER BY traj_id
        LIMIT $2
    """, tag, n)
    return [r['traj_id'] for r in rows]


async def fetch_actuals_for_ids(conn: asyncpg.Connection, ids: List[str]) -> List[Tuple[str, float]]:
    rows = await conn.fetch("""
        SELECT si.seg_id AS traj_id, si.sidtw_average_distance AS mean_distance
        FROM evaluation.sidtw_info si
        WHERE si.seg_id = ANY($1::text[])
    """, ids)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows if r['mean_distance'] is not None]


async def fetch_validation_trajs(conn: asyncpg.Connection) -> List[Tuple[str, float]]:
    rows = await conn.fetch("""
        SELECT DISTINCT ON (tt.traj_id) tt.traj_id, mi.sidtw_average_distance AS mean_distance
        FROM motion.traj_info tt
        LEFT JOIN evaluation.sidtw_info mi ON mi.seg_id = tt.traj_id
        WHERE tt.tag = $1
        ORDER BY tt.traj_id
    """, VALIDATION_TAG)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows if r['mean_distance'] is not None]


def _temp_tag(base_tag: str, n: int) -> str:
    return f'{base_tag}-first-{n}'


async def set_temp_tag(conn: asyncpg.Connection, base_tag: str, ids: List[str], n: int) -> None:
    """Tag first n trajectories with a temp tag (keeps base_tag on remaining rows)."""
    temp = _temp_tag(base_tag, n)
    await conn.execute("""
        UPDATE motion.traj_info SET tag = $1
        WHERE traj_id = ANY($2::text[]) AND tag = $3
    """, temp, ids, base_tag)


async def restore_temp_tag(conn: asyncpg.Connection, base_tag: str, n: int) -> None:
    """Restore temp tag back to base_tag."""
    temp = _temp_tag(base_tag, n)
    await conn.execute("""
        UPDATE motion.traj_info SET tag = $1 WHERE tag = $2
    """, base_tag, temp)


async def cleanup_all_temp_tags(conn: asyncpg.Connection, datasets: List[str]) -> None:
    """Safety cleanup: restore any leftover temp tags for these datasets."""
    for base_tag in datasets:
        await conn.execute("""
            UPDATE motion.traj_info SET tag = $1
            WHERE tag LIKE $2
        """, base_tag, f'{base_tag}-first-%')


# ── Search ────────────────────────────────────────────────────────────────────

def extract_pred(result: dict, stage: int) -> Optional[Tuple[float, float]]:
    prog = result.get('prognosis') or {}
    key  = 'decomposed' if stage == 2 else 's1_decomposed'
    pred = prog.get(key) or {}
    p_hat, sigma = pred.get('p_hat'), pred.get('sigma')
    if p_hat is None or sigma is None:
        return None
    return float(p_hat), float(sigma)


async def search_one(
    pool: asyncpg.Pool,
    traj_id: str,
    stage: int,
    limit: int,
    include_tags: List[str],
    exclude_ids: Optional[List[str]] = None,
) -> Optional[Tuple[float, float]]:
    try:
        async with pool.acquire() as conn:
            result = await run_similarity_pipeline(
                target_id=traj_id,
                pool=pool,
                conn=conn,
                modes=SEARCH_MODES,
                limit=limit,
                metric='sidtw',
                include_tags=include_tags,
                exclude_ids=exclude_ids,
                stage2_active=(stage == 2),
                prognosis_active=True,
                calibration_tag='all',
                conformal_active=False,
            )
        return extract_pred(result, stage)
    except Exception as e:
        logger.warning('failed traj=%s stage=%d: %s', traj_id, stage, e)
        return None


async def run_batch(
    pool: asyncpg.Pool,
    val_trajs: List[Tuple[str, float]],
    active_tags: List[str],
    stages: List[int],
    limit: int,
    batch_size: int,
    desc: str,
) -> Dict[str, Dict[int, List[Tuple[float, float, float]]]]:
    """Run all validation trajectories against active_tags and return (p_hat, p_actual, sigma)."""
    results: Dict[str, Dict[int, List[Tuple[float, float, float]]]] = {
        tag: {s: [] for s in stages} for tag in active_tags
    }

    with tqdm(total=len(val_trajs), desc=desc, leave=False) as pbar:
        for i in range(0, len(val_trajs), batch_size):
            batch = val_trajs[i:i + batch_size]
            tasks = [
                search_one(pool, traj_id, stage, limit, include_tags=[tag])
                for traj_id, _ in batch
                for tag in active_tags
                for stage in stages
            ]
            res = await asyncio.gather(*tasks)
            idx = 0
            for traj_id, p_actual in batch:
                for tag in active_tags:
                    for stage in stages:
                        pred = res[idx]; idx += 1
                        if pred:
                            results[tag][stage].append((pred[0], p_actual, pred[1]))
            pbar.update(len(batch))

    return results


# ── Stats ─────────────────────────────────────────────────────────────────────

def mae(rows):        return statistics.mean(abs(h - a) for h, a, _ in rows)
def rmse(rows):       return math.sqrt(statistics.mean((h - a) ** 2 for h, a, _ in rows))
def mean_sigma(rows): return statistics.mean(s for _, _, s in rows)
def ncs(rows):        return [abs(h - a) / max(s, EPSILON) for h, a, s in rows]


# ── Normal run ────────────────────────────────────────────────────────────────

async def run(limit: int, datasets: List[str], stages: List[int], batch_size: int) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        for tag in datasets:
            print(f'  {tag}: {await fetch_tag_count(conn, tag)} trajectories')
        val_trajs = await fetch_validation_trajs(conn)

    print(f'  {VALIDATION_TAG}: {len(val_trajs)} validation trajectories\n')
    if not val_trajs:
        await pool.close(); return

    results = await run_batch(pool, val_trajs, datasets, stages, limit, batch_size, 'Validating')
    await pool.close()
    _print_table(results, datasets, stages, val_trajs, f'full datasets, limit={limit}')


# ── Learning curve ────────────────────────────────────────────────────────────

async def run_learning_curve(
    limit: int, datasets: List[str], stages: List[int], batch_size: int, steps: List[int]
) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        counts: Dict[str, int] = {}
        for tag in datasets:
            counts[tag] = await fetch_tag_count(conn, tag)
            print(f'  {tag}: {counts[tag]} trajectories')
        val_trajs = await fetch_validation_trajs(conn)
        # Safety: clean up any leftover temp tags from a previous crashed run
        await cleanup_all_temp_tags(conn, datasets)

    print(f'  {VALIDATION_TAG}: {len(val_trajs)} validation trajectories\n')
    if not val_trajs:
        await pool.close(); return

    # curve[n][base_tag][stage] = list of (p_hat, p_actual, sigma)
    curve: Dict[int, Dict[str, Dict[int, List[Tuple[float, float, float]]]]] = {}

    try:
        for n in steps:
            # Only include datasets that have at least n trajectories
            active = [tag for tag in datasets if counts[tag] >= n]
            if not active:
                print(f'n={n}: no dataset has enough trajectories, skipping.')
                continue

            # Set temp tags for first n trajectories of each active dataset
            async with pool.acquire() as conn:
                for tag in active:
                    ids = await fetch_first_n_ids(conn, tag, n)
                    await set_temp_tag(conn, tag, ids, n)

            temp_tags = [_temp_tag(tag, n) for tag in active]
            results = await run_batch(
                pool, val_trajs, temp_tags, stages, limit, batch_size, f'n={n:>4}'
            )

            # Restore original tags immediately after each step
            async with pool.acquire() as conn:
                for tag in active:
                    await restore_temp_tag(conn, tag, n)

            # Re-key results from temp_tag back to base_tag
            curve[n] = {
                tag: results[_temp_tag(tag, n)]
                for tag in active
                if _temp_tag(tag, n) in results
            }
            print(f'n={n}: done ({", ".join(f"{tag}: {len(curve[n].get(tag, {}).get(stages[0], []))} results" for tag in active)})')

    finally:
        # Guarantee cleanup even on crash
        async with pool.acquire() as conn:
            await cleanup_all_temp_tags(conn, datasets)

    await pool.close()
    _print_learning_curve(curve, datasets, stages, steps, val_trajs, limit)


# ── LOO learning curve ───────────────────────────────────────────────────────

async def run_loo_curve(
    limit: int, datasets: List[str], stages: List[int], batch_size: int, steps: List[int]
) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        counts: Dict[str, int] = {}
        for tag in datasets:
            counts[tag] = await fetch_tag_count(conn, tag)
            print(f'  {tag}: {counts[tag]} trajectories')
        await cleanup_all_temp_tags(conn, datasets)

    print()

    # curve[n][base_tag][stage] = list of (p_hat, p_actual, sigma)
    curve: Dict[int, Dict[str, Dict[int, List[Tuple[float, float, float]]]]] = {}

    try:
        for n in steps:
            active = [tag for tag in datasets if counts[tag] >= n]
            if not active:
                print(f'n={n}: skipping, no dataset has enough trajectories.')
                continue

            curve[n] = {}

            async with pool.acquire() as conn:
                ids_per_tag: Dict[str, List[str]] = {}
                actuals_per_tag: Dict[str, List[Tuple[str, float]]] = {}
                for tag in active:
                    ids = await fetch_first_n_ids(conn, tag, n)
                    ids_per_tag[tag] = ids
                    actuals_per_tag[tag] = await fetch_actuals_for_ids(conn, ids)
                    await set_temp_tag(conn, tag, ids, n)

            for tag in active:
                temp_tag = _temp_tag(tag, n)
                trajs = actuals_per_tag[tag]
                tag_results: Dict[int, List[Tuple[float, float, float]]] = {s: [] for s in stages}

                with tqdm(total=len(trajs), desc=f'  n={n:>4} {tag}', leave=False) as pbar:
                    for i in range(0, len(trajs), batch_size):
                        batch = trajs[i:i + batch_size]
                        tasks = [
                            search_one(pool, traj_id, stage, limit,
                                       include_tags=[temp_tag], exclude_ids=[traj_id])
                            for traj_id, _ in batch
                            for stage in stages
                        ]
                        res = await asyncio.gather(*tasks)
                        idx = 0
                        for traj_id, p_actual in batch:
                            for stage in stages:
                                pred = res[idx]; idx += 1
                                if pred:
                                    tag_results[stage].append((pred[0], p_actual, pred[1]))
                        pbar.update(len(batch))

                curve[n][tag] = tag_results

            async with pool.acquire() as conn:
                for tag in active:
                    await restore_temp_tag(conn, tag, n)

            print(f'n={n}: done ({", ".join(f"{tag}: {len(curve[n].get(tag, {}).get(stages[0], []))} results" for tag in active)})')

    finally:
        async with pool.acquire() as conn:
            await cleanup_all_temp_tags(conn, datasets)

    await pool.close()
    _print_learning_curve(curve, datasets, stages, steps, None, limit, loo=True)


# ── Output ────────────────────────────────────────────────────────────────────

def _print_table(results, datasets, stages, val_trajs, title: str) -> None:
    print(f'\n{"="*80}')
    print(f'Validation Results — {title}')
    print(f'Validation set: {len(val_trajs)} trajectories ({VALIDATION_TAG})')
    print(f'{"="*80}')
    for stage in stages:
        print(f'\nStage {stage} ({"RRF" if stage == 1 else "DTW"}):')
        print(f'  {"Dataset":<22} {"n":>5}  {"MAE (mm)":>10}  {"RMSE (mm)":>10}  {"Mean σ":>10}  {"Mean NCS":>10}  {"Median NCS":>10}')
        print(f'  {"-"*82}')
        for tag in datasets:
            rows = results[tag][stage]
            if not rows:
                print(f'  {tag:<22} {"—":>5}'); continue
            nc = ncs(rows)
            print(f'  {tag:<22} {len(rows):>5}  '
                  f'{mae(rows):>10.4f}  {rmse(rows):>10.4f}  '
                  f'{mean_sigma(rows):>10.4f}  '
                  f'{statistics.mean(nc):>10.4f}  {statistics.median(nc):>10.4f}')
    print()


def _print_learning_curve(curve, datasets, stages, steps, val_trajs, limit, loo=False) -> None:
    valid_steps = [n for n in steps if n in curve]
    col = 14

    print(f'\n{"="*80}')
    if loo:
        print(f'LOO Learning Curve — limit={limit} (evaluated within each dataset)')
    else:
        print(f'Learning Curve — limit={limit}, validation set: {len(val_trajs)} trajectories')
    print(f'{"="*80}')

    for stage in stages:
        label = "RRF" if stage == 1 else "DTW"
        for metric_name, fn in [('MAE (mm)', mae), ('Mean σ (mm)', mean_sigma)]:
            print(f'\nStage {stage} ({label}) — {metric_name}:')
            header = f'  {"n":>5}  ' + '  '.join(f'{tag:>{col}}' for tag in datasets)
            print(header)
            print(f'  {"-" * (len(header) - 2)}')
            for n in valid_steps:
                row = f'  {n:>5}  '
                for tag in datasets:
                    rows = curve[n].get(tag, {}).get(stage, [])
                    row += f'{fn(rows):>{col}.4f}  ' if rows else f'{"—":>{col}}  '
                print(row)
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',          type=int,  default=10,                 help='Similarity search k (default: 10)')
    parser.add_argument('--batch',          type=int,  default=5,                  help='Trajectories per parallel batch (default: 5)')
    parser.add_argument('--datasets',       type=str,  default=','.join(DATASETS), help='Comma-separated dataset tags')
    parser.add_argument('--no-stage2',      action='store_true',                   help='Skip Stage 2 (DTW)')
    parser.add_argument('--learning-curve', action='store_true',                   help='Run learning curve vs external validation set')
    parser.add_argument('--loo-curve',      action='store_true',                   help='Run LOO learning curve within each dataset')
    parser.add_argument('--steps',          type=str,  default=','.join(map(str, DEFAULT_STEPS)),
                                                                                   help='Comma-separated n values for learning/LOO curve')
    args = parser.parse_args()

    stages   = [1] if args.no_stage2 else [1, 2]
    datasets = [d.strip() for d in args.datasets.split(',')]
    steps    = [int(s.strip()) for s in args.steps.split(',')]

    if args.loo_curve:
        asyncio.run(run_loo_curve(
            limit=args.limit, datasets=datasets, stages=stages,
            batch_size=args.batch, steps=steps,
        ))
    elif args.learning_curve:
        asyncio.run(run_learning_curve(
            limit=args.limit, datasets=datasets, stages=stages,
            batch_size=args.batch, steps=steps,
        ))
    else:
        asyncio.run(run(
            limit=args.limit, datasets=datasets, stages=stages, batch_size=args.batch,
        ))
