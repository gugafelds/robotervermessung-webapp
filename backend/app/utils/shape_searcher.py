# backend/app/utils/shape_searcher.py

import asyncpg
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ShapeSearcher:
    """
    Embedding-basierte Shape Similarity Search
    Nutzt pgvector <=> operator für cosine distance
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
            candidate_ids: Optional[List[str]] = None,
            only_bahnen: bool = False,
            only_segments: bool = False
    ) -> List[Dict]:
        """
        Sucht ähnliche Bahnen/Segmente basierend auf Embedding

        Args:
            target_id: Target ID
            mode: 'joint', 'position', 'orientation', 'velocity', 'metadata'
            limit: Max Ergebnisse
            candidate_ids: Optional Pre-Filter Liste
            only_bahnen: Nur Bahnen (segment_id = bahn_id)
            only_segments: Nur Segmente (segment_id != bahn_id)

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

            # 2. Baue WHERE Conditions
            where_conditions = [
                f"e.segment_id != $2",
                f"e.{embedding_col} IS NOT NULL"
            ]

            # Filter für Bahnen/Segmente
            if only_bahnen:
                where_conditions.append("e.segment_id = e.bahn_id")
                lambda_factor = 1
            elif only_segments:
                where_conditions.append("e.segment_id != e.bahn_id")
                lambda_factor = 1

            where_clause = " AND ".join(where_conditions)

            # ⭐ 3. SET HNSW parameter ERST (außerhalb der Query)
            await self.connection.execute("SET LOCAL hnsw.ef_search = 100;")

            # 4. Query
            if candidate_ids is not None and len(candidate_ids) > 0:
                # Mit Kandidaten-Filter
                where_conditions.append("e.segment_id = ANY($3)")
                where_clause = " AND ".join(where_conditions)

                query = f"""
                    SELECT 
                        e.segment_id,
                        e.bahn_id,
                        e.{embedding_col} <=> $1::vector as distance
                    FROM bewegungsdaten.bahn_embeddings e
                    WHERE {where_clause}
                    ORDER BY distance
                    LIMIT $4
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,
                    target_id,
                    candidate_ids,
                    limit*lambda_factor
                )
            else:
                # Full Search
                query = f"""
                    SELECT 
                        e.segment_id,
                        e.bahn_id,
                        e.{embedding_col} <=> $1::vector as distance
                    FROM bewegungsdaten.bahn_embeddings e
                    WHERE {where_clause}
                    ORDER BY distance
                    LIMIT $3
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,
                    target_id,
                    limit*lambda_factor
                )

            # 5. Format Results
            ranked_results = []
            for rank, row in enumerate(results, start=1):
                ranked_results.append({
                    'segment_id': row['segment_id'],
                    'bahn_id': row['bahn_id'],
                    'distance': float(row['distance']),
                    'rank': rank,
                    'mode': mode
                })

            filter_info = ""
            if only_bahnen:
                filter_info = "(only bahnen)"
            elif only_segments:
                filter_info = "(only segments)"

            logger.info(
                f"{mode.upper()} search for {target_id}: "
                f"Found {len(ranked_results)} results {filter_info}"
            )

            return ranked_results

        except Exception as e:
            logger.error(f"Error in {mode} embedding search for {target_id}: {e}")
            return []

    async def check_embeddings_exist(self, target_id: str) -> Dict[str, bool]:
        """
        Prüft welche Embeddings für Target vorhanden sind

        Returns:
            Dict: {'joint': True, 'position': False, 'orientation': True}
        """
        try:
            query = """
                SELECT joint_embedding IS NOT NULL       as has_joint,
                       position_embedding IS NOT NULL    as has_position,
                       orientation_embedding IS NOT NULL as has_orientation,
                       velocity_embedding IS NOT NULL    as has_velocity,
                       metadata_embedding IS NOT NULL    as has_metadata
                FROM bewegungsdaten.bahn_embeddings
                WHERE segment_id = $1
            """

            result = await self.connection.fetchrow(query, target_id)

            if not result:
                return {
                    'joint': False, 
                    'position': False, 
                    'orientation': False, 
                    'velocity': False, 
                    'metadata': False
                }

            return {
                'joint': result['has_joint'],
                'position': result['has_position'],
                'orientation': result['has_orientation'],
                'velocity': result['has_velocity'],
                'metadata': result['has_metadata']
            }

        except Exception as e:
            logger.error(f"Error checking embeddings for {target_id}: {e}")
            return {
                'joint': False, 
                'position': False, 
                'orientation': False, 
                'velocity': False, 
                'metadata': False
            }