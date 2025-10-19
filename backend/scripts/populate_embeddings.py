# backend/scripts/populate_embeddings.py

import asyncio
import asyncpg
import sys
from pathlib import Path
import io
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.joint_calculator import FastJointEmbeddingCalculator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:manager@134.147.100.22:5432/robotervermessung"
LAST_N_BAHNEN = 1000


async def populate_fast_bulk(n: int = 1000):
    """
    BULK-OPTIMIERTE Version mit COPY
    Lädt ALLE Daten auf einmal, berechnet in Python, schreibt mit COPY
    """

    logger.info(f"Verbinde zu Datenbank...")
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        calculator = FastJointEmbeddingCalculator(
            pool,
            samples_per_joint=25,
            downsample_factor=5
        )

        async with pool.acquire() as conn:
            # === PHASE 1: BAHNEN laden ===
            logger.info("=" * 70)
            logger.info("PHASE 1: Lade Bahnen")
            logger.info("=" * 70)

            t0 = time.time()
            bahnen = await conn.fetch("""
                                      SELECT bahn_id
                                      FROM bahn_info
                                      ORDER BY recording_date DESC, bahn_id DESC
                                          LIMIT $1
                                      """, n)

            bahn_ids = [row['bahn_id'] for row in bahnen]
            logger.info(f"✓ Gefunden: {len(bahn_ids)} Bahnen ({time.time() - t0:.1f}s)")

            # === PHASE 2: SEGMENTE laden ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 2: Lade Segmente")
            logger.info("=" * 70)

            t0 = time.time()
            segments = await conn.fetch("""
                                        SELECT segment_id, bahn_id
                                        FROM bahn_meta
                                        WHERE bahn_id = ANY ($1)
                                          AND segment_id != bahn_id
                                        ORDER BY bahn_id, segment_id
                                        """, bahn_ids)

            logger.info(f"✓ Gefunden: {len(segments)} Segmente ({time.time() - t0:.1f}s)")

            # Mapping
            segment_to_bahn = {
                seg['segment_id']: seg['bahn_id']
                for seg in segments
            }

            # === PHASE 3: Existierende laden ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 3: Prüfe existierende Embeddings")
            logger.info("=" * 70)

            t0 = time.time()
            existing = await conn.fetch("""
                                        SELECT segment_id
                                        FROM bahn_joint_embeddings
                                        WHERE bahn_id = ANY ($1)
                                        """, bahn_ids)

            existing_ids = {row['segment_id'] for row in existing}
            logger.info(f"✓ Bereits vorhanden: {len(existing_ids)} ({time.time() - t0:.1f}s)")

            # Fehlende berechnen
            missing_segment_ids = [
                seg['segment_id'] for seg in segments
                if seg['segment_id'] not in existing_ids
            ]

            missing_bahn_ids = [
                bahn_id for bahn_id in bahn_ids
                if bahn_id not in existing_ids
            ]

            logger.info(f"✓ Zu berechnen:")
            logger.info(f"  - Segmente: {len(missing_segment_ids)}")
            logger.info(f"  - Bahnen:   {len(missing_bahn_ids)}")

            if len(missing_segment_ids) == 0 and len(missing_bahn_ids) == 0:
                logger.info("\n🎉 Alle Embeddings sind bereits vorhanden!")
                return

            # === PHASE 4: ALLE JOINT STATES auf einmal laden! ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 4: Lade ALLE Joint States (BULK)")
            logger.info("=" * 70)

            t0 = time.time()

            # Segmente - MIT ARRAY AGGREGATION!
            segment_states = {}
            if missing_segment_ids:
                all_segment_states = await conn.fetch(f"""
                    WITH numbered AS (
                        SELECT segment_id,
                               joint_1, joint_2, joint_3,
                               joint_4, joint_5, joint_6,
                               ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY timestamp) as rn
                        FROM bewegungsdaten.bahn_joint_states
                        WHERE segment_id = ANY ($1)
                    )
                    SELECT segment_id,
                           array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_1_arr,
                           array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_2_arr,
                           array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_3_arr,
                           array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_4_arr,
                           array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_5_arr,
                           array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_6_arr
                    FROM numbered
                    GROUP BY segment_id
                    ORDER BY segment_id
                """, missing_segment_ids)

                # Konvertiere Arrays zu Dict Format
                segment_states = {}
                for row in all_segment_states:
                    segment_id = row['segment_id']
                    # Prüfe ob Arrays vorhanden sind
                    if row['joint_1_arr'] is None or len(row['joint_1_arr']) == 0:
                        continue
                    # Erstelle Liste von Dicts aus den Arrays
                    segment_states[segment_id] = [
                        {
                            'joint_1': row['joint_1_arr'][i],
                            'joint_2': row['joint_2_arr'][i],
                            'joint_3': row['joint_3_arr'][i],
                            'joint_4': row['joint_4_arr'][i],
                            'joint_5': row['joint_5_arr'][i],
                            'joint_6': row['joint_6_arr'][i]
                        }
                        for i in range(len(row['joint_1_arr']))
                    ]

                logger.info(
                    f"✓ Segment States: {len(all_segment_states)} Segmente, {sum(len(v) for v in segment_states.values())} Punkte (aggregated+downsampled) ({time.time() - t0:.1f}s)")

            # Bahnen - MIT ARRAY AGGREGATION!
            t0 = time.time()
            bahn_states = {}
            if missing_bahn_ids:
                all_bahn_states = await conn.fetch(f"""
                    WITH numbered AS (
                        SELECT bahn_id,
                               joint_1, joint_2, joint_3,
                               joint_4, joint_5, joint_6,
                               ROW_NUMBER() OVER (PARTITION BY bahn_id ORDER BY segment_id, timestamp) as rn
                        FROM bewegungsdaten.bahn_joint_states
                        WHERE bahn_id = ANY ($1)
                    )
                    SELECT bahn_id,
                           array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_1_arr,
                           array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_2_arr,
                           array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_3_arr,
                           array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_4_arr,
                           array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_5_arr,
                           array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_6_arr
                    FROM numbered
                    GROUP BY bahn_id
                    ORDER BY bahn_id
                """, missing_bahn_ids)

                # Konvertiere Arrays zu Dict Format
                bahn_states = {}
                for row in all_bahn_states:
                    bahn_id = row['bahn_id']
                    # Prüfe ob Arrays vorhanden sind
                    if row['joint_1_arr'] is None or len(row['joint_1_arr']) == 0:
                        continue
                    bahn_states[bahn_id] = [
                        {
                            'joint_1': row['joint_1_arr'][i],
                            'joint_2': row['joint_2_arr'][i],
                            'joint_3': row['joint_3_arr'][i],
                            'joint_4': row['joint_4_arr'][i],
                            'joint_5': row['joint_5_arr'][i],
                            'joint_6': row['joint_6_arr'][i]
                        }
                        for i in range(len(row['joint_1_arr']))
                    ]

                logger.info(
                    f"✓ Bahn States: {len(all_bahn_states)} Bahnen, {sum(len(v) for v in bahn_states.values())} Punkte (aggregated+downsampled) ({time.time() - t0:.1f}s)")

            # === PHASE 5: EMBEDDINGS berechnen (in Python) ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 5: Berechne Embeddings (BULK)")
            logger.info("=" * 70)

            t0 = time.time()
            rows_to_insert = []

            # Segmente
            if missing_segment_ids:
                logger.info("Berechne Segment-Embeddings...")
                for segment_id in missing_segment_ids:
                    if segment_id not in segment_states:
                        continue

                    # Daten sind bereits downsampled im Query
                    embedding = calculator._create_embedding_from_trajectory(
                        segment_states[segment_id]
                    )

                    if embedding is not None:
                        embedding_str = '[' + ','.join(str(x) for x in embedding.tolist()) + ']'
                        rows_to_insert.append((
                            segment_id,
                            segment_to_bahn[segment_id],
                            embedding_str,
                            calculator.samples_per_joint
                        ))

                logger.info(f"✓ Segment-Embeddings: {len([r for r in rows_to_insert if r[0] != r[1]])} berechnet")

            # Bahnen
            if missing_bahn_ids:
                logger.info("Berechne Bahn-Embeddings...")
                for bahn_id in missing_bahn_ids:
                    if bahn_id not in bahn_states:
                        continue

                    # Daten sind bereits downsampled im Query
                    embedding = calculator._create_embedding_from_trajectory(
                        bahn_states[bahn_id]
                    )

                    if embedding is not None:
                        embedding_str = '[' + ','.join(str(x) for x in embedding.tolist()) + ']'
                        rows_to_insert.append((
                            bahn_id,  # segment_id = bahn_id für Bahnen!
                            bahn_id,
                            embedding_str,
                            calculator.samples_per_joint
                        ))

                logger.info(f"✓ Bahn-Embeddings: {len([r for r in rows_to_insert if r[0] == r[1]])} berechnet")

            logger.info(f"✓ Gesamt: {len(rows_to_insert)} Embeddings ({time.time() - t0:.1f}s)")

            # === PHASE 6: BULK INSERT mit COPY ===
            if rows_to_insert:
                logger.info("\n" + "=" * 70)
                logger.info("PHASE 6: Bulk Insert mit COPY")
                logger.info("=" * 70)

                t0 = time.time()

                # CREATE TEMP TABLE als TEXT (vector wird nicht unterstützt!)
                await conn.execute("""
                                   CREATE
                                   TEMP TABLE temp_embeddings (
                        segment_id TEXT,
                        bahn_id TEXT,
                        joint_embedding TEXT,
                        sample_count INTEGER
                    )
                                   """)

                # DIREKT mit copy_records_to_table
                records = [
                    (row[0], row[1], row[2], row[3])  # segment_id, bahn_id, embedding_str, sample_count
                    for row in rows_to_insert
                ]

                await conn.copy_records_to_table(
                    'temp_embeddings',
                    records=records,
                    columns=['segment_id', 'bahn_id', 'joint_embedding', 'sample_count']
                )

                logger.info(f"✓ COPY: {len(records)} Zeilen ({time.time() - t0:.1f}s)")

                # INSERT mit ON CONFLICT (mit ::vector cast!)
                t0 = time.time()
                result = await conn.execute("""
                                            INSERT INTO bahn_joint_embeddings
                                                (segment_id, bahn_id, joint_embedding, sample_count)
                                            SELECT segment_id,
                                                   bahn_id,
                                                   joint_embedding::vector, sample_count
                                            FROM temp_embeddings ON CONFLICT (segment_id) DO
                                            UPDATE SET
                                                joint_embedding = EXCLUDED.joint_embedding,
                                                updated_at = NOW()
                                            """)

                logger.info(f"✓ INSERT: {result} ({time.time() - t0:.1f}s)")

            # === ZUSAMMENFASSUNG ===
            logger.info("\n" + "=" * 70)
            logger.info("FERTIG!")
            logger.info("=" * 70)
            logger.info(f"✓ Neue Embeddings: {len(rows_to_insert)}")
            logger.info(f"✓ Gesamt in DB:    {len(existing_ids) + len(rows_to_insert)}")

    finally:
        await pool.close()


async def recompute_bahn_embeddings_bulk(n: int = 1000):
    """
    NEU-Berechnung NUR der Bahn-Embeddings (BULK-optimiert)
    """

    logger.info("=" * 70)
    logger.info("RE-COMPUTE: Nur Bahn-Embeddings (BULK)")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        calculator = FastJointEmbeddingCalculator(pool)

        async with pool.acquire() as conn:
            # Letzte N Bahnen
            t0 = time.time()
            bahnen = await conn.fetch("""
                                      SELECT bahn_id
                                      FROM bahn_info
                                      ORDER BY recording_date DESC, bahn_id DESC
                                          LIMIT $1
                                      """, n)

            bahn_ids = [row['bahn_id'] for row in bahnen]
            logger.info(f"Bahnen: {len(bahn_ids)} ({time.time() - t0:.1f}s)")

            # Existierende
            t0 = time.time()
            existing = await conn.fetch("""
                                        SELECT segment_id
                                        FROM bahn_joint_embeddings
                                        WHERE bahn_id = segment_id
                                          AND bahn_id = ANY ($1)
                                        """, bahn_ids)

            existing_ids = {row['segment_id'] for row in existing}
            missing_ids = [bid for bid in bahn_ids if bid not in existing_ids]

            logger.info(f"Fehlende: {len(missing_ids)} ({time.time() - t0:.1f}s)")

            if not missing_ids:
                logger.info("🎉 Alle Bahn-Embeddings vorhanden!")
                return

            # ALLE Joint States laden (bereits downsampled + aggregated!)
            t0 = time.time()
            all_states = await conn.fetch(f"""
                WITH numbered AS (
                    SELECT bahn_id,
                           joint_1, joint_2, joint_3,
                           joint_4, joint_5, joint_6,
                           ROW_NUMBER() OVER (PARTITION BY bahn_id ORDER BY segment_id, timestamp) as rn
                    FROM bewegungsdaten.bahn_joint_states
                    WHERE bahn_id = ANY ($1)
                )
                SELECT bahn_id,
                       array_agg(joint_1 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_1_arr,
                       array_agg(joint_2 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_2_arr,
                       array_agg(joint_3 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_3_arr,
                       array_agg(joint_4 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_4_arr,
                       array_agg(joint_5 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_5_arr,
                       array_agg(joint_6 ORDER BY rn) FILTER (WHERE rn % {calculator.downsample_factor} = 1) as joint_6_arr
                FROM numbered
                GROUP BY bahn_id
                ORDER BY bahn_id
            """, missing_ids)

            logger.info(f"States geladen: {len(all_states)} Bahnen (aggregated) ({time.time() - t0:.1f}s)")

            # Gruppiere
            bahn_states = {}
            for row in all_states:
                bahn_id = row['bahn_id']
                # Prüfe ob Arrays vorhanden sind
                if row['joint_1_arr'] is None or len(row['joint_1_arr']) == 0:
                    continue
                bahn_states[bahn_id] = [
                    {
                        'joint_1': row['joint_1_arr'][i],
                        'joint_2': row['joint_2_arr'][i],
                        'joint_3': row['joint_3_arr'][i],
                        'joint_4': row['joint_4_arr'][i],
                        'joint_5': row['joint_5_arr'][i],
                        'joint_6': row['joint_6_arr'][i]
                    }
                    for i in range(len(row['joint_1_arr']))
                ]

            # Berechne
            t0 = time.time()
            rows_to_insert = []
            for bahn_id in missing_ids:
                if bahn_id not in bahn_states:
                    continue

                # WICHTIG: Daten sind bereits downsampled,
                # also _create_embedding_from_trajectory verwenden
                embedding = calculator._create_embedding_from_trajectory(
                    bahn_states[bahn_id]
                )

                if embedding is not None:
                    embedding_str = '[' + ','.join(str(x) for x in embedding.tolist()) + ']'
                    rows_to_insert.append((
                        bahn_id,
                        bahn_id,
                        embedding_str,
                        calculator.samples_per_joint
                    ))

            logger.info(f"Embeddings berechnet: {len(rows_to_insert)} ({time.time() - t0:.1f}s)")

            # COPY
            if rows_to_insert:
                t0 = time.time()

                await conn.execute("""
                                   CREATE
                                   TEMP TABLE temp_bahn_embeddings (
                        segment_id TEXT,
                        bahn_id TEXT,
                        joint_embedding TEXT,
                        sample_count INTEGER
                    )
                                   """)

                # DIREKT mit copy_records_to_table
                records = [
                    (row[0], row[1], row[2], row[3])
                    for row in rows_to_insert
                ]

                await conn.copy_records_to_table(
                    'temp_bahn_embeddings',
                    records=records,
                    columns=['segment_id', 'bahn_id', 'joint_embedding', 'sample_count']
                )

                logger.info(f"COPY: {len(records)} ({time.time() - t0:.1f}s)")

                t0 = time.time()
                result = await conn.execute("""
                                            INSERT INTO bahn_joint_embeddings
                                                (segment_id, bahn_id, joint_embedding, sample_count)
                                            SELECT segment_id,
                                                   bahn_id,
                                                   joint_embedding::vector, sample_count
                                            FROM temp_bahn_embeddings ON CONFLICT (segment_id) DO
                                            UPDATE SET
                                                joint_embedding = EXCLUDED.joint_embedding,
                                                updated_at = NOW()
                                            """)

                logger.info(f"INSERT: {result} ({time.time() - t0:.1f}s)")
                logger.info(f"✓ Fertig: {len(rows_to_insert)}/{len(missing_ids)}")

    finally:
        await pool.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Populate Joint Embeddings (BULK-optimiert mit COPY)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'bahn-only'],
        default='full',
        help='full = Segmente + Bahnen, bahn-only = nur Bahnen (default: full)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Anzahl Bahnen (default: 1000)'
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("BULK Joint Embeddings Population (mit COPY)")
    logger.info("Mode: " + args.mode.upper())
    logger.info("=" * 70)

    start = time.time()

    if args.mode == 'full':
        asyncio.run(populate_fast_bulk(args.limit))
    else:
        asyncio.run(recompute_bahn_embeddings_bulk(args.limit))

    duration = time.time() - start

    logger.info(f"\n⏱️  Gesamtzeit: {duration:.1f}s")