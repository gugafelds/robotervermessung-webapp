# backend/app/utils/shape_searcher.py

import asyncpg
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ShapeSearcher:
    """
    Embedding-basierte Shape Similarity Search
    Nutzt pgvector <->> operator für cosine distance
    """

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection

    async def get_target_embedding(
            self,
            target_id: str,
            mode: str
    ) -> Optional[List[float]]:
        """
        Holt Embedding für Target ID

        Args:
            target_id: Segment/Bahn ID
            mode: 'joint', 'position', 'orientation'

        Returns:
            Embedding als List[float] oder None
        """
        try:
            embedding_col = f"{mode}_embedding"

            query = f"""
                SELECT {embedding_col}
                FROM bewegungsdaten.bahn_embeddings
                WHERE segment_id = $1
            """

            result = await self.connection.fetchrow(query, target_id)

            if not result or result[embedding_col] is None:
                logger.warning(f"No {mode} embedding found for {target_id}")
                return None

            # pgvector gibt string zurück: "[0.1,0.2,...]"
            embedding = result[embedding_col]

            return embedding

        except Exception as e:
            logger.error(f"Error getting {mode} embedding for {target_id}: {e}")
            return None

    async def search_by_embedding(
            self,
            target_id: str,
            mode: str,
            limit: int = 100,
            candidate_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Sucht ähnliche Bahnen/Segmente basierend auf Embedding

        Args:
            target_id: Target ID
            mode: 'joint', 'position', 'orientation'
            limit: Max Ergebnisse
            candidate_ids: Optional Pre-Filter Liste (für Efficiency!)

        Returns:
            List[Dict] mit segment_id, bahn_id, distance, rank
        """
        try:
            # 1. Hole Target Embedding
            target_embedding = await self.get_target_embedding(target_id, mode)

            if target_embedding is None:
                logger.error(f"Cannot get {mode} embedding for {target_id}")
                return []

            embedding_col = f"{mode}_embedding"

            # 2. Query: Mit oder ohne Candidate Pre-Filter
            if candidate_ids is not None and len(candidate_ids) > 0:
                # Pre-Filtered Search (SCHNELL!)
                query = f"""
                    SELECT 
                        segment_id,
                        bahn_id,
                        {embedding_col} <-> $1::vector as distance
                    FROM bewegungsdaten.bahn_embeddings
                    WHERE segment_id = ANY($2)
                      AND segment_id != $3
                      AND {embedding_col} IS NOT NULL
                    ORDER BY distance
                    LIMIT $4
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,
                    candidate_ids,
                    target_id,
                    limit
                )
            else:
                # Full Search (LANGSAM, aber vollständig)
                query = f"""
                    SELECT 
                        segment_id,
                        bahn_id,
                        {embedding_col} <-> $1::vector as distance
                    FROM bewegungsdaten.bahn_embeddings
                    WHERE segment_id != $2
                      AND {embedding_col} IS NOT NULL
                    ORDER BY distance
                    LIMIT $3
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,
                    target_id,
                    limit
                )

            # 3. Format Results
            ranked_results = []
            for rank, row in enumerate(results, start=1):
                ranked_results.append({
                    'segment_id': row['segment_id'],
                    'bahn_id': row['bahn_id'],
                    'distance': float(row['distance']),
                    'rank': rank,
                    'mode': mode
                })

            logger.info(
                f"{mode.upper()} search for {target_id}: "
                f"Found {len(ranked_results)} results "
                f"{'(pre-filtered)' if candidate_ids else '(full search)'}"
            )

            return ranked_results

        except Exception as e:
            logger.error(f"Error in {mode} embedding search for {target_id}: {e}")
            return []

    async def search_multi_modal(
            self,
            target_id: str,
            modes: List[str] = None,
            limit: int = 100,
            candidate_ids: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Sucht mit ALLEN Embedding-Modi parallel

        Args:
            target_id: Target ID
            modes: Welche Modi? (default: ['joint', 'position', 'orientation'])
            limit: Ergebnisse pro Modus
            candidate_ids: Optional Pre-Filter

        Returns:
            Dict: {
                'joint': [results],
                'position': [results],
                'orientation': [results]
            }
        """
        if modes is None:
            modes = ['joint', 'position', 'orientation']

        results = {}

        for mode in modes:
            mode_results = await self.search_by_embedding(
                target_id=target_id,
                mode=mode,
                limit=limit,
                candidate_ids=candidate_ids
            )
            results[mode] = mode_results

        logger.info(
            f"Multi-modal search for {target_id}: "
            f"{', '.join([f'{m}={len(results[m])}' for m in modes])}"
        )

        return results

    async def check_embeddings_exist(self, target_id: str) -> Dict[str, bool]:
        """
        Prüft welche Embeddings für Target vorhanden sind

        Returns:
            Dict: {'joint': True, 'position': False, 'orientation': True}
        """
        try:
            query = """
                    SELECT joint_embedding IS NOT NULL       as has_joint, \
                           position_embedding IS NOT NULL    as has_position, \
                           orientation_embedding IS NOT NULL as has_orientation
                    FROM bewegungsdaten.bahn_embeddings
                    WHERE segment_id = $1 \
                    """

            result = await self.connection.fetchrow(query, target_id)

            if not result:
                return {'joint': False, 'position': False, 'orientation': False}

            return {
                'joint': result['has_joint'],
                'position': result['has_position'],
                'orientation': result['has_orientation']
            }

        except Exception as e:
            logger.error(f"Error checking embeddings for {target_id}: {e}")
            return {'joint': False, 'position': False, 'orientation': False}