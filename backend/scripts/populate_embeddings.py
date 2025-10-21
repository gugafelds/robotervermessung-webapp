# backend/scripts/populate_embeddings.py

import asyncio
import asyncpg
import numpy as np
import time
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.embedding_calculator import EmbeddingCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:manager@134.147.100.22:5432/robotervermessung"


class EmbeddingConfig:
    """Konfiguration für Embedding Population"""
    def __init__(
        self,
        joint_samples: int = 50,
        position_samples: int = 50,
        orientation_samples: int = 30,
        downsample_factor: int = 5
    ):
        self.joint_samples = joint_samples
        self.position_samples = position_samples
        self.orientation_samples = orientation_samples
        self.downsample_factor = downsample_factor


async def populate_all_embeddings(
    config: EmbeddingConfig,
    limit: int = 1000,
    mode: str = 'full'  # 'full', 'segments-only', 'bahnen-only'
):
    """
    MAIN FUNCTION: Populiert ALLE Embeddings (Joint, Position, Orientation)

    Args:
        config: EmbeddingConfig mit Sample-Anzahlen
        limit: Anzahl Bahnen
        mode: 'full' = Segmente+Bahnen, 'segments-only', 'bahnen-only'
    """
    logger.info("=" * 70)
    logger.info("POPULATE ALL EMBEDDINGS")
    logger.info(f"Mode: {mode.upper()}")
    logger.info(f"Limit: {limit} Bahnen")
    logger.info(f"Joint: {config.joint_samples} samples → {config.joint_samples * 6} dims")
    logger.info(f"Position: {config.position_samples} samples → {config.position_samples * 3} dims")
    logger.info(f"Orientation: {config.orientation_samples} samples → {config.orientation_samples * 4} dims")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        calculator = EmbeddingCalculator(
            joint_samples=config.joint_samples,
            position_samples=config.position_samples,
            orientation_samples=config.orientation_samples
        )

        async with pool.acquire() as conn:
            # Phase 1: Lade Bahnen
            logger.info("\n[Phase 1/6] Lade Bahnen...")
            t0 = time.time()
            bahnen = await conn.fetch("""
                SELECT bahn_id
                FROM bahn_info
                ORDER BY recording_date DESC, bahn_id DESC
                LIMIT $1
            """, limit)
            bahn_ids = [r['bahn_id'] for r in bahnen]
            logger.info(f"✓ {len(bahn_ids)} Bahnen ({time.time()-t0:.1f}s)")

            # Phase 2: Lade Segmente
            if mode in ['full', 'segments-only']:
                logger.info("\n[Phase 2/6] Lade Segmente...")
                t0 = time.time()
                segments = await conn.fetch("""
                                            SELECT segment_id, bahn_id
                                            FROM bahn_metadata
                                            WHERE bahn_id = ANY ($1)
                                              AND segment_id != bahn_id -- NUR Segmente
                                            """, bahn_ids)
                segment_ids = [r['segment_id'] for r in segments]
                segment_to_bahn = {r['segment_id']: r['bahn_id'] for r in segments}
                logger.info(f"✓ {len(segment_ids)} Segmente ({time.time() - t0:.1f}s)")
            else:
                segment_ids = []
                segment_to_bahn = {}

            # Phase 3: Check existing
            logger.info("\n[Phase 3/6] Prüfe existierende Embeddings...")
            t0 = time.time()
            existing = await conn.fetch("""
                                        SELECT segment_id
                                        FROM bahn_embeddings
                                        WHERE bahn_id = ANY ($1)
                                        """, bahn_ids)
            existing_ids = {r['segment_id'] for r in existing}

            if mode == 'bahnen-only':
                # Nur Bahnen (segment_id = bahn_id)
                missing_ids = [bid for bid in bahn_ids if bid not in existing_ids]
                segment_to_bahn = {bid: bid for bid in missing_ids}  # FIX: Mapping für Bahnen
            elif mode == 'segments-only':
                # Nur Segmente (segment_id != bahn_id)
                missing_ids = [sid for sid in segment_ids if sid not in existing_ids]
            else:  # full
                # Beides: Segmente UND Bahnen
                missing_segment_ids = [sid for sid in segment_ids if sid not in existing_ids]
                missing_bahn_ids = [bid for bid in bahn_ids if bid not in existing_ids]
                missing_ids = missing_segment_ids + missing_bahn_ids
                # Erweitere Mapping für Bahnen
                segment_to_bahn.update({bid: bid for bid in missing_bahn_ids})

            logger.info(f"✓ Zu berechnen: {len(missing_ids)} ({time.time() - t0:.1f}s)")
            if mode == 'full':
                logger.info(f"  - Segmente: {len(missing_segment_ids)}")
                logger.info(f"  - Bahnen: {len(missing_bahn_ids)}")

            if not missing_ids:
                logger.info("🎉 Alle Embeddings vorhanden!")
                return

            # Phase 4: Lade ALLE Daten (BULK mit ARRAY aggregation)
            logger.info("\n[Phase 4/6] Lade Rohdaten (BULK)...")
            all_data = await load_all_data_bulk(
                conn,
                missing_ids,
                mode,
                config.downsample_factor
            )

            # Phase 5: Berechne Embeddings
            logger.info("\n[Phase 5/6] Berechne Embeddings...")
            t0 = time.time()
            rows = compute_all_embeddings(
                calculator,
                all_data,
                segment_to_bahn if mode != 'bahnen-only' else {bid: bid for bid in bahn_ids}
            )
            logger.info(f"✓ {len(rows)} Embeddings berechnet ({time.time()-t0:.1f}s)")

            # Phase 6: Bulk Insert
            if rows:
                logger.info("\n[Phase 6/6] Bulk Insert...")
                await bulk_insert_embeddings(conn, rows)

            logger.info("\n" + "=" * 70)
            logger.info("FERTIG!")
            logger.info(f"✓ Neue Embeddings: {len(rows)}")
            logger.info(f"✓ Gesamt in DB: {len(existing_ids) + len(rows)}")
            logger.info("=" * 70)

    finally:
        await pool.close()


async def load_all_data_bulk(
        conn,
        ids: List[str],
        mode: str,
        downsample_factor: int
) -> Dict:
    """
    Lädt Joint, Position und Orientation Daten für alle IDs

    Returns: {
        'joint': {id: [data]},
        'position': {id: [data]},
        'orientation': {id: [data]}
    }
    """
    t0 = time.time()
    result = {'joint': {}, 'position': {}, 'orientation': {}}

    if mode == 'full':
        # MIXED mode
        await _load_segments_data(conn, ids, downsample_factor, result)
        return result

        # Für segments-only und bahnen-only
    id_col = 'segment_id' if mode == 'segments-only' else 'bahn_id'
    order_clause = 'timestamp' if mode == 'segments-only' else 'segment_id, timestamp'

    # ===== JOINT STATES =====
    logger.info("  → Joint States...")
    joint_data = await conn.fetch(f"""
        WITH numbered AS (
            SELECT {id_col},
                   joint_1, joint_2, joint_3, joint_4, joint_5, joint_6,
                   ROW_NUMBER() OVER (PARTITION BY {id_col} ORDER BY {order_clause}) as rn
            FROM bahn_joint_states
            WHERE {id_col} = ANY($1)
        )
        SELECT {id_col},
               array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j1,
               array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j2,
               array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j3,
               array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j4,
               array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j5,
               array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j6
        FROM numbered
        GROUP BY {id_col}
    """, ids)

    for row in joint_data:
        id_val = row[id_col]
        if row['j1'] and len(row['j1']) > 0:
            result['joint'][id_val] = [
                {'joint_1': row['j1'][i], 'joint_2': row['j2'][i], 'joint_3': row['j3'][i],
                 'joint_4': row['j4'][i], 'joint_5': row['j5'][i], 'joint_6': row['j6'][i]}
                for i in range(len(row['j1']))
            ]

    logger.info(f"    ✓ Joint: {len(result['joint'])} IDs ({time.time() - t0:.1f}s)")

    # ===== POSITION SOLL =====
    t0 = time.time()
    logger.info("  → Position Soll...")
    pos_data = await conn.fetch(f"""
        WITH numbered AS (
            SELECT {id_col}, x_soll, y_soll, z_soll,
                   ROW_NUMBER() OVER (PARTITION BY {id_col} ORDER BY {order_clause}) as rn
            FROM bahn_position_soll
            WHERE {id_col} = ANY($1)
        )
        SELECT {id_col},
               array_agg(x_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as x,
               array_agg(y_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as y,
               array_agg(z_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as z
        FROM numbered
        GROUP BY {id_col}
    """, ids)

    for row in pos_data:
        id_val = row[id_col]
        if row['x'] and len(row['x']) > 0:
            result['position'][id_val] = [
                {'x_soll': row['x'][i], 'y_soll': row['y'][i], 'z_soll': row['z'][i]}
                for i in range(len(row['x']))
            ]

    logger.info(f"    ✓ Position: {len(result['position'])} IDs ({time.time() - t0:.1f}s)")

    # ===== ORIENTATION SOLL =====
    t0 = time.time()
    logger.info("  → Orientation Soll...")
    ori_data = await conn.fetch(f"""
        WITH numbered AS (
            SELECT {id_col}, qw_soll, qx_soll, qy_soll, qz_soll,
                   ROW_NUMBER() OVER (PARTITION BY {id_col} ORDER BY {order_clause}) as rn
            FROM bahn_orientation_soll
            WHERE {id_col} = ANY($1)
        )
        SELECT {id_col},
               array_agg(qw_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qw,
               array_agg(qx_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qx,
               array_agg(qy_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qy,
               array_agg(qz_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qz
        FROM numbered
        GROUP BY {id_col}
    """, ids)

    for row in ori_data:
        id_val = row[id_col]
        if row['qw'] and len(row['qw']) > 0:
            result['orientation'][id_val] = [
                {'qw_soll': row['qw'][i], 'qx_soll': row['qx'][i],
                 'qy_soll': row['qy'][i], 'qz_soll': row['qz'][i]}
                for i in range(len(row['qw']))
            ]

    logger.info(f"    ✓ Orientation: {len(result['orientation'])} IDs ({time.time() - t0:.1f}s)")

    return result


async def _load_segments_data(conn, ids, downsample_factor, result):
    """
    Helper für 'full' mode: Lädt Segmente UND Bahnen separat

    Segmente: WHERE segment_id = X (nur das Segment)
    Bahnen: WHERE bahn_id = X (alle Segmente der Bahn!)
    """
    # Trenne IDs in Segmente vs Bahnen
    # Annahme: Segmente haben "_seg_" oder mehr als 1 Underscore
    # Bahnen sind einfache IDs
    segment_ids = []
    bahn_ids = []

    for id_val in ids:
        # Einfache Heuristik: Wenn ID einen Underscore enthält, ist es ein Segment
        # Sonst ist es eine Bahn
        if '_' in id_val:
            segment_ids.append(id_val)
        else:
            bahn_ids.append(id_val)

    logger.info(f"  → Mixed Mode: {len(segment_ids)} Segmente + {len(bahn_ids)} Bahnen")

    t0 = time.time()

    # =================== JOINT STATES ===================

    # SEGMENTE (nur eigene joint_states)
    if segment_ids:
        logger.info("  → Joint States (Segmente)...")
        seg_joint = await conn.fetch(f"""
            WITH numbered AS (
                SELECT segment_id,
                       joint_1, joint_2, joint_3, joint_4, joint_5, joint_6,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM bahn_joint_states
                WHERE segment_id = ANY($1)
            )
            SELECT segment_id,
                   array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j1,
                   array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j2,
                   array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j3,
                   array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j4,
                   array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j5,
                   array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j6
            FROM numbered
            GROUP BY segment_id
        """, segment_ids)

        for row in seg_joint:
            if row['j1'] and len(row['j1']) > 0:
                result['joint'][row['segment_id']] = [
                    {'joint_1': row['j1'][i], 'joint_2': row['j2'][i], 'joint_3': row['j3'][i],
                     'joint_4': row['j4'][i], 'joint_5': row['j5'][i], 'joint_6': row['j6'][i]}
                    for i in range(len(row['j1']))
                ]

    # BAHNEN (alle joint_states über alle Segmente!)
    if bahn_ids:
        logger.info("  → Joint States (Bahnen)...")
        bahn_joint = await conn.fetch(f"""
            WITH numbered AS (
                SELECT bahn_id,
                       joint_1, joint_2, joint_3, joint_4, joint_5, joint_6,
                       ROW_NUMBER() OVER (PARTITION BY bahn_id ORDER BY segment_id, timestamp) as rn
                FROM bahn_joint_states
                WHERE bahn_id = ANY($1)
            )
            SELECT bahn_id,
                   array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j1,
                   array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j2,
                   array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j3,
                   array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j4,
                   array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j5,
                   array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as j6
            FROM numbered
            GROUP BY bahn_id
        """, bahn_ids)

        for row in bahn_joint:
            if row['j1'] and len(row['j1']) > 0:
                result['joint'][row['bahn_id']] = [
                    {'joint_1': row['j1'][i], 'joint_2': row['j2'][i], 'joint_3': row['j3'][i],
                     'joint_4': row['j4'][i], 'joint_5': row['j5'][i], 'joint_6': row['j6'][i]}
                    for i in range(len(row['j1']))
                ]

    logger.info(f"    ✓ Joint: {len(result['joint'])} IDs ({time.time() - t0:.1f}s)")

    # =================== POSITION SOLL ===================
    t0 = time.time()
    logger.info("  → Position Soll...")

    # SEGMENTE
    if segment_ids:
        seg_pos = await conn.fetch(f"""
            WITH numbered AS (
                SELECT segment_id, x_soll, y_soll, z_soll,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM bahn_position_soll
                WHERE segment_id = ANY($1)
            )
            SELECT segment_id,
                   array_agg(x_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as x,
                   array_agg(y_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as y,
                   array_agg(z_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as z
            FROM numbered
            GROUP BY segment_id
        """, segment_ids)

        for row in seg_pos:
            if row['x'] and len(row['x']) > 0:
                result['position'][row['segment_id']] = [
                    {'x_soll': row['x'][i], 'y_soll': row['y'][i], 'z_soll': row['z'][i]}
                    for i in range(len(row['x']))
                ]

    # BAHNEN
    if bahn_ids:
        bahn_pos = await conn.fetch(f"""
            WITH numbered AS (
                SELECT bahn_id, x_soll, y_soll, z_soll,
                       ROW_NUMBER() OVER (PARTITION BY bahn_id ORDER BY segment_id, timestamp) as rn
                FROM bahn_position_soll
                WHERE bahn_id = ANY($1)
            )
            SELECT bahn_id,
                   array_agg(x_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as x,
                   array_agg(y_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as y,
                   array_agg(z_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as z
            FROM numbered
            GROUP BY bahn_id
        """, bahn_ids)

        for row in bahn_pos:
            if row['x'] and len(row['x']) > 0:
                result['position'][row['bahn_id']] = [
                    {'x_soll': row['x'][i], 'y_soll': row['y'][i], 'z_soll': row['z'][i]}
                    for i in range(len(row['x']))
                ]

    logger.info(f"    ✓ Position: {len(result['position'])} IDs ({time.time() - t0:.1f}s)")

    # =================== ORIENTATION SOLL ===================
    t0 = time.time()
    logger.info("  → Orientation Soll...")

    # SEGMENTE
    if segment_ids:
        seg_ori = await conn.fetch(f"""
            WITH numbered AS (
                SELECT segment_id, qw_soll, qx_soll, qy_soll, qz_soll,
                       ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                FROM bahn_orientation_soll
                WHERE segment_id = ANY($1)
            )
            SELECT segment_id,
                   array_agg(qw_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qw,
                   array_agg(qx_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qx,
                   array_agg(qy_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qy,
                   array_agg(qz_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qz
            FROM numbered
            GROUP BY segment_id
        """, segment_ids)

        for row in seg_ori:
            if row['qw'] and len(row['qw']) > 0:
                result['orientation'][row['segment_id']] = [
                    {'qw_soll': row['qw'][i], 'qx_soll': row['qx'][i],
                     'qy_soll': row['qy'][i], 'qz_soll': row['qz'][i]}
                    for i in range(len(row['qw']))
                ]

    # BAHNEN
    if bahn_ids:
        bahn_ori = await conn.fetch(f"""
            WITH numbered AS (
                SELECT bahn_id, qw_soll, qx_soll, qy_soll, qz_soll,
                       ROW_NUMBER() OVER (PARTITION BY bahn_id ORDER BY segment_id, timestamp) as rn
                FROM bahn_orientation_soll
                WHERE bahn_id = ANY($1)
            )
            SELECT bahn_id,
                   array_agg(qw_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qw,
                   array_agg(qx_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qx,
                   array_agg(qy_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qy,
                   array_agg(qz_soll ORDER BY rn) FILTER (WHERE rn % {downsample_factor} = 1) as qz
            FROM numbered
            GROUP BY bahn_id
        """, bahn_ids)

        for row in bahn_ori:
            if row['qw'] and len(row['qw']) > 0:
                result['orientation'][row['bahn_id']] = [
                    {'qw_soll': row['qw'][i], 'qx_soll': row['qx'][i],
                     'qy_soll': row['qy'][i], 'qz_soll': row['qz'][i]}
                    for i in range(len(row['qw']))
                ]

    logger.info(f"    ✓ Orientation: {len(result['orientation'])} IDs ({time.time() - t0:.1f}s)")

def compute_all_embeddings(
    calculator: EmbeddingCalculator,
    data: Dict,
    id_to_bahn: Dict[str, str]
) -> List[Tuple]:
    """
    Berechnet alle drei Embeddings für alle IDs

    Returns: List[(segment_id, bahn_id, joint_emb_str, pos_emb_str, ori_emb_str, samples)]
    """
    rows = []

    all_ids = set(data['joint'].keys()) | set(data['position'].keys()) | set(data['orientation'].keys())

    logger.info(f"  → Computing embeddings for {len(all_ids)} IDs...")
    logger.info(f"  → id_to_bahn mapping has {len(id_to_bahn)} entries")  # ✅ DEBUG

    for segment_id in all_ids:
        # Joint
        joint_emb = None
        if segment_id in data['joint']:
            joint_emb = calculator.compute_joint_embedding(data['joint'][segment_id])

        # Position
        pos_emb = None
        if segment_id in data['position']:
            pos_emb = calculator.compute_position_embedding(data['position'][segment_id])

        # Orientation
        ori_emb = None
        if segment_id in data['orientation']:
            ori_emb = calculator.compute_orientation_embedding(data['orientation'][segment_id])

        # Skip wenn nichts berechnet wurde
        if joint_emb is None and pos_emb is None and ori_emb is None:
            continue

        # Convert to string
        joint_str = _array_to_str(joint_emb) if joint_emb is not None else None
        pos_str = _array_to_str(pos_emb) if pos_emb is not None else None
        ori_str = _array_to_str(ori_emb) if ori_emb is not None else None

        bahn_id = id_to_bahn.get(segment_id, segment_id)

        rows.append((
            segment_id,
            bahn_id,
            joint_str,
            pos_str,
            ori_str,
            calculator.joint_samples,
            calculator.position_samples,
            calculator.orientation_samples
        ))

    return rows


def _array_to_str(arr: np.ndarray) -> str:
    """Convert numpy array to PostgreSQL vector string"""
    return '[' + ','.join(str(x) for x in arr.tolist()) + ']'


async def bulk_insert_embeddings(conn, rows: List[Tuple]):
    """Bulk insert mit COPY"""
    t0 = time.time()

    # Temp table
    await conn.execute("""
        CREATE TEMP TABLE temp_embeddings (
            segment_id TEXT,
            bahn_id TEXT,
            joint_embedding TEXT,
            position_embedding TEXT,
            orientation_embedding TEXT,
            joint_sample_count INTEGER,
            position_sample_count INTEGER,
            orientation_sample_count INTEGER
        )
    """)

    # COPY
    await conn.copy_records_to_table(
        'temp_embeddings',
        records=rows,
        columns=['segment_id', 'bahn_id', 'joint_embedding', 'position_embedding',
                'orientation_embedding', 'joint_sample_count', 'position_sample_count',
                'orientation_sample_count']
    )
    logger.info(f"  ✓ COPY: {len(rows)} rows ({time.time()-t0:.1f}s)")

    # INSERT with conflict handling
    t0 = time.time()
    await conn.execute("""
        INSERT INTO bahn_embeddings
            (segment_id, bahn_id, joint_embedding, position_embedding, orientation_embedding,
             joint_sample_count, position_sample_count, orientation_sample_count)
        SELECT 
            segment_id, bahn_id,
            joint_embedding::vector,
            position_embedding::vector,
            orientation_embedding::vector,
            joint_sample_count,
            position_sample_count,
            orientation_sample_count
        FROM temp_embeddings
        ON CONFLICT (segment_id) DO UPDATE SET
            joint_embedding = EXCLUDED.joint_embedding,
            position_embedding = EXCLUDED.position_embedding,
            orientation_embedding = EXCLUDED.orientation_embedding,
            joint_sample_count = EXCLUDED.joint_sample_count,
            position_sample_count = EXCLUDED.position_sample_count,
            orientation_sample_count = EXCLUDED.orientation_sample_count
    """)
    logger.info(f"  ✓ INSERT ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate ALL Embeddings')
    parser.add_argument('--mode', choices=['full', 'segments-only', 'bahnen-only'],
                       default='full')
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--joint-samples', type=int, default=50)
    parser.add_argument('--position-samples', type=int, default=50)
    parser.add_argument('--orientation-samples', type=int, default=30)

    args = parser.parse_args()

    config = EmbeddingConfig(
        joint_samples=args.joint_samples,
        position_samples=args.position_samples,
        orientation_samples=args.orientation_samples
    )

    asyncio.run(populate_all_embeddings(config, args.limit, args.mode))