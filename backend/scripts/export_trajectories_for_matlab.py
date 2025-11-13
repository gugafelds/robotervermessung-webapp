"""
Export Joint-Trajektorien aus PostgreSQL für MATLAB DTW-Baseline

Usage:
    python export_trajectories_for_matlab.py --output ./matlab_data --limit 100

Output:
    - trajectories.mat: MATLAB struct mit allen Trajektorien
    - metadata.csv: Metadaten für jede Trajektorie
"""

import asyncio
import asyncpg
import numpy as np
import argparse
import logging
from pathlib import Path
from scipy.io import savemat
import csv
import sys
import os

# Add parent directory to path to import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_segment_ids(conn, limit: int = None, only_bahnen: bool = True):
    """Holt segment_ids aus der Datenbank"""

    where_clause = "WHERE segment_id = bahn_id" if only_bahnen else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
        SELECT segment_id, bahn_id, duration, length, movement_type
        FROM bewegungsdaten.bahn_metadata
        {where_clause}
        ORDER BY segment_id
        {limit_clause}
    """

    results = await conn.fetch(query)
    logger.info(f"Fetched {len(results)} segment IDs")
    return results


async def fetch_joint_trajectory(conn, segment_id: str):
    """Holt Joint-Trajektorie für ein Segment"""

    query = """
        SELECT timestamp, joint_1, joint_2, joint_3, joint_4, joint_5, joint_6
        FROM bewegungsdaten.bahn_joint_states
        WHERE segment_id = $1
        ORDER BY timestamp
    """

    results = await conn.fetch(query, segment_id)

    if not results:
        return None

    # Convert to numpy array
    trajectory = np.array([
        [r['joint_1'], r['joint_2'], r['joint_3'],
         r['joint_4'], r['joint_5'], r['joint_6']]
        for r in results
    ], dtype=np.float64)

    timestamps = np.array([float(r['timestamp']) for r in results], dtype=np.float64)

    return {
        'trajectory': trajectory,  # (n_samples, 6)
        'timestamps': timestamps,   # (n_samples,)
        'n_samples': len(trajectory)
    }


async def fetch_embeddings_and_distances(conn, segment_ids: list):
    """Holt Embeddings und pre-computed Distanzen"""

    query = """
        SELECT
            e.segment_id,
            e.joint_embedding,
            e.position_embedding,
            e.orientation_embedding,
            e.velocity_embedding,
            e.acceleration_embedding
        FROM bewegungsdaten.bahn_embeddings e
        WHERE e.segment_id = ANY($1)
    """

    results = await conn.fetch(query, segment_ids)

    # Convert to dict
    embeddings = {}
    for r in results:
        embeddings[r['segment_id']] = {
            'joint': np.array(r['joint_embedding']) if r['joint_embedding'] else None,
            'position': np.array(r['position_embedding']) if r['position_embedding'] else None,
            'orientation': np.array(r['orientation_embedding']) if r['orientation_embedding'] else None,
            'velocity': np.array(r['velocity_embedding']) if r['velocity_embedding'] else None,
            'acceleration': np.array(r['acceleration_embedding']) if r['acceleration_embedding'] else None,
        }

    logger.info(f"Fetched embeddings for {len(embeddings)} segments")
    return embeddings


async def export_data(output_dir: Path, limit: int = None, only_bahnen: bool = True):
    """Hauptfunktion: Exportiert alle Daten für MATLAB"""

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 1. Hole Segment-IDs
        logger.info("Fetching segment metadata...")
        segments_meta = await fetch_segment_ids(conn, limit=limit, only_bahnen=only_bahnen)
        segment_ids = [s['segment_id'] for s in segments_meta]

        if not segment_ids:
            logger.error("No segments found!")
            return

        # 2. Hole Trajektorien
        logger.info("Fetching joint trajectories...")
        trajectories = {}
        metadata_list = []

        for i, seg_meta in enumerate(segments_meta):
            seg_id = seg_meta['segment_id']

            if (i + 1) % 10 == 0:
                logger.info(f"  Progress: {i + 1}/{len(segment_ids)}")

            traj_data = await fetch_joint_trajectory(conn, seg_id)

            if traj_data is None:
                logger.warning(f"  No trajectory data for {seg_id}")
                continue

            trajectories[seg_id] = traj_data

            metadata_list.append({
                'segment_id': seg_id,
                'bahn_id': seg_meta['bahn_id'],
                'duration': seg_meta['duration'],
                'length': seg_meta['length'],
                'movement_type': seg_meta['movement_type'],
                'n_samples': traj_data['n_samples']
            })

        logger.info(f"Successfully fetched {len(trajectories)} trajectories")

        # 3. Hole Embeddings
        logger.info("Fetching embeddings...")
        embeddings = await fetch_embeddings_and_distances(conn, list(trajectories.keys()))

        # 4. Export zu MATLAB .mat file
        logger.info("Creating MATLAB .mat file...")

        # Prepare data for MATLAB struct
        matlab_data = {
            'segment_ids': np.array([s for s in trajectories.keys()], dtype=object),
            'n_trajectories': len(trajectories)
        }

        # Add trajectories (as cell array for variable length)
        traj_list = []
        timestamps_list = []
        n_samples_list = []

        for seg_id in trajectories.keys():
            traj_list.append(trajectories[seg_id]['trajectory'])
            timestamps_list.append(trajectories[seg_id]['timestamps'])
            n_samples_list.append(trajectories[seg_id]['n_samples'])

        matlab_data['trajectories'] = np.array(traj_list, dtype=object)
        matlab_data['timestamps'] = np.array(timestamps_list, dtype=object)
        matlab_data['n_samples'] = np.array(n_samples_list, dtype=np.int32)

        # Add embeddings (fixed size, so regular array)
        joint_emb_list = []
        position_emb_list = []

        for seg_id in trajectories.keys():
            if seg_id in embeddings and embeddings[seg_id]['joint'] is not None:
                joint_emb_list.append(embeddings[seg_id]['joint'])
                position_emb_list.append(embeddings[seg_id]['position'] if embeddings[seg_id]['position'] is not None else np.zeros(300))
            else:
                joint_emb_list.append(np.zeros(300))  # Placeholder
                position_emb_list.append(np.zeros(300))

        matlab_data['joint_embeddings'] = np.array(joint_emb_list, dtype=np.float64)
        matlab_data['position_embeddings'] = np.array(position_emb_list, dtype=np.float64)

        # Save to .mat file
        mat_file = output_dir / 'trajectories.mat'
        savemat(str(mat_file), matlab_data, do_compression=True)
        logger.info(f"✅ Saved MATLAB file: {mat_file}")

        # 5. Export metadata als CSV
        csv_file = output_dir / 'metadata.csv'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['segment_id', 'bahn_id', 'duration', 'length', 'movement_type', 'n_samples'])
            writer.writeheader()
            writer.writerows(metadata_list)

        logger.info(f"✅ Saved metadata CSV: {csv_file}")

        # 6. Summary
        logger.info("\n" + "="*60)
        logger.info("EXPORT SUMMARY")
        logger.info("="*60)
        logger.info(f"Total trajectories exported: {len(trajectories)}")
        logger.info(f"Output directory: {output_dir.absolute()}")
        logger.info(f"Files created:")
        logger.info(f"  - trajectories.mat ({mat_file.stat().st_size / 1024 / 1024:.2f} MB)")
        logger.info(f"  - metadata.csv")
        logger.info("="*60)

    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description='Export trajectories for MATLAB DTW baseline')
    parser.add_argument('--output', type=str, default='./matlab_data',
                        help='Output directory (default: ./matlab_data)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of trajectories (default: all)')
    parser.add_argument('--all-segments', action='store_true',
                        help='Export all segments, not just bahnen (default: only bahnen)')

    args = parser.parse_args()

    output_dir = Path(args.output)

    asyncio.run(export_data(
        output_dir=output_dir,
        limit=args.limit,
        only_bahnen=not args.all_segments
    ))


if __name__ == '__main__':
    main()
