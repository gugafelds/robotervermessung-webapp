"""
Recomputes ONLY motion.traj_embeddings.orientation_embedding for the given trajectories, from the current
motion.traj_orientation_cmd (after fix_soll_values.py). Rows whose vector does not change are not written.
Without --update: preview, writes nothing.

    python scripts/update_orientation_embeddings.py --ids-file ids.txt            # preview
    python scripts/update_orientation_embeddings.py --ids-file ids.txt --update
"""
import argparse
import asyncio
import json
import os
import sys

import asyncpg
import numpy as np
from dotenv import load_dotenv

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BACKEND, '.env'))
sys.path.insert(0, BACKEND)
from app.utils.metadata_embeddings.metadata_calculator import MetadataCalculatorService  # noqa: E402

TOL = 1e-5  # stored vectors are float4


def changed(new: np.ndarray, old: str | None) -> bool:
    return old is None or not np.allclose(new, json.loads(old), atol=TOL)


async def main(a) -> None:
    ids = [l.strip() for l in open(a.ids_file) if l.strip()]
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    svc = MetadataCalculatorService(None)
    written = total = failed = missing = 0
    try:
        for tid in ids:
            data = await svc._fetch_all_traj_data(conn, tid)
            if not data:
                failed += 1
                print(f'{tid}: not found')
                continue
            svc.embedding_calculator = await svc._get_embedding_calculator(conn, data['traj_info']['robot_model'])
            try:
                rows = svc._calculate_all_embeddings_in_memory(tid, data)
            except ValueError as e:  # (0,0,0,0) quaternion: fix_soll_values.py has not run on this trajectory
                failed += 1
                print(f'{tid}: {e}')
                continue
            old = dict(await conn.fetch('SELECT seg_id, orientation_embedding::text FROM motion.traj_embeddings WHERE traj_id = $1', tid))
            diff = [r for r in rows if r['orientation_embedding'] is not None and changed(r['orientation_embedding'], old.get(r['seg_id']))]
            total += len(rows)
            missing += sum(r['seg_id'] not in old for r in diff)
            diff = [r for r in diff if r['seg_id'] in old]  # UPDATE cannot create missing rows
            written += len(diff)
            if diff:
                print(f'{tid}: {len(diff)} of {len(rows)} vectors change')
            if a.update:
                async with conn.transaction():
                    for r in diff:
                        await conn.execute('UPDATE motion.traj_embeddings SET orientation_embedding = $1::text::motion.vector WHERE seg_id = $2',
                                           '[' + ','.join(f'{v:.7g}' for v in r['orientation_embedding']) + ']', r['seg_id'])
    finally:
        await conn.close()
    print(f'{len(ids)} trajectories, {total} vectors, {written} {"written" if a.update else "would change"}, {failed} failed, {missing} without embedding row')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ids-file', required=True, help='one traj_id per line')
    ap.add_argument('--update', action='store_true', help='write; default is a preview')
    asyncio.run(main(ap.parse_args()))
