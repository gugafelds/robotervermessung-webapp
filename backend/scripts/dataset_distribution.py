# backend/scripts/dataset_distribution.py
"""
Reports the distribution of position, orientation, joint values, velocity
and metadata (movement_type, weight, length) for all trajectories under a
given tag. Terminal output only — no files/folders.

Usage:
    python dataset_distribution.py --tag rv2-dataset-validation
    python dataset_distribution.py --tag rv2-dataset-1 rv2-dataset-validation
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
from collections import Counter
from typing import Dict, List

import asyncpg
import numpy as np
from dotenv import load_dotenv
from scipy.spatial.transform import Rotation as R

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
ORIENTATION_SAMPLE_SIZE = 5000  # random-sampled rows for RPY conversion (fast, representative)


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {'min': float('nan'), 'max': float('nan'), 'mean': float('nan'), 'std': float('nan')}
    return {
        'min': min(values), 'max': max(values),
        'mean': statistics.mean(values),
        'std': statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _print_stats_table(title: str, rows: Dict[str, Dict[str, float]]) -> None:
    print(f'\n{title}')
    print(f'  {"":12s} {"min":>10s} {"max":>10s} {"mean":>10s} {"std":>10s}')
    for label, s in rows.items():
        print(f'  {label:12s} {s["min"]:10.3f} {s["max"]:10.3f} {s["mean"]:10.3f} {s["std"]:10.3f}')


async def report_tag(conn: asyncpg.Connection, tag: str) -> None:
    traj_ids = [r['traj_id'] for r in await conn.fetch(
        "SELECT traj_id FROM motion.traj_info WHERE tag = $1", tag)]

    print(f'\n{"=" * 70}')
    print(f'Tag: {tag} — {len(traj_ids)} trajectories')
    print(f'{"=" * 70}')

    if not traj_ids:
        print('  no trajectories found.')
        return

    # ── Metadata: position centroid, velocity, movement_type, weight, length ──
    meta_rows = await conn.fetch("""
        SELECT movement_type, weight, length, mean_vel, min_vel, max_vel,
               position_x, position_y, position_z
        FROM motion.traj_metadata
        WHERE traj_id = ANY($1::text[])
    """, traj_ids)

    if meta_rows:
        _print_stats_table('Position (segment centroid, mm)', {
            'x': _stats([r['position_x'] for r in meta_rows if r['position_x'] is not None]),
            'y': _stats([r['position_y'] for r in meta_rows if r['position_y'] is not None]),
            'z': _stats([r['position_z'] for r in meta_rows if r['position_z'] is not None]),
        })
        _print_stats_table('Velocity (mm/s)', {
            'mean_vel': _stats([r['mean_vel'] for r in meta_rows if r['mean_vel'] is not None]),
            'min_vel':  _stats([r['min_vel']  for r in meta_rows if r['min_vel']  is not None]),
            'max_vel':  _stats([r['max_vel']  for r in meta_rows if r['max_vel']  is not None]),
        })
        _print_stats_table('Metadata (weight kg / length mm)', {
            'weight': _stats([r['weight'] for r in meta_rows if r['weight'] is not None]),
            'length': _stats([r['length'] for r in meta_rows if r['length'] is not None]),
        })
        mt_counts = Counter(r['movement_type'] for r in meta_rows)
        print('\nmove_type distribution (segments):')
        for mt, c in mt_counts.most_common():
            print(f'  {mt:12s} {c:6d}  ({100 * c / len(meta_rows):.1f}%)')
    else:
        print('  no traj_metadata rows found.')

    # ── Joint values — SQL-side aggregates, fast even over all timesteps ──
    joint_row = await conn.fetchrow("""
        SELECT
            MIN(joint_1) j1_min, MAX(joint_1) j1_max, AVG(joint_1) j1_mean, STDDEV(joint_1) j1_std,
            MIN(joint_2) j2_min, MAX(joint_2) j2_max, AVG(joint_2) j2_mean, STDDEV(joint_2) j2_std,
            MIN(joint_3) j3_min, MAX(joint_3) j3_max, AVG(joint_3) j3_mean, STDDEV(joint_3) j3_std,
            MIN(joint_4) j4_min, MAX(joint_4) j4_max, AVG(joint_4) j4_mean, STDDEV(joint_4) j4_std,
            MIN(joint_5) j5_min, MAX(joint_5) j5_max, AVG(joint_5) j5_mean, STDDEV(joint_5) j5_std,
            MIN(joint_6) j6_min, MAX(joint_6) j6_max, AVG(joint_6) j6_mean, STDDEV(joint_6) j6_std
        FROM motion.traj_joint_states
        WHERE traj_id = ANY($1::text[])
    """, traj_ids)

    if joint_row and joint_row['j1_min'] is not None:
        joint_stats = {
            f'joint_{i}': {
                'min': joint_row[f'j{i}_min'], 'max': joint_row[f'j{i}_max'],
                'mean': joint_row[f'j{i}_mean'], 'std': joint_row[f'j{i}_std'] or 0.0,
            }
            for i in range(1, 7)
        }
        _print_stats_table('Joint values (deg)', joint_stats)
    else:
        print('\nJoint values (deg)\n  no traj_joint_states rows found.')

    # ── Orientation — needs quat→RPY conversion in Python, sample for speed ──
    pose_rows = await conn.fetch("""
        SELECT qx_act, qy_act, qz_act, qw_act
        FROM motion.traj_pose_act
        WHERE traj_id = ANY($1::text[])
        ORDER BY random()
        LIMIT $2
    """, traj_ids, ORIENTATION_SAMPLE_SIZE)

    if pose_rows:
        quats = np.array([[r['qx_act'], r['qy_act'], r['qz_act'], r['qw_act']] for r in pose_rows])
        rpy = R.from_quat(quats).as_euler('xyz', degrees=True)
        _print_stats_table(f'Orientation RPY (deg, sample n={len(pose_rows)})', {
            'roll':  _stats(list(rpy[:, 0])),
            'pitch': _stats(list(rpy[:, 1])),
            'yaw':   _stats(list(rpy[:, 2])),
        })
    else:
        print('\nOrientation RPY (deg)\n  no traj_pose_act rows found.')


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', nargs='+', required=True, help='One or more tags to report (space-separated)')
    args = parser.parse_args()

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for tag in args.tag:
            await report_tag(conn, tag)
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
