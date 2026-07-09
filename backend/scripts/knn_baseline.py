# backend/scripts/knn_baseline.py
"""
kNN Metadata Baseline — exakt wie das MATLAB multi_two_stage.m,
aber in Python und mit denselben Komponenten wie das Framework.

Stage 1: Euclidean kNN auf Metadata-Features (statt HNSW-Embeddings)
Stage 2: DTW-Reranking via dtw_reranker.rerank() — identisch zum Framework
Aggregation: length-weighted (traj_metadata.length in mm)
Prognose: inverse-distance weighted mean

Verwendung:
    python knn_baseline.py --tag ba-mueller --k 10 --queries 100
    python knn_baseline.py --tag rv2-dataset-off --k 10
    python knn_baseline.py --tag all --k 5 --queries 200
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional

import asyncpg
import numpy as np
from dotenv import load_dotenv
from tqdm import tqdm

# Framework-Komponenten
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))
from utils.multimodal_framework.dtw_reranker import rerank
from utils.metadata_embeddings.trajectory_loader import TrajectoryLoader

load_dotenv()
logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')

EPSILON     = 1e-6
SIGMA_FLOOR = 0.005

# Normalisierungskonstanten — identisch zu EmbeddingCalculator
VEL_MAX     = 3200.0
ACCEL_MAX   = 10200.0
MAX_PAYLOAD = 60.0
REACH_XY    = 1600.0
REACH_Z_MAX = 2000.0
REACH_Z_MIN = 400.0


# ─────────────────────────────────────────────────────────────────────────────
# Metadata → 15D Feature-Vektor  (identisch zu compute_metadata_embedding)
# ─────────────────────────────────────────────────────────────────────────────

def metadata_to_vector(row: Dict) -> np.ndarray:
    mt = (row.get('movement_type') or '').lower().strip()
    if mt in ('linear', 'l'):
        lr, cr = 1.0, 0.0
    elif mt in ('circular', 'c'):
        lr, cr = 0.0, 1.0
    else:
        nl, nc = mt.count('l'), mt.count('c')
        tot = nl + nc
        lr, cr = (nl / tot, nc / tot) if tot > 0 else (0.0, 0.0)

    vec = np.array([
        lr,
        cr,
        np.clip(row.get('weight',       0.0) / MAX_PAYLOAD, 0, 1),
        np.clip(row.get('position_x',   0.0) / REACH_XY,  -1, 1),
        np.clip(row.get('position_y',   0.0) / REACH_XY,  -1, 1),
        np.clip((row.get('position_z',  0.0) - REACH_Z_MIN) / (REACH_Z_MAX - REACH_Z_MIN), 0, 1),
        np.clip(row.get('max_vel',      0.0) / VEL_MAX,    0, 1),
        np.clip(row.get('mean_vel',     0.0) / VEL_MAX,    0, 1),
        np.clip(row.get('median_vel',   0.0) / VEL_MAX,    0, 1),
        np.clip(row.get('std_vel',      0.0) / VEL_MAX,    0, 1),
        np.clip(abs(row.get('min_accel',   0.0)) / ACCEL_MAX, 0, 1),
        np.clip(abs(row.get('max_accel',   0.0)) / ACCEL_MAX, 0, 1),
        np.clip(abs(row.get('mean_accel',  0.0)) / ACCEL_MAX, 0, 1),
        np.clip(abs(row.get('median_accel',0.0)) / ACCEL_MAX, 0, 1),
        np.clip(row.get('std_accel',    0.0) / ACCEL_MAX, 0, 1),
    ], dtype=np.float32)

    norm = np.linalg.norm(vec)
    return vec / norm if norm > 1e-9 else vec


# ─────────────────────────────────────────────────────────────────────────────
# Prognose — identisch zu predictor.py _predict_direct
# ─────────────────────────────────────────────────────────────────────────────

def weighted_prediction(vals: List[float], dists: List[float]) -> Dict:
    v = np.array(vals, dtype=float)
    d = np.array(dists, dtype=float)
    w = 1.0 / (d + EPSILON)
    w /= w.sum()
    p_hat = float(np.dot(w, v))
    sigma = max(float(np.sqrt(np.dot(w, (v - p_hat) ** 2))), SIGMA_FLOOR, EPSILON)
    return {'p_hat': p_hat, 'sigma': sigma, 'd_min': float(d.min())}


# ─────────────────────────────────────────────────────────────────────────────
# Hauptloop
# ─────────────────────────────────────────────────────────────────────────────

async def run(
    tag:          str,
    k:            int   = 10,
    queries:      Optional[int] = None,
    dtw_mode:     str   = 'position',
    metric:       str   = 'sidtw',
    stage2:       bool  = True,
    random_seed:  int   = 21,
) -> None:

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=8)

    async with pool.acquire() as conn:

        # ── 1. Alle Segment-Metadata laden ───────────────────────────────
        tag_sql = "AND ti.tag = $1" if tag != 'all' else ''
        params  = [tag] if tag != 'all' else []

        seg_rows = await conn.fetch(f"""
            SELECT m.seg_id, m.traj_id, m.length,
                   m.movement_type, m.weight,
                   m.max_vel, m.mean_vel, m.median_vel, m.std_vel,
                   m.min_accel, m.max_accel, m.mean_accel, m.median_accel, m.std_accel,
                   m.position_x, m.position_y, m.position_z
            FROM motion.traj_metadata m
            INNER JOIN motion.traj_info ti ON m.traj_id = ti.traj_id
            WHERE m.seg_id != m.traj_id {tag_sql}
        """, *params)

        all_seg_ids  = [r['seg_id']  for r in seg_rows]
        all_traj_ids = [r['traj_id'] for r in seg_rows]
        all_vecs     = np.stack([metadata_to_vector(dict(r)) for r in seg_rows])
        seg_row_map  = {r['seg_id']: dict(r) for r in seg_rows}

        print(f'  Segmente geladen: {len(all_seg_ids)}')

        # ── 2. Query-Trajektorien ─────────────────────────────────────────
        traj_rows = await conn.fetch(f"""
            SELECT DISTINCT m.traj_id
            FROM motion.traj_metadata m
            INNER JOIN motion.traj_info ti ON m.traj_id = ti.traj_id
            INNER JOIN evaluation.{metric}_info ei ON m.traj_id = ei.seg_id
            WHERE m.seg_id = m.traj_id {tag_sql}
        """, *params)

        query_ids = [r['traj_id'] for r in traj_rows]
        if queries:
            rng = np.random.default_rng(random_seed)
            idx = rng.choice(len(query_ids), min(queries, len(query_ids)), replace=False)
            query_ids = [query_ids[i] for i in sorted(idx)]

        print(f'  Queries: {len(query_ids)}\n')

        # ── 3. Pro Query evaluieren ───────────────────────────────────────
        all_errors_s1 = []
        all_errors_s2 = []
        all_gt        = []

        loader = TrajectoryLoader(conn)

        for traj_id in tqdm(query_ids, desc=f'kNN [{tag}] K={k}'):

            # Ground truth
            gt_row = await conn.fetchrow(
                f"SELECT {metric}_average_distance FROM evaluation.{metric}_info WHERE seg_id = $1",
                traj_id,
            )
            if not gt_row:
                continue
            p_actual = float(gt_row[f'{metric}_average_distance'])

            # Segmente dieser Query
            seg_ids_of_traj = [r['seg_id'] for r in await conn.fetch(
                "SELECT seg_id FROM motion.traj_metadata WHERE traj_id = $1 AND seg_id != traj_id ORDER BY seg_id",
                traj_id,
            )]
            if not seg_ids_of_traj:
                continue

            # Maske: gleiche Trajektorie ausschließen
            valid_mask = np.array([tid != traj_id for tid in all_traj_ids])

            seg_preds_s1 = []
            seg_preds_s2 = []
            seg_lengths  = []

            for seg_id in seg_ids_of_traj:
                if seg_id not in seg_row_map:
                    continue

                seg_meta = seg_row_map[seg_id]
                seg_lengths.append(float(seg_meta.get('length') or 1.0))
                query_vec = metadata_to_vector(seg_meta)

                # kNN — Euclidean auf Feature-Matrix
                dists = np.linalg.norm(all_vecs - query_vec, axis=1)
                dists[~valid_mask] = np.inf

                sorted_idx = np.argsort(dists)[:k]
                nb_ids   = [all_seg_ids[i] for i in sorted_idx if not np.isinf(dists[i])]
                nb_dists = [float(dists[i]) for i in sorted_idx if not np.isinf(dists[i])]

                if not nb_ids:
                    continue

                # Ground truth der Nachbarn
                gt_rows = await conn.fetch(
                    f"SELECT seg_id, {metric}_average_distance FROM evaluation.{metric}_info WHERE seg_id = ANY($1)",
                    nb_ids,
                )
                gt_map = {r['seg_id']: float(r[f'{metric}_average_distance']) for r in gt_rows}

                nb_vals  = [gt_map[sid] for sid in nb_ids if sid in gt_map]
                nb_ds_s1 = [d for sid, d in zip(nb_ids, nb_dists) if sid in gt_map]

                if not nb_vals:
                    continue

                # Stage 1 Prognose
                pred_s1 = weighted_prediction(nb_vals, nb_ds_s1)
                seg_preds_s1.append(pred_s1['p_hat'])

                # Stage 2: DTW Reranking
                if stage2:
                    query_traj_data = await loader.load_trajectory_data(traj_id, dtw_mode)

                    # Segment-Sequenz des Query-Segments laden
                    seg_data = await conn.fetch(
                        f"SELECT seg_id, x_cmd, y_cmd, z_cmd FROM motion.traj_position_cmd WHERE seg_id = $1 ORDER BY timestamp"
                        if dtw_mode == 'position' else
                        f"SELECT seg_id, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6 FROM motion.traj_joint_states WHERE seg_id = $1 ORDER BY timestamp",
                        seg_id,
                    )
                    if not seg_data:
                        seg_preds_s2.append(pred_s1['p_hat'])
                        continue

                    if dtw_mode == 'position':
                        query_seg_seq = np.array([[r['x_cmd'], r['y_cmd'], r['z_cmd']] for r in seg_data])
                    else:
                        query_seg_seq = np.array([[r['joint_1'], r['joint_2'], r['joint_3'],
                                                    r['joint_4'], r['joint_5'], r['joint_6']] for r in seg_data])

                    # Kandidaten-Sequenzen laden
                    if dtw_mode == 'position':
                        cand_rows = await conn.fetch(
                            "SELECT seg_id, x_cmd, y_cmd, z_cmd FROM motion.traj_position_cmd WHERE seg_id = ANY($1) ORDER BY seg_id, timestamp",
                            nb_ids,
                        )
                    else:
                        cand_rows = await conn.fetch(
                            "SELECT seg_id, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6 FROM motion.traj_joint_states WHERE seg_id = ANY($1) ORDER BY seg_id, timestamp",
                            nb_ids,
                        )

                    # Kandidaten gruppieren
                    cand_seqs: Dict[str, np.ndarray] = {}
                    for r in cand_rows:
                        sid = r['seg_id']
                        if sid not in cand_seqs:
                            cand_seqs[sid] = []
                        if dtw_mode == 'position':
                            cand_seqs[sid].append([r['x_cmd'], r['y_cmd'], r['z_cmd']])
                        else:
                            cand_seqs[sid].append([r['joint_1'], r['joint_2'], r['joint_3'],
                                                    r['joint_4'], r['joint_5'], r['joint_6']])
                    cand_seqs = {sid: np.array(v) for sid, v in cand_seqs.items() if v}

                    if not cand_seqs:
                        seg_preds_s2.append(pred_s1['p_hat'])
                        continue

                    # DTW Reranking — identisch zu Framework
                    reranked = rerank(
                        query_seq=query_seg_seq,
                        candidates=cand_seqs,
                        mode=dtw_mode,
                        window_percent=0.2,
                        limit=k,
                    )

                    # Stage 2 Prognose
                    dtw_vals  = [gt_map[r['id']] for r in reranked if r['id'] in gt_map]
                    dtw_dists = [r['dtw_distance'] for r in reranked if r['id'] in gt_map]

                    if dtw_vals:
                        pred_s2 = weighted_prediction(dtw_vals, dtw_dists)
                        seg_preds_s2.append(pred_s2['p_hat'])
                    else:
                        seg_preds_s2.append(pred_s1['p_hat'])

            if not seg_preds_s1:
                continue

            # Length-weighted Aggregation
            w = np.array(seg_lengths[:len(seg_preds_s1)])
            w = w / w.sum()

            p_hat_s1 = float(np.dot(w, seg_preds_s1))
            all_errors_s1.append(abs(p_actual - p_hat_s1))
            all_gt.append(p_actual)

            if stage2 and seg_preds_s2:
                w2 = np.array(seg_lengths[:len(seg_preds_s2)])
                w2 = w2 / w2.sum()
                p_hat_s2 = float(np.dot(w2, seg_preds_s2))
                all_errors_s2.append(abs(p_actual - p_hat_s2))

    # ── Ergebnisse ────────────────────────────────────────────────────────
    e1 = np.array(all_errors_s1)
    gt = np.array(all_gt)

    print(f'\n╔{"═"*62}╗')
    print(f'║  kNN METADATA BASELINE                                       ║')
    print(f'╚{"═"*62}╝\n')
    print(f'  Tag:     {tag}')
    print(f'  K:       {k}')
    print(f'  Queries: {len(e1)}')
    print(f'  DTW:     {dtw_mode}\n')
    print(f'  {"Methode":<28} {"MAE":>8} {"RMSE":>8}')
    print(f'  {"-"*46}')
    print(f'  {"kNN S1 (Metadata)":<28} {np.mean(e1):>8.4f} {np.sqrt(np.mean(e1**2)):>8.4f}')

    if stage2 and all_errors_s2:
        e2 = np.array(all_errors_s2)
        print(f'  {"kNN S2 (Metadata + DTW)":<28} {np.mean(e2):>8.4f} {np.sqrt(np.mean(e2**2)):>8.4f}')

    mean_gt = float(np.mean(gt))
    print(f'\n  Global mean baseline MAE: {np.mean(np.abs(gt - mean_gt)):.4f} mm')
    print(f'  Mean p_actual:            {mean_gt:.4f} mm\n')

    await pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag',      type=str, default='ba-mueller')
    parser.add_argument('--k',        type=int, default=10)
    parser.add_argument('--queries',  type=int, default=None)
    parser.add_argument('--dtw-mode', type=str, default='position')
    parser.add_argument('--metric',   type=str, default='sidtw')
    parser.add_argument('--no-stage2', action='store_true')
    parser.add_argument('--seed',     type=int, default=21)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    asyncio.run(run(
        tag=args.tag,
        k=args.k,
        queries=args.queries,
        dtw_mode=args.dtw_mode,
        metric=args.metric,
        stage2=not args.no_stage2,
        random_seed=args.seed,
    ))