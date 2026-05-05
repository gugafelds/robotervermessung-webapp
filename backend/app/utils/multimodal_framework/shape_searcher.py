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
    ) -> Optional[Dict]:
        """
        Holt Embedding und parent traj_id für Target ID.

        Returns:
            {
                "embedding": List[float],
                "traj_id": str
            }
            oder None
        """
        try:
            embedding_col = f"{mode}_embedding"

            query = f"""
                SELECT 
                    traj_id,
                    {embedding_col}
                FROM motion.traj_embeddings
                WHERE seg_id = $1
            """

            result = await self.connection.fetchrow(query, target_id)

            if not result or result[embedding_col] is None:
                logger.warning(f"No {mode} embedding found for {target_id}")
                return None

            return {
                "embedding": result[embedding_col],
                "traj_id": result["traj_id"]
            }

        except Exception as e:
            logger.error(f"Error getting {mode} embedding for {target_id}: {e}")
            return None

    async def search_by_embedding(
            self,
            target_id: str,
            mode: str,
            limit: int = 100,
            candidate_ids: Optional[List[str]] = None,
            only_traj: bool = False,
            only_segments: bool = False
    ) -> List[Dict]:
        """
        Sucht ähnliche Bahnen/Segmente basierend auf Embedding

        Args:
            target_id: Target ID (kann Traj-ID oder Segment-ID sein)
            mode: 'joint', 'position', 'orientation', 'velocity', 'metadata'
            limit: Max Ergebnisse
            candidate_ids: Optional Pre-Filter Liste
            only_traj: Nur Bahnen (seg_id = traj_id)
            only_segments: Nur Segmente (seg_id != traj_id)

        Returns:
            List[Dict] mit seg_id, traj_id, distance, rank
        """

        try:
            target_data = await self.get_target_embedding(target_id, mode)

            if target_data is None:
                logger.error(f"Cannot get {mode} embedding for {target_id}")
                return []

            target_embedding = target_data["embedding"]
            parent_traj_id = target_data["traj_id"]

            embedding_col = f"{mode}_embedding"

            # 3. Baue WHERE Conditions
            #    - e.seg_id != $2        → schließt das Segment selbst aus
            #    - e.traj_id != $3       → schließt alle Segmente der gleichen Trajectory aus
            where_conditions = [
                "e.seg_id != $2",
                "e.traj_id != $3",
                f"e.{embedding_col} IS NOT NULL"
            ]

            # Filter für Bahnen/Segmente
            if only_traj:
                where_conditions.append("e.seg_id = e.traj_id")
            elif only_segments:
                where_conditions.append("e.seg_id != e.traj_id")

            where_clause = " AND ".join(where_conditions)

            # 4. SET HNSW parameter (außerhalb der Query)
            await self.connection.execute("SET hnsw.ef_search = 500;")

            # 5. Query
            if candidate_ids is not None and len(candidate_ids) > 0:
                # Mit Kandidaten-Filter
                where_conditions.append("e.seg_id = ANY($4)")
                where_clause = " AND ".join(where_conditions)

                query = f"""
                    SELECT 
                        e.seg_id,
                        e.traj_id,
                        e.{embedding_col} <=> $1::vector as distance
                    FROM motion.traj_embeddings e
                    WHERE {where_clause}
                    ORDER BY distance, e.seg_id
                    LIMIT $5
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,  # $1
                    target_id,         # $2 — seg_id != target_id
                    parent_traj_id,    # $3 — traj_id != parent_traj_id
                    candidate_ids,     # $4
                    limit              # $5
                )
            else:
                # Full Search
                query = f"""
                    SELECT 
                        e.seg_id,
                        e.traj_id,
                        e.{embedding_col} <=> $1::vector as distance
                    FROM motion.traj_embeddings e
                    WHERE {where_clause}
                    ORDER BY distance, e.seg_id
                    LIMIT $4
                """

                results = await self.connection.fetch(
                    query,
                    target_embedding,  # $1
                    target_id,         # $2 — seg_id != target_id
                    parent_traj_id,    # $3 — traj_id != parent_traj_id
                    limit              # $4
                )

            # 6. Format Results
            ranked_results = []
            for rank, row in enumerate(results, start=1):
                ranked_results.append({
                    'seg_id': row['seg_id'],
                    'traj_id': row['traj_id'],
                    'distance': float(row['distance']),
                    'rank': rank,
                    'mode': mode
                })

            filter_info = ""
            if only_traj:
                filter_info = "(only trajs)"
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
                FROM motion.traj_embeddings
                WHERE seg_id = $1
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