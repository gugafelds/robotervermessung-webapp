# backend/scripts/test_similarity.py

import asyncio
import asyncpg
import sys
from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.embedding_calculator import EmbeddingCalculator
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:manager@134.147.100.22:5432/robotervermessung"


async def plot_joint_states(conn, target_bahn_id: str, similar_bahn_ids: list):
    """
    Plottet die Joint States der Target-Bahn und der ersten 5 ähnlichen Bahnen
    """
    logger.info("\n" + "=" * 70)
    logger.info("PLOTTING JOINT STATES")
    logger.info("=" * 70)

    # Begrenze auf erste 5
    bahn_ids_to_plot = [target_bahn_id] + similar_bahn_ids[:5]

    # Erstelle Figure mit 6 Subplots (ein Joint pro Subplot)
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle(f'Joint States Vergleich - Target: {target_bahn_id}', fontsize=16, fontweight='bold')
    axes = axes.flatten()

    joint_names = ['Joint 1', 'Joint 2', 'Joint 3', 'Joint 4', 'Joint 5', 'Joint 6']
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']

    for idx, bahn_id in enumerate(bahn_ids_to_plot):
        # Lade Joint States
        joint_data = await conn.fetch("""
                                      SELECT joint_1, joint_2, joint_3, joint_4, joint_5, joint_6
                                      FROM bewegungsdaten.bahn_joint_states
                                      WHERE bahn_id = $1
                                      ORDER BY timestamp DESC
                                      """, bahn_id)

        if not joint_data:
            logger.warning(f"Keine Joint-Daten für Bahn {bahn_id}")
            continue

        # Konvertiere zu numpy arrays
        joints = {
            'joint_1': [row['joint_1'] for row in joint_data],
            'joint_2': [row['joint_2'] for row in joint_data],
            'joint_3': [row['joint_3'] for row in joint_data],
            'joint_4': [row['joint_4'] for row in joint_data],
            'joint_5': [row['joint_5'] for row in joint_data],
            'joint_6': [row['joint_6'] for row in joint_data],
        }

        # Plotte jeden Joint
        for joint_idx, (joint_key, joint_values) in enumerate(joints.items()):
            ax = axes[joint_idx]

            # Label für Legende
            if idx == 0:
                label = f'Target ({bahn_id})'
                linestyle = '-'
                linewidth = 2.5
                alpha = 1.0
            else:
                label = f'Similar #{idx} ({bahn_id})'
                linestyle = '--'
                linewidth = 1.5
                alpha = 0.7

            # Plotte die Joint-Werte
            ax.plot(joint_values,
                    label=label,
                    color=colors[idx % len(colors)],
                    linestyle=linestyle,
                    linewidth=linewidth,
                    alpha=alpha)

            ax.set_title(joint_names[joint_idx], fontweight='bold')
            ax.set_xlabel('Event Index')
            ax.set_ylabel('Joint Angle [°]')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=8)

    plt.tight_layout()

    # Speichere Plot
    output_file = f'joint_states_comparison_{target_bahn_id}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Plot gespeichert: {output_file}")

    # Zeige Plot (optional - auskommentieren wenn nicht gewünscht)
    # plt.show()

    plt.close()


async def test_bahn_similarity(
        target_bahn_id: str,
        bahn_limit: int = 10,
        plot_joints: bool = False
):
    """
    Test BAHN-Level Similarity
    Nutzt pgvector Index! (bahn_id = segment_id)
    """
    logger.info("=" * 70)
    logger.info("BAHN-LEVEL SIMILARITY TEST")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        async with pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            # Lade Target Bahn-Embedding
            target = await conn.fetchrow("""
                                         SELECT joint_embedding, segment_id
                                         FROM bahn_embeddings
                                         WHERE bahn_id = $1
                                           AND segment_id = $1
                                         """, target_bahn_id)

            if not target:
                logger.error(f"Bahn {target_bahn_id} hat kein Bahn-Embedding!")
                logger.info("Tipp: Führen Sie populate_embeddings.py aus")
                return

            target_embedding = target['joint_embedding']

            # Finde ähnliche Bahnen (mit pgvector Index!)
            results = await conn.fetch("""
                                       SELECT bahn_id,
                                              segment_id,
                                              joint_embedding <-> $1::vector AS distance
                                       FROM bahn_embeddings
                                       WHERE bahn_id = segment_id
                                         AND bahn_id != $2
                                       ORDER BY joint_embedding <-> $1::vector
                                           LIMIT $3
                                       """, target_embedding, target_bahn_id, bahn_limit)

            # Lade Target Info
            target_info = await conn.fetchrow("""
                                              SELECT bi.robot_model,
                                                     bi.recording_date,
                                                     bm.meta_value,
                                                     COUNT(DISTINCT bje.segment_id) - 1 as segment_count
                                              FROM bahn_info bi
                                                       LEFT JOIN bahn_meta bm
                                                                 ON bi.bahn_id = bm.bahn_id
                                                                     AND bi.bahn_id = bm.segment_id
                                                       LEFT JOIN bahn_embeddings bje
                                                                 ON bi.bahn_id = bje.bahn_id
                                              WHERE bi.bahn_id = $1
                                              GROUP BY bi.robot_model, bi.recording_date, bm.meta_value
                                              """, target_bahn_id)

            # Target Info ausgeben
            logger.info(f"\nTARGET BAHN: {target_bahn_id}")
            if target_info:
                logger.info(f"  Segmente:      {target_info['segment_count']}")
                logger.info(f"  Robot:         {target_info['robot_model']}")
                logger.info(f"  Recorded:      {target_info['recording_date']}")
                if target_info['meta_value']:
                    logger.info(f"  Meta-Value:    {target_info['meta_value']:.2f}")

            # Ähnliche Bahnen
            logger.info(f"\n{'Rank':<6} {'Bahn ID':<20} {'Distance':<12} {'Robot':<15}")
            logger.info("-" * 70)

            similar_bahn_ids = []
            for i, row in enumerate(results, 1):
                bahn_id = row['bahn_id']
                similar_bahn_ids.append(bahn_id)

                # Lade Info
                info = await conn.fetchrow("""
                                           SELECT bi.robot_model,
                                                  COUNT(DISTINCT bje.segment_id) - 1 as segment_count
                                           FROM bahn_info bi
                                                    LEFT JOIN bahn_embeddings bje
                                                              ON bi.bahn_id = bje.bahn_id
                                           WHERE bi.bahn_id = $1
                                           GROUP BY bi.robot_model
                                           """, bahn_id)

                logger.info(
                    f"{i:<6} {bahn_id:<20} {row['distance']:<12.4f} "
                    f"{info['robot_model'] if info else 'N/A':<15}"
                )

            # Plotte Joint States wenn gewünscht
            if plot_joints and similar_bahn_ids:
                await plot_joint_states(conn, target_bahn_id, similar_bahn_ids)

    finally:
        await pool.close()


async def test_segment_similarity(
        target_bahn_id: str,
        segment_limit: int = 5
):
    """
    Test SEGMENT-Level Similarity
    Für JEDES Segment der Bahn
    """
    logger.info("=" * 70)
    logger.info("SEGMENT-LEVEL SIMILARITY TEST")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        async with pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            # Lade alle Segmente der Target-Bahn
            target_segments = await conn.fetch("""
                                               SELECT segment_id, joint_embedding
                                               FROM bahn_embeddings
                                               WHERE bahn_id = $1
                                                 AND segment_id != $1
                                               ORDER BY segment_id
                                               """, target_bahn_id)

            if not target_segments:
                logger.error(f"Bahn {target_bahn_id} hat keine Segment-Embeddings!")
                return

            logger.info(f"\nTarget Bahn: {target_bahn_id}")
            logger.info(f"Segmente: {len(target_segments)}")
            logger.info("=" * 70)

            # Für jedes Target-Segment
            for target_seg in target_segments[:3]:  # Nur erste 3 als Beispiel
                segment_id = target_seg['segment_id']
                embedding = target_seg['joint_embedding']

                # Finde ähnliche Segmente (mit pgvector Index!)
                similar = await conn.fetch("""
                                           SELECT segment_id,
                                                  bahn_id,
                                                  joint_embedding <-> $1::vector AS distance
                                           FROM bahn_embeddings
                                           WHERE segment_id != bahn_id
                      AND segment_id != $2
                                             AND bahn_id != $3
                                           ORDER BY joint_embedding <-> $1::vector
                                               LIMIT $4
                                           """, embedding, segment_id, target_bahn_id, segment_limit)

                # Lade Target-Info
                target_info = await conn.fetchrow("""
                                                  SELECT length, duration, meta_value
                                                  FROM bahn_meta
                                                  WHERE segment_id = $1
                                                  """, segment_id)

                logger.info(f"\n--- {segment_id} ---")
                if target_info:
                    logger.info(
                        f"Length: {target_info['length']:.2f}mm, "
                        f"Duration: {target_info['duration']:.3f}s"
                    )

                logger.info(f"\n  {'Rank':<6} {'Segment ID':<30} {'Distance':<10}")
                for i, sim in enumerate(similar, 1):
                    logger.info(
                        f"  {i:<6} {sim['segment_id']:<30} {sim['distance']:<10.4f}"
                    )

    finally:
        await pool.close()


async def test_hierarchical_similarity(
        target_bahn_id: str,
        bahn_limit: int = 10,
        segment_limit: int = 5,
        plot_joints: bool = False
):
    """
    Test HIERARCHICAL Similarity (Bahn + Segment)
    """
    logger.info("=" * 70)
    logger.info("HIERARCHICAL JOINT SIMILARITY TEST")
    logger.info("=" * 70)
    logger.info(f"Target Bahn: {target_bahn_id}")
    logger.info(f"Bahn Limit: {bahn_limit}")
    logger.info(f"Segment Limit: {segment_limit}")
    logger.info("=" * 70)

    pool = await asyncpg.create_pool(
        DATABASE_URL,
        server_settings={'search_path': 'bewegungsdaten, public'}
    )

    try:
        async with pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            # === PHASE 1: BAHN-LEVEL ===
            logger.info("\n[Phase 1/2] Bahn-Level Similarity...")

            target_bahn = await conn.fetchrow("""
                                              SELECT joint_embedding
                                              FROM bahn_embeddings
                                              WHERE bahn_id = $1
                                                AND segment_id = $1
                                              """, target_bahn_id)

            if not target_bahn:
                logger.error(f"Bahn {target_bahn_id} hat kein Bahn-Embedding!")
                return

            bahn_results = await conn.fetch("""
                                            SELECT bahn_id,
                                                   joint_embedding <-> $1::vector AS distance
                                            FROM bahn_embeddings
                                            WHERE bahn_id = segment_id
                                              AND bahn_id != $2
                                            ORDER BY joint_embedding <-> $1::vector
                                                LIMIT $3
                                            """, target_bahn['joint_embedding'], target_bahn_id, bahn_limit)

            logger.info(f"✓ Gefunden: {len(bahn_results)} ähnliche Bahnen")

            # === PHASE 2: SEGMENT-LEVEL ===
            logger.info("\n[Phase 2/2] Segment-Level Similarity...")

            target_segments = await conn.fetch("""
                                               SELECT segment_id, joint_embedding
                                               FROM bahn_embeddings
                                               WHERE bahn_id = $1
                                                 AND segment_id != $1
                                               ORDER BY segment_id
                                               """, target_bahn_id)

            segment_results = []
            for target_seg in target_segments:
                similar = await conn.fetch("""
                                           SELECT segment_id,
                                                  bahn_id,
                                                  joint_embedding <-> $1::vector AS distance
                                           FROM bahn_embeddings
                                           WHERE segment_id != bahn_id
                      AND segment_id != $2
                                             AND bahn_id != $3
                                           ORDER BY joint_embedding <-> $1::vector
                                               LIMIT $4
                                           """, target_seg['joint_embedding'], target_seg['segment_id'],
                                           target_bahn_id, segment_limit)

                segment_results.append({
                    'target_segment_id': target_seg['segment_id'],
                    'similar_segments': [dict(s) for s in similar]
                })

            logger.info(f"✓ Bearbeitet: {len(segment_results)} Segmente")

            # === AUSGABE ===
            logger.info("\n" + "=" * 70)
            logger.info("BAHN-LEVEL RESULTS")
            logger.info("=" * 70)

            logger.info(f"\nTarget: {target_bahn_id}")
            logger.info(f"Gefunden: {len(bahn_results)} ähnliche Bahnen\n")

            similar_bahn_ids = []
            for i, bahn in enumerate(bahn_results[:10], 1):
                similar_bahn_ids.append(bahn['bahn_id'])
                logger.info(
                    f"  {i}. {bahn['bahn_id']} | "
                    f"Distance: {bahn['distance']:.4f}"
                )

            logger.info("\n" + "=" * 70)
            logger.info("SEGMENT-LEVEL RESULTS")
            logger.info("=" * 70)

            logger.info(f"Target Segmente: {len(segment_results)}")

            if segment_results:
                first = segment_results[1] if len(segment_results) > 1 else segment_results[0]
                logger.info(f"\nBeispiel: {first['target_segment_id']}")
                for i, sim in enumerate(first['similar_segments'][:5], 1):
                    logger.info(
                        f"  {i}. {sim['segment_id']} | "
                        f"Distance: {sim['distance']:.4f}"
                    )

            # SUMMARY
            logger.info("\n" + "=" * 70)
            logger.info("SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Similar Bahnen:     {len(bahn_results)}")
            logger.info(f"Target Segmente:    {len(segment_results)}")
            logger.info(f"Method:             joint_embedding_pgvector")
            logger.info(f"Dimensions:         150 (25 samples × 6 joints)")
            logger.info(f"Index:              HNSW (pgvector)")

            # Plotte Joint States wenn gewünscht
            if plot_joints and similar_bahn_ids:
                await plot_joint_states(conn, target_bahn_id, similar_bahn_ids)

    finally:
        await pool.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Teste Joint Embedding Similarity (Hierarchical)'
    )
    parser.add_argument(
        'bahn_id',
        type=str,
        help='Target Bahn ID'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['bahn', 'segment', 'hierarchical'],
        default='hierarchical',
        help='Test-Modus (default: hierarchical)'
    )
    parser.add_argument(
        '--bahn-limit',
        type=int,
        default=10,
        help='Anzahl ähnlicher Bahnen (default: 10)'
    )
    parser.add_argument(
        '--segment-limit',
        type=int,
        default=10,
        help='Anzahl ähnlicher Segmente (default: 5)'
    )
    parser.add_argument(
        '--plot-joints',
        action='store_true',
        help='Plotte Joint States der ersten 5 ähnlichen Bahnen'
    )

    args = parser.parse_args()

    if args.mode == 'bahn':
        asyncio.run(test_bahn_similarity(args.bahn_id, args.bahn_limit, args.plot_joints))
    elif args.mode == 'segment':
        asyncio.run(test_segment_similarity(args.bahn_id, args.segment_limit))
    else:
        asyncio.run(test_hierarchical_similarity(
            args.bahn_id,
            args.bahn_limit,
            args.segment_limit,
            args.plot_joints
        ))