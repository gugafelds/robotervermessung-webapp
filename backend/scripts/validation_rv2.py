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
DATASETS       = ['rv2-dataset-1', 'rv2-dataset-2', 'rv2-dataset-3', 'rv2-dataset-4',
                   'rv2-dataset-5', 'rv2-dataset-6', 'rv2-dataset-7']
SEARCH_MODES   = ['position', 'joint', 'orientation', 'velocity', 'metadata']
EPSILON        = 1e-9
DEFAULT_STEPS  = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]


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


async def fetch_validation_trajs(conn: asyncpg.Connection, tag: str) -> List[Tuple[str, float]]:
    rows = await conn.fetch("""
        SELECT DISTINCT ON (tt.traj_id) tt.traj_id, mi.sidtw_average_distance AS mean_distance
        FROM motion.traj_info tt
        LEFT JOIN evaluation.sidtw_info mi ON mi.seg_id = tt.traj_id
        WHERE tt.tag = $1
        ORDER BY tt.traj_id
    """, tag)
    return [(r['traj_id'], float(r['mean_distance'])) for r in rows if r['mean_distance'] is not None]


def _temp_tag(base_tag: str, n: int) -> str:
    return f'{base_tag}-first-{n}'


async def set_temp_tag(conn: asyncpg.Connection, base_tag: str, ids: List[str], n: int) -> None:
    await conn.execute("""
        UPDATE motion.traj_info SET tag = $1
        WHERE traj_id = ANY($2::text[]) AND tag = $3
    """, _temp_tag(base_tag, n), ids, base_tag)


async def restore_temp_tag(conn: asyncpg.Connection, base_tag: str, n: int) -> None:
    await conn.execute("""
        UPDATE motion.traj_info SET tag = $1 WHERE tag = $2
    """, base_tag, _temp_tag(base_tag, n))


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
    desc: str,
) -> Dict[str, Dict[int, List[Tuple[float, float, float]]]]:
    """Run all validation trajectories against active_tags and return (p_hat, p_actual, sigma)."""
    results: Dict[str, Dict[int, List[Tuple[float, float, float]]]] = {
        tag: {s: [] for s in stages} for tag in active_tags
    }

    with tqdm(total=len(val_trajs) * len(active_tags), desc=desc, leave=False) as pbar:
        for traj_id, p_actual in val_trajs:
            for tag in active_tags:
                for stage in stages:
                    pred = await search_one(pool, traj_id, stage, limit, include_tags=[tag])
                    if pred:
                        results[tag][stage].append((pred[0], p_actual, pred[1]))
                pbar.update(1)

    return results


# ── Stats ─────────────────────────────────────────────────────────────────────

def mae(rows):        return statistics.mean(abs(h - a) for h, a, _ in rows)
def rmse(rows):       return math.sqrt(statistics.mean((h - a) ** 2 for h, a, _ in rows))
def mean_sigma(rows): return statistics.mean(s for _, _, s in rows)
def ncs(rows):        return [abs(h - a) / max(s, EPSILON) for h, a, s in rows]


# ── Normal run ────────────────────────────────────────────────────────────────

async def run(limit: int, datasets: List[str], stages: List[int], batch_size: int,
              val_tags: List[str]) -> None:
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        for tag in datasets:
            print(f'  {tag}: {await fetch_tag_count(conn, tag)} trajectories')
        all_val: Dict[str, List[Tuple[str, float]]] = {}
        for vtag in val_tags:
            trajs = await fetch_validation_trajs(conn, vtag)
            all_val[vtag] = trajs
            print(f'  {vtag}: {len(trajs)} validation trajectories')

    print()
    all_val = {k: v for k, v in all_val.items() if v}
    if not all_val:
        await pool.close(); return

    # run each validation set independently, then aggregate
    all_results: Dict[str, Dict[str, Dict[int, List[Tuple[float, float, float]]]]] = {}
    for vtag, val_trajs in all_val.items():
        all_results[vtag] = await run_batch(
            pool, val_trajs, datasets, stages, limit, f'Validating [{vtag}]'
        )
    await pool.close()
    _print_table_multi(all_results, datasets, stages, all_val, limit)


# ── Learning curve ────────────────────────────────────────────────────────────

async def run_learning_curve(
    limit: int, datasets: List[str], stages: List[int], batch_size: int, steps: List[int],
    val_tags: List[str] = None,
) -> None:
    if val_tags is None:
        val_tags = ['rv2-dataset-validation']

    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=5, max_size=20,
        server_settings={'search_path': 'motion, public'},
    )

    async with pool.acquire() as conn:
        counts: Dict[str, int] = {}
        for tag in datasets:
            counts[tag] = await fetch_tag_count(conn, tag)
            print(f'  {tag}: {counts[tag]} trajectories')
        all_val: Dict[str, List[Tuple[str, float]]] = {}
        for vtag in val_tags:
            trajs = await fetch_validation_trajs(conn, vtag)
            all_val[vtag] = trajs
            print(f'  {vtag}: {len(trajs)} validation trajectories')
        await cleanup_all_temp_tags(conn, datasets)

    print()
    all_val = {k: v for k, v in all_val.items() if v}
    if not all_val:
        await pool.close(); return

    # all_curves[vtag][n][base_tag][stage] = list of (p_hat, p_actual, sigma)
    all_curves: Dict[str, Dict[int, Dict[str, Dict[int, List[Tuple[float, float, float]]]]]] = {
        vtag: {} for vtag in all_val
    }

    try:
        for n in steps:
            active = [tag for tag in datasets if counts[tag] >= n]
            if not active:
                print(f'n={n}: no dataset has enough trajectories, skipping.')
                continue

            async with pool.acquire() as conn:
                for tag in active:
                    ids = await fetch_first_n_ids(conn, tag, n)
                    await set_temp_tag(conn, tag, ids, n)

            for vtag, val_trajs in all_val.items():
                all_curves[vtag][n] = {}
                for tag in active:
                    temp_tag = _temp_tag(tag, n)
                    tag_results: Dict[int, List[Tuple[float, float, float]]] = {s: [] for s in stages}
                    with tqdm(total=len(val_trajs), desc=f'  n={n:>4} {tag} [{vtag}]', leave=False) as pbar:
                        for i in range(0, len(val_trajs), batch_size):
                            batch = val_trajs[i:i + batch_size]
                            tasks = [
                                search_one(pool, traj_id, stage, limit, include_tags=[temp_tag])
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
                    all_curves[vtag][n][tag] = tag_results

            async with pool.acquire() as conn:
                for tag in active:
                    await restore_temp_tag(conn, tag, n)

            first_vtag = next(iter(all_val))
            print(f'n={n}: done ({", ".join(f"{tag}: {len(all_curves[first_vtag][n].get(tag, {}).get(stages[0], []))} results" for tag in active)})')

    finally:
        async with pool.acquire() as conn:
            await cleanup_all_temp_tags(conn, datasets)

    await pool.close()
    _print_learning_curve(all_curves, datasets, stages, steps, all_val, limit)


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
                actuals_per_tag: Dict[str, List[Tuple[str, float]]] = {}
                for tag in active:
                    ids = await fetch_first_n_ids(conn, tag, n)
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
    _print_learning_curve({None: curve}, datasets, stages, steps, {}, limit, loo=True)


# ── Output ────────────────────────────────────────────────────────────────────

def _print_table_multi(
    all_results: Dict[str, Dict[str, Dict[int, List[Tuple[float, float, float]]]]],
    datasets: List[str],
    stages: List[int],
    all_val: Dict[str, List],
    limit: int,
) -> None:
    vtags = list(all_results.keys())
    multi = len(vtags) > 1
    print(f'\n{"="*80}')
    print(f'Validation Results — limit={limit}')
    for vtag, trajs in all_val.items():
        print(f'  Validation set: {vtag} ({len(trajs)} trajectories)')
    print(f'{"="*80}')

    for stage in stages:
        print(f'\nStage {stage} ({"RRF" if stage == 1 else "DTW"}):')
        hdr = f'  {"Dataset":<22} {"n":>5}  {"MAE":>12}  {"RMSE":>12}  {"Mean σ":>10}  {"Mean NCS":>10}'
        print(hdr)
        print(f'  {"-"*(len(hdr)-2)}')
        _fmt = lambda vals: f'{statistics.mean(vals):>6.4f}±{statistics.stdev(vals) if len(vals)>1 else 0:.4f}'
        for tag in datasets:
            maes, rmses, sigmas, ncss_mean, ns = [], [], [], [], []
            for vtag in vtags:
                rows = all_results[vtag].get(tag, {}).get(stage, [])
                if rows:
                    maes.append(mae(rows)); rmses.append(rmse(rows))
                    sigmas.append(mean_sigma(rows))
                    ncss_mean.append(statistics.mean(ncs(rows)))
                    ns.append(len(rows))
            if not maes:
                print(f'  {tag:<22} {"—":>5}'); continue
            n_str = f'{int(statistics.mean(ns)):>5}'
            if multi:
                print(f'  {tag:<22} {n_str}  {_fmt(maes):>12}  {_fmt(rmses):>12}  '
                      f'{statistics.mean(sigmas):>10.4f}  {statistics.mean(ncss_mean):>10.4f}')
            else:
                print(f'  {tag:<22} {n_str}  {maes[0]:>12.4f}  {rmses[0]:>12.4f}  '
                      f'{sigmas[0]:>10.4f}  {ncss_mean[0]:>10.4f}')
    print()


def _print_learning_curve(all_curves, datasets, stages, steps, all_val, limit, loo=False) -> None:
    # all_curves: Dict[vtag, curve] where curve[n][tag][stage] = rows
    # For LOO: all_curves is passed as {None: curve} single-entry dict
    vtags = list(all_curves.keys())
    multi = len(vtags) > 1
    col   = 16 if multi else 14
    _fmt  = lambda vals: f'{statistics.mean(vals):.4f}±{statistics.stdev(vals) if len(vals)>1 else 0:.4f}'

    valid_steps = [n for n in steps if any(n in all_curves[v] for v in vtags)]

    print(f'\n{"="*80}')
    if loo:
        print(f'LOO Learning Curve — limit={limit} (evaluated within each dataset)')
    else:
        for vtag, trajs in all_val.items():
            print(f'Learning Curve — limit={limit}, validation: {vtag} ({len(trajs)} trajs)')
    print(f'{"="*80}')

    for stage in stages:
        label = "RRF" if stage == 1 else "DTW"
        for metric_name, fn in [('MAE (mm)', mae), ('Mean σ (mm)', mean_sigma),
                                 ('Mean NCS', lambda rows: statistics.mean(ncs(rows)))]:
            print(f'\nStage {stage} ({label}) — {metric_name}:')
            header = f'  {"n":>5}  ' + '  '.join(f'{tag:>{col}}' for tag in datasets)
            print(header)
            print(f'  {"-" * (len(header) - 2)}')
            for n in valid_steps:
                row = f'  {n:>5}  '
                for tag in datasets:
                    vals = [fn(all_curves[v][n][tag][stage])
                            for v in vtags if n in all_curves[v] and tag in all_curves[v][n]
                            and all_curves[v][n][tag].get(stage)]
                    if not vals:
                        row += f'{"—":>{col}}  '
                    elif multi:
                        row += f'{_fmt(vals):>{col}}  '
                    else:
                        row += f'{vals[0]:>{col}.4f}  '
                print(row)
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',            type=int,  default=10,  help='Similarity search k (default: 10)')
    parser.add_argument('--batch',            type=int,  default=5,   help='Trajectories per parallel batch (default: 5)')
    parser.add_argument('--datasets',         nargs='+', default=None, help='Dataset tags (space- or comma-separated)')
    parser.add_argument('--validation-tags',  nargs='+', default=None, help='Validation set tags (space- or comma-separated, default: rv2-dataset-validation)')
    parser.add_argument('--no-stage2',        action='store_true',     help='Skip Stage 2 (DTW)')
    parser.add_argument('--learning-curve',   action='store_true',     help='Run learning curve vs external validation set')
    parser.add_argument('--loo-curve',        action='store_true',     help='Run LOO learning curve within each dataset')
    parser.add_argument('--steps',            nargs='+', default=None, help='n values for learning/LOO curve (space- or comma-separated)')
    args = parser.parse_args()

    def _pl(raw, default): return ' '.join(raw).replace(',', ' ').split() if raw else default

    stages   = [1] if args.no_stage2 else [1, 2]
    datasets = _pl(args.datasets, DATASETS)
    steps    = [int(s) for s in _pl(args.steps, DEFAULT_STEPS)]
    val_tags = _pl(args.validation_tags, ['rv2-dataset-validation'])

    if args.loo_curve:
        asyncio.run(run_loo_curve(
            limit=args.limit, datasets=datasets, stages=stages,
            batch_size=args.batch, steps=steps,
        ))
    elif args.learning_curve:
        asyncio.run(run_learning_curve(
            limit=args.limit, datasets=datasets, stages=stages,
            batch_size=args.batch, steps=steps, val_tags=val_tags,
        ))
    else:
        asyncio.run(run(
            limit=args.limit, datasets=datasets, stages=stages,
            batch_size=args.batch, val_tags=val_tags,
        ))
