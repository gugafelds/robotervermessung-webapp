"""
Creates motion.traj_embeddings rows for trajectories that have none (all five embeddings, segments and
trajectory level), from the stored motion.traj_metadata, the same path as the upload (process_single_traj).
Without --insert: preview, writes nothing.

    python scripts/insert_missing_embeddings.py            # preview
    python scripts/insert_missing_embeddings.py --insert
"""
import argparse
import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BACKEND, '.env'))
sys.path.insert(0, BACKEND)
from app.utils.metadata_embeddings.metadata_calculator import MetadataCalculatorService  # noqa: E402

COLS = ('joint_embedding', 'position_embedding', 'orientation_embedding', 'velocity_embedding', 'metadata_embedding')
vec = lambda v: '[' + ','.join(f'{x:.7g}' for x in v) + ']'  # noqa: E731


async def main(a) -> None:
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    svc = MetadataCalculatorService(None)
    try:
        ids = [r[0] for r in await conn.fetch('SELECT traj_id FROM motion.traj_info i WHERE NOT EXISTS '
                                              '(SELECT 1 FROM motion.traj_embeddings e WHERE e.traj_id = i.traj_id) ORDER BY 1')]
        rows, bad = [], []
        for tid in ids:
            res = await svc.process_single_traj(conn, tid, compute_metadata=False)
            segs = res['segments_processed'] + 1  # metadata rows incl. the trajectory row
            emb = res['embeddings']
            incomplete = [r['seg_id'] for r in emb if any(r[c] is None for c in COLS)]
            print(f"{tid}: {len(emb)} rows for {segs} metadata rows, incomplete {incomplete or 'none'}, error {res['error']}")
            if res['error'] or incomplete or len(emb) != segs:
                bad.append(tid)  # table has no NULL embeddings: never insert a partial trajectory
            else:
                rows += emb
        if a.insert and rows:
            async with conn.transaction():
                await conn.executemany(
                    'INSERT INTO motion.traj_embeddings (seg_id, traj_id, ' + ', '.join(COLS) + ') VALUES ($1, $2, '
                    + ', '.join(f'${i}::text::motion.vector' for i in range(3, 8)) + ') ON CONFLICT (seg_id) DO NOTHING',
                    [(r['seg_id'], r['traj_id'], *(vec(r[c]) for c in COLS)) for r in rows])
        print(f'{len(ids)} trajectories without embeddings, {len(rows)} rows {"inserted" if a.insert else "would be inserted"}, '
              f'skipped {bad or "none"}')
    finally:
        await conn.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--insert', action='store_true', help='write; default is a preview')
    asyncio.run(main(ap.parse_args()))
