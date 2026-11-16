"""
Removes corrupt commanded positions (websocket spikes: a run of 1-3 samples leaves the path and comes back, incl. zero
coordinates with a half-value follower) from motion.traj_position_cmd and recomputes what depends on them, per trajectory
in one transaction: evaluation.sidtw/ed (_info + _evaluation, same evaluate() as the upload), acc_position.p1_sidtw,
traj_metadata length + position_x/y/z, and all traj_embeddings columns (same calculator as the upload).
Detection: metrics() of robotervermessung-recorder/scripts/active-learning/analysis/position_cmd_scan.py; per segment the
sample whose removal lowers the largest spike most is dropped, until no spike is left (at most 12 per segment; after a zero
the stream can need 8 samples to come back, each halving the gap: 1789562251_3 z 1, 571, 856, ... 1132 mm).
The samples are deleted, not interpolated (the stream is irregularly timed anyway).

    python scripts/fix_position_spikes.py --ids <file>            # preview, writes nothing
    python scripts/fix_position_spikes.py --check <traj_id> ...   # recompute an unchanged trajectory, must equal the DB
    python scripts/fix_position_spikes.py --ids <file> --update
"""
import argparse
import asyncio
import os
import sys

import asyncpg
import numpy as np
from dotenv import load_dotenv

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REC = os.path.expanduser('~/robotervermessung-recorder')
load_dotenv(os.path.join(BACKEND, '.env'))
DATABASE_URL = os.environ['DATABASE_URL']  # read now: position_cmd_scan imports recorder common.py, which points it at the local mirror
sys.path[:0] = [BACKEND, os.path.join(REC, 'src/trajectory_evaluation'), os.path.join(REC, 'scripts/active-learning/analysis')]
from position_cmd_scan import metrics  # noqa: E402
from trajectory_evaluation.evaluator import evaluate  # noqa: E402
from app.utils.upload_data.evaluation_processor import _insert_info, _insert_pos_deviations  # noqa: E402
from app.utils.metadata_embeddings.metadata_calculator import MetadataCalculatorService  # noqa: E402

EMB = ('joint_embedding', 'position_embedding', 'orientation_embedding', 'velocity_embedding', 'metadata_embedding')
MD = ('length', 'position_x', 'position_y', 'position_z')
vec = lambda v: '[' + ','.join(f'{x:.7g}' for x in v) + ']'  # noqa: E731


def corrupt(P: np.ndarray, max_drop: int = 12) -> list:
    """Indices (into P) of corrupt samples, greedy: drop the candidate that lowers the largest spike most."""
    keep = np.arange(len(P))
    drop = []
    while True:
        _, _, _, _, ns, h, i = metrics(P[keep])
        if ns == 0:
            return sorted(drop)
        if len(drop) == max_drop:
            raise ValueError(f'still spiking after {max_drop} removals')
        cand = [c for c in range(i - 1, i + 4) if 0 < c < len(keep) - 1]
        best = min(cand, key=lambda c: metrics(np.delete(P[keep], c, axis=0))[5])
        drop.append(int(keep[best]))
        keep = np.delete(keep, best)


def demo():
    t = np.linspace(0, 100, 200)[:, None] * np.array([[1.0, 0.5, 0.0]]) + [1000.0, 0, 900]
    assert corrupt(t) == []
    b = t.copy()
    b[50] += [0, 0, 5.0]
    b[100], b[101] = 0.0, b[102] / 2  # zero, then half value
    assert corrupt(b) == [50, 100, 101], corrupt(b)


def stats(d):
    return round(float(np.min(d)), 7), round(float(np.max(d)), 7), round(float(np.mean(d)), 7), round(float(np.std(d)), 7)


async def compute(conn, svc, tid, fix: bool):
    """Everything that depends on traj_position_cmd, with the corrupt samples removed (fix) or as stored."""
    td = await svc._fetch_all_traj_data(conn, tid)
    svc.embedding_calculator = await svc._get_embedding_calculator(conn, td['traj_info']['robot_model'])
    segs, removed = [], []
    for s in td['segments']:
        s = dict(s)
        P = np.column_stack([s['x_data'], s['y_data'], s['z_data']]).astype(float)
        bad = corrupt(P) if fix else []
        removed += [(s['seg_id'], s['timestamps'][i], *P[i].round(1)) for i in bad]
        for k in ('x_data', 'y_data', 'z_data', 'timestamps'):
            s[k] = [v for i, v in enumerate(s[k]) if i not in set(bad)]
        segs.append(s)
    td['segments'] = segs
    # evaluation: same inputs as the upload (POSITION_CMD and TRANSFORM in time order)
    pos = sorted(((ts, s['seg_id'], x, y, z) for s in segs for ts, x, y, z in zip(s['timestamps'], s['x_data'], s['y_data'], s['z_data'])), key=lambda r: int(r[0]))
    act = await conn.fetch('SELECT seg_id, x_act, y_act, z_act FROM motion.traj_pose_act WHERE traj_id = $1 ORDER BY timestamp', tid)
    res = evaluate(soll_pos=np.array([r[2:] for r in pos], float), ist_pos=np.array([list(r[1:]) for r in act], float),
                   soll_ori=np.zeros((1, 4)), ist_ori=np.zeros((1, 4)), segment_ids_pos=[r[1] for r in pos],
                   segment_ids_ori=[r[0] for r in act], use_ed=True, use_sidtw=True, use_gd=False, use_qdtw=False)
    info = {}
    for m, r in res.items():
        d, sid = r.distances, r.segment_ids
        for s in dict.fromkeys(sid):
            info[(m, str(s))] = stats(d[[i for i, x in enumerate(sid) if x == s]])
        info[(m, tid)] = stats(d)
    md = {r['seg_id']: r for r in svc._calculate_all_metadata_in_memory(tid, td)}
    stored = {r['seg_id']: dict(r) for r in await svc._load_existing_metadata(conn, tid)}
    for sid, r in stored.items():
        r.update({k: md[sid][k] for k in MD})
    td['metadata_rows'] = list(stored.values())
    emb = svc._calculate_all_embeddings_in_memory(tid, td)
    return removed, res, info, md, emb


async def stored_state(conn, tid):
    info = {}
    for m in ('ed', 'sidtw'):
        for r in await conn.fetch(f'SELECT seg_id, {m}_min_distance, {m}_max_distance, {m}_average_distance, {m}_standard_deviation '
                                  f'FROM evaluation.{m}_info WHERE traj_id = $1', tid):
            info[(m, r[0])] = tuple(float(v) for v in r[1:])
    md = {r['seg_id']: r for r in await conn.fetch(f'SELECT seg_id, {", ".join(MD)} FROM motion.traj_metadata WHERE traj_id = $1', tid)}
    emb = {r['seg_id']: r for r in await conn.fetch(f'SELECT seg_id, {", ".join(f"{c}::text AS {c}" for c in EMB)} '
                                                    'FROM motion.traj_embeddings WHERE traj_id = $1', tid)}
    return info, md, emb


def compare(tid, info, md, emb, s_info, s_md, s_emb, quiet=False):
    """Largest differences against the stored state: info (mm), metadata, embeddings."""
    assert set(info) == set(s_info), (set(info) ^ set(s_info))
    di = max(abs(a - b) for k in info for a, b in zip(info[k], s_info[k]))
    dm = max(abs(float(md[s][k]) - float(s_md[s][k])) for s in s_md for k in MD)
    de = max(float(np.max(np.abs(np.array(r[c], float) - np.array(s_emb[r['seg_id']][c].strip('[]').split(','), float))))
             for r in emb for c in EMB)
    if not quiet:
        print(f'  {tid}: max diff info {di:.3g} mm, metadata {dm:.3g}, embeddings {de:.3g}')
    return di, dm, de


async def write(conn, tid, removed, res, md, emb):
    async with conn.transaction():
        n = 0
        for sid, ts, *_ in removed:
            n += int((await conn.execute('DELETE FROM motion.traj_position_cmd WHERE traj_id = $1 AND seg_id = $2 AND timestamp = $3',
                                         tid, sid, ts)).split()[-1])
        assert n == len(removed), (n, len(removed))
        for m, r in res.items():
            await conn.execute(f'DELETE FROM evaluation.{m}_evaluation WHERE traj_id = $1', tid)
            await conn.execute(f'DELETE FROM evaluation.{m}_info WHERE traj_id = $1', tid)
            d, sid = r.distances, r.segment_ids
            for s in dict.fromkeys(sid):
                await _insert_info(conn, m, tid, str(s), *stats(d[[i for i, x in enumerate(sid) if x == s]]))
            await _insert_info(conn, m, tid, tid, *stats(d))
            await _insert_pos_deviations(conn, m, tid, d, r.soll_aligned, r.ist_aligned, sid)
        # acc_position.p1_sidtw = last SIDTW deviation of the segment (acc_position_fill.py), trajectory row = mean
        await conn.execute("""
            UPDATE evaluation.acc_position a SET p1_sidtw = round(l.d::numeric, 5) FROM (
                SELECT DISTINCT ON (seg_id) seg_id, sidtw_deviation d FROM evaluation.sidtw_evaluation
                WHERE traj_id = $1 ORDER BY seg_id, points_order DESC) l
            WHERE a.segment_id = l.seg_id AND a.traj_id = $1""", tid)
        await conn.execute("""
            UPDATE evaluation.acc_position SET p1_sidtw = (SELECT round(avg(p1_sidtw)::numeric, 5) FROM evaluation.acc_position
                WHERE traj_id = $1 AND segment_id <> $1) WHERE segment_id = $1""", tid)
        for sid, r in md.items():
            await conn.execute(f'UPDATE motion.traj_metadata SET {", ".join(f"{k} = ${i + 2}" for i, k in enumerate(MD))} '
                               f'WHERE seg_id = $1', sid, *(float(r[k]) for k in MD))
        for r in emb:
            await conn.execute(f'UPDATE motion.traj_embeddings SET {", ".join(f"{c} = ${i + 2}::text::motion.vector" for i, c in enumerate(EMB))} '
                               'WHERE seg_id = $1', r['seg_id'], *(vec(r[c]) for c in EMB))


async def main(a):
    conn = await asyncpg.connect(DATABASE_URL)
    assert DATABASE_URL.endswith('/rmpd'), 'not the remote rmpd'
    svc = MetadataCalculatorService(None)
    try:
        if a.check:
            for tid in a.check:
                _, _, info, md, emb = await compute(conn, svc, tid, fix=False)
                compare(tid, info, md, emb, *await stored_state(conn, tid))
            return
        ids = [l.strip() for l in open(a.ids) if l.strip()]
        for tid in ids:
            s_info, s_md, s_emb = await stored_state(conn, tid)
            _, _, info0, md0, emb0 = await compute(conn, svc, tid, fix=False)
            base = compare(tid, info0, md0, emb0, s_info, s_md, s_emb, quiet=True)
            removed, res, info, md, emb = await compute(conn, svc, tid, fix=True)
            segs = sorted({r[0] for r in removed})
            print(f'{tid}: reproduces DB (info {base[0]:.2g} mm, metadata {base[1]:.2g}, emb {base[2]:.2g}); remove {len(removed)} samples '
                  + ', '.join(f'{r[0]}@{r[1]} ({r[2]}, {r[3]}, {r[4]})' for r in removed))
            for s in segs:
                print(f'    {s}: SIDTW avg/max {s_info[("sidtw", s)][2]:.3f}/{s_info[("sidtw", s)][1]:.3f} -> {info[("sidtw", s)][2]:.3f}/{info[("sidtw", s)][1]:.3f}, '
                      f'ED avg/max {s_info[("ed", s)][2]:.3f}/{s_info[("ed", s)][1]:.3f} -> {info[("ed", s)][2]:.3f}/{info[("ed", s)][1]:.3f}, '
                      f'length {float(s_md[s]["length"]):.1f} -> {md[s]["length"]:.1f}')
            if max(base) > a.tol:
                print(f'    SKIP: recompute of the stored state differs from the DB by more than {a.tol}')
                continue
            if a.update and removed:
                await write(conn, tid, removed, res, md, emb)
                print('    written')
    finally:
        await conn.close()


if __name__ == '__main__':
    demo()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ids', help='file with one traj_id per line')
    ap.add_argument('--check', nargs='+', help='unchanged trajectories: recompute must equal the DB')
    ap.add_argument('--update', action='store_true', help='write; default is a preview')
    ap.add_argument('--tol', type=float, default=1e-3, help='largest allowed difference of the unchanged recompute')
    asyncio.run(main(ap.parse_args()))
