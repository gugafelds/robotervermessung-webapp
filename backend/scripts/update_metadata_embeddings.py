# backend/scripts/update_metadata_embeddings.py
"""
Replaces ONLY motion.traj_embeddings.metadata_embedding -- joint/position/orientation/velocity stay untouched.

  --fit URL   fit app/utils/metadata_embeddings/metadata_scale.json on that DB (read-only): per level (segments,
              whole trajectories) mean/std of the METADATA_FEATURES over all rows of motion.traj_metadata and
              weights = sqrt(ExtraTrees feature_importances_) for the measured SIDTW (evaluation.sidtw_info).
  --db URL    recompute metadata_embedding of every row from motion.traj_metadata with metadata_scale.json, set the
              column to the new dimension and rebuild its HNSW indexes -- one transaction. The previous column is
              kept in motion.traj_embeddings_metadata_backup (seg_id, metadata_embedding) unless --no-backup.

--db has no default on purpose (never the production DB from .env by accident). The stored vectors depend on the
scale: after a refit, recompute (both steps in one call). Duration: the UPDATE rewrites every row, so the other
four HNSW indexes get new entries too -- 218k rows on the production DB took 30 min (04.10.2026), during which
motion.traj_embeddings is locked (searches wait). Run it when no measurement campaign is active.

Usage:
    python update_metadata_embeddings.py --fit postgresql://...remote... --db postgresql://...localhost.../rmpd_local
    python update_metadata_embeddings.py --db postgresql://...   # recompute with the existing metadata_scale.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))
from utils.metadata_embeddings.embedding_calculator import (  # noqa: E402
    EmbeddingCalculator, METADATA_FEATURES, METADATA_SCALE_PATH, metadata_features,
)

COLUMNS = 'seg_id, traj_id, movement_type, max_vel, mean_vel, std_vel, duration, length, weight, position_x, position_y, position_z'


def load_metadata(conn, with_labels: bool = False) -> pd.DataFrame:
    join = ' LEFT JOIN evaluation.sidtw_info s ON s.seg_id = m.seg_id' if with_labels else ''
    label = ', s.sidtw_average_distance AS y' if with_labels else ''
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join('m.' + c.strip() for c in COLUMNS.split(','))}{label} FROM motion.traj_metadata m{join}")
    return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])


def fit(url: str) -> None:
    from sklearn.ensemble import ExtraTreesRegressor
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    df = load_metadata(conn, with_labels=True)
    conn.close()
    out = {'features': METADATA_FEATURES, 'computed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'fitted_on': re.sub(r'//[^@]*@', '//', url)}
    for level, rows in (('segment', df[df.seg_id != df.traj_id]), ('trajectory', df[df.seg_id == df.traj_id])):
        X = np.stack([metadata_features(r) for r in rows.to_dict('records')])
        sd = X.std(0)
        lab = rows.y.notna().values
        # 30k labelled rows are plenty for stable importances (100 trees, min_samples_leaf as in the recorder's models)
        idx = np.random.default_rng(0).permutation(np.flatnonzero(lab))[:30000]
        imp = ExtraTreesRegressor(100, min_samples_leaf=5, n_jobs=-1, random_state=0).fit(
            X[idx], rows.y.values[idx].astype(float)).feature_importances_
        out[level] = {'mean': X.mean(0).round(6).tolist(),
                      'std': np.where(sd > 0, sd, 1.0).round(6).tolist(),  # constant feature -> 0 after centring
                      'weight': np.sqrt(imp).round(6).tolist(), 'n_rows': len(rows), 'n_labelled': int(lab.sum())}
        print(f'{level}: {len(rows)} rows, {lab.sum()} labelled; importance ' +
              ', '.join(f'{f}={w:.3f}' for f, w in zip(METADATA_FEATURES, imp)))
    METADATA_SCALE_PATH.write_text(json.dumps(out, indent=2))
    print(f'wrote {METADATA_SCALE_PATH}')


def recompute(url: str, backup: bool) -> None:
    calc = EmbeddingCalculator()
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    rows = load_metadata(conn).to_dict('records')
    emb = [(r['seg_id'], '[' + ','.join(f'{v:.7g}' for v in calc.compute_metadata_embedding(r)) + ']') for r in rows]

    cur.execute("""SELECT format_type(atttypid, atttypmod) FROM pg_attribute
                   WHERE attrelid = 'motion.traj_embeddings'::regclass AND attname = 'metadata_embedding'""")
    new_type = re.sub(r'\(\d+\)', f'({len(METADATA_FEATURES)})', cur.fetchone()[0])
    cur.execute("""SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'motion' AND tablename = 'traj_embeddings'
                   AND indexdef LIKE '%(metadata_embedding %'""")
    indexes = cur.fetchall()

    if backup:
        cur.execute('DROP TABLE IF EXISTS motion.traj_embeddings_metadata_backup')
        cur.execute('CREATE TABLE motion.traj_embeddings_metadata_backup AS SELECT seg_id, metadata_embedding FROM motion.traj_embeddings')
    for name, _ in indexes:
        cur.execute(f'DROP INDEX motion.{name}')
    cur.execute(f'ALTER TABLE motion.traj_embeddings ALTER COLUMN metadata_embedding TYPE {new_type} USING NULL')
    cur.execute('CREATE TEMP TABLE new_metadata_embedding (seg_id TEXT PRIMARY KEY, emb TEXT) ON COMMIT DROP')
    execute_values(cur, 'INSERT INTO new_metadata_embedding VALUES %s', emb, page_size=5000)
    cur.execute(f"""UPDATE motion.traj_embeddings e SET metadata_embedding = n.emb::{new_type}
                    FROM new_metadata_embedding n WHERE n.seg_id = e.seg_id""")
    updated = cur.rowcount
    for _, definition in indexes:
        cur.execute(definition)
    conn.commit()
    cur.execute('SELECT count(*), count(metadata_embedding) FROM motion.traj_embeddings')
    total, filled = cur.fetchone()
    conn.close()
    print(f'metadata_embedding -> {new_type}: {updated} rows updated, {filled}/{total} filled, '
          f'{len(indexes)} indexes rebuilt' + (', backup in motion.traj_embeddings_metadata_backup' if backup else ''))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fit', metavar='URL', help='DB to fit metadata_scale.json on (read-only)')
    ap.add_argument('--db', metavar='URL', required=True, help='DB whose metadata_embedding column is replaced')
    ap.add_argument('--no-backup', action='store_true')
    a = ap.parse_args()
    if a.fit:
        fit(a.fit)
    recompute(a.db, backup=not a.no_backup)
