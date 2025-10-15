# backend/scripts/populate_embeddings.py

import asyncio
import asyncpg
import sys
from pathlib import Path

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
BATCH_SIZE = 50


async def populate_fast(n: int = 1000):
    """
    SCHNELLE Version - berechnet SEGMENT-Level + BAHN-Level Embeddings
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
            samples_per_joint=100,
            downsample_factor=1
        )

        async with pool.acquire() as conn:
            # === PHASE 1: BAHNEN ===
            logger.info("=" * 70)
            logger.info("PHASE 1: Lade Bahnen")
            logger.info("=" * 70)

            bahnen = await conn.fetch("""
                                      SELECT bahn_id
                                      FROM bahn_info
                                      ORDER BY recording_date DESC, bahn_id DESC
                                          LIMIT $1
                                      """, n)

            bahn_ids = [row['bahn_id'] for row in bahnen]
            logger.info(f"✓ Gefunden: {len(bahn_ids)} Bahnen")

            # === PHASE 2: SEGMENTE ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 2: Lade Segmente")
            logger.info("=" * 70)

            segments = await conn.fetch("""
                                        SELECT segment_id, bahn_id
                                        FROM bahn_meta
                                        WHERE bahn_id = ANY ($1)
                                          AND segment_id != bahn_id
                                        ORDER BY bahn_id, segment_id
                                        """, bahn_ids)

            logger.info(f"✓ Gefunden: {len(segments)} Segmente")

            # Mapping
            segment_to_bahn = {
                seg['segment_id']: seg['bahn_id']
                for seg in segments
            }

            # === PHASE 3: Prüfe existierende ===
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 3: Prüfe existierende Embeddings")
            logger.info("=" * 70)

            existing = await conn.fetch("""
                                        SELECT segment_id
                                        FROM bahn_joint_embeddings
                                        WHERE bahn_id = ANY ($1)
                                        """, bahn_ids)

            existing_ids = {row['segment_id'] for row in existing}
            logger.info(f"✓ Bereits vorhanden: {len(existing_ids)} Embeddings")

            # Fehlende Segmente
            missing_segment_ids = [
                seg['segment_id'] for seg in segments
                if seg['segment_id'] not in existing_ids
            ]

            # Fehlende Bahnen (wo segment_id = bahn_id)
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

            # === PHASE 4: SEGMENT-EMBEDDINGS berechnen ===
            if missing_segment_ids:
                logger.info("\n" + "=" * 70)
                logger.info("PHASE 4: Berechne SEGMENT-Embeddings")
                logger.info("=" * 70)

                total_segments = len(missing_segment_ids)
                processed_segments = 0

                for i in range(0, total_segments, BATCH_SIZE):
                    batch = missing_segment_ids[i:i + BATCH_SIZE]

                    # Berechne Batch
                    embeddings = await calculator.calculate_embedding_batch(batch)

                    # Speichere Batch
                    if embeddings:
                        count = await calculator.store_embeddings_batch(
                            embeddings,
                            segment_to_bahn
                        )
                        processed_segments += count

                        logger.info(
                            f"  [{processed_segments}/{total_segments}] "
                            f"Batch {i // BATCH_SIZE + 1}: "
                            f"{count}/{len(batch)} erfolgreich"
                        )
                    else:
                        logger.warning(
                            f"  Batch {i // BATCH_SIZE + 1}: "
                            f"Keine Embeddings berechnet"
                        )

                logger.info(f"✓ Segment-Embeddings: {processed_segments}/{total_segments}")

            # === PHASE 5: BAHN-EMBEDDINGS berechnen ===
            if missing_bahn_ids:
                logger.info("\n" + "=" * 70)
                logger.info("PHASE 5: Berechne BAHN-Embeddings")
                logger.info("=" * 70)

                total_bahnen = len(missing_bahn_ids)
                processed_bahnen = 0

                for i in range(0, total_bahnen, BATCH_SIZE):
                    batch = missing_bahn_ids[i:i + BATCH_SIZE]

                    # Berechne Batch (ganze Bahnen!)
                    embeddings = await calculator.calculate_bahn_embeddings_batch(batch)

                    # Speichere Batch (mit bahn_id = segment_id!)
                    if embeddings:
                        count = await calculator.store_bahn_embeddings_batch(embeddings)
                        processed_bahnen += count

                        logger.info(
                            f"  [{processed_bahnen}/{total_bahnen}] "
                            f"Batch {i // BATCH_SIZE + 1}: "
                            f"{count}/{len(batch)} erfolgreich"
                        )
                    else:
                        logger.warning(
                            f"  Batch {i // BATCH_SIZE + 1}: "
                            f"Keine Embeddings berechnet"
                        )

                logger.info(f"✓ Bahn-Embeddings: {processed_bahnen}/{total_bahnen}")

            # === ZUSAMMENFASSUNG ===
            logger.info("\n" + "=" * 70)
            logger.info("FERTIG!")
            logger.info("=" * 70)
            logger.info(f"✓ Segment-Embeddings: {processed_segments if missing_segment_ids else 0}")
            logger.info(f"✓ Bahn-Embeddings:    {processed_bahnen if missing_bahn_ids else 0}")
            logger.info(
                f"✓ Gesamt neu:         {(processed_segments if missing_segment_ids else 0) + (processed_bahnen if missing_bahn_ids else 0)}")
            logger.info(
                f"✓ Gesamt in DB:       {len(existing_ids) + (processed_segments if missing_segment_ids else 0) + (processed_bahnen if missing_bahn_ids else 0)}")

    finally:
        await pool.close()


async def recompute_bahn_embeddings(n: int = 1000):
    """
    NEU-Berechnung NUR der Bahn-Embeddings
    (z.B. wenn Segmente schon da sind, aber Bahnen fehlen)
    """

    logger.info("=" * 70)
    logger.info("RE-COMPUTE: Nur Bahn-Embeddings")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        calculator = FastJointEmbeddingCalculator(pool)

        async with pool.acquire() as conn:
            # Letzte N Bahnen
            bahnen = await conn.fetch("""
                                      SELECT bahn_id
                                      FROM bahn_info
                                      ORDER BY recording_date DESC, bahn_id DESC
                                          LIMIT $1
                                      """, n)

            bahn_ids = [row['bahn_id'] for row in bahnen]
            logger.info(f"Bahnen: {len(bahn_ids)}")

            # Prüfe welche Bahn-Embeddings fehlen
            existing = await conn.fetch("""
                                        SELECT segment_id
                                        FROM bahn_joint_embeddings
                                        WHERE bahn_id = segment_id
                                          AND bahn_id = ANY ($1)
                                        """, bahn_ids)

            existing_ids = {row['segment_id'] for row in existing}
            missing_ids = [bid for bid in bahn_ids if bid not in existing_ids]

            logger.info(f"Fehlende Bahn-Embeddings: {len(missing_ids)}")

            if not missing_ids:
                logger.info("🎉 Alle Bahn-Embeddings vorhanden!")
                return

            # Berechne in Batches
            total = len(missing_ids)
            processed = 0

            for i in range(0, total, BATCH_SIZE):
                batch = missing_ids[i:i + BATCH_SIZE]

                embeddings = await calculator.calculate_bahn_embeddings_batch(batch)

                if embeddings:
                    count = await calculator.store_bahn_embeddings_batch(embeddings)
                    processed += count
                    logger.info(f"[{processed}/{total}] Batch {i // BATCH_SIZE + 1}: {count}")

            logger.info(f"✓ Fertig: {processed}/{total}")

    finally:
        await pool.close()


if __name__ == "__main__":
    import time
    import argparse

    parser = argparse.ArgumentParser(
        description='Populate Joint Embeddings (Segment + Bahn Level)'
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
    logger.info("FAST Joint Embeddings Population")
    logger.info("Mode: " + args.mode.upper())
    logger.info("=" * 70)

    start = time.time()

    if args.mode == 'full':
        asyncio.run(populate_fast(args.limit))
    else:
        asyncio.run(recompute_bahn_embeddings(args.limit))

    duration = time.time() - start

    logger.info(f"\n⏱️  Gesamtzeit: {duration:.1f}s")