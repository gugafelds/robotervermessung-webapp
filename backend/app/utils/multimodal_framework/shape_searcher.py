# backend/app/utils/multimodal_framework/shape_searcher.py

import asyncpg
import numpy as np
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

    async def get_target_embedding(self, target_id: str, mode: str) -> Optional[Dict]:
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
                "traj_id":   result["traj_id"]
            }
        except Exception as e:
            logger.error(f"Error getting {mode} embedding for {target_id}: {e}")
            return None

    async def search_by_embedding(
            self,
            target_id:     str,
            mode:          str,
            limit:         int            = 100,
            candidate_ids: Optional[List[str]] = None,
            only_traj:     bool           = False,
            only_segments: bool           = False,
    ) -> List[Dict]:
        try:
            target_data = await self.get_target_embedding(target_id, mode)
            if target_data is None:
                logger.error(f"Cannot get {mode} embedding for {target_id}")
                return []

            target_embedding = target_data["embedding"]
            parent_traj_id   = target_data["traj_id"]
            embedding_col    = f"{mode}_embedding"

            # Baue WHERE Conditions
            where_conditions = [
                "e.seg_id != $2",
                "e.traj_id != $3",
                f"e.{embedding_col} IS NOT NULL"
            ]

            if only_traj:
                where_conditions.append("e.seg_id = e.traj_id")
            elif only_segments:
                where_conditions.append("e.seg_id != e.traj_id")

            where_clause = " AND ".join(where_conditions)

            await self.connection.execute("SET hnsw.ef_search = 500;")

            if candidate_ids is not None and len(candidate_ids) > 0:
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
                    target_embedding,
                    target_id,
                    parent_traj_id,
                    candidate_ids,
                    limit,
                )
            else:
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
                    target_embedding,
                    target_id,
                    parent_traj_id,
                    limit,
                )

            ranked_results = []
            for rank, row in enumerate(results, start=1):
                ranked_results.append({
                    'seg_id':   row['seg_id'],
                    'traj_id':  row['traj_id'],
                    'distance': float(row['distance']),
                    'rank':     rank,
                    'mode':     mode,
                })

            filter_info = "(only trajs)" if only_traj else "(only segments)" if only_segments else ""
            logger.info(
                f"{mode.upper()} search for {target_id}: "
                f"Found {len(ranked_results)} results {filter_info}"
            )
            return ranked_results

        except Exception as e:
            logger.error(f"Error in {mode} embedding search for {target_id}: {e}")
            return []

    async def check_embeddings_exist(self, target_id: str) -> Dict[str, bool]:
        try:
            query = """
                SELECT joint_embedding       IS NOT NULL AS has_joint,
                       position_embedding    IS NOT NULL AS has_position,
                       orientation_embedding IS NOT NULL AS has_orientation,
                       velocity_embedding    IS NOT NULL AS has_velocity,
                       metadata_embedding    IS NOT NULL AS has_metadata
                FROM motion.traj_embeddings
                WHERE seg_id = $1
            """
            result = await self.connection.fetchrow(query, target_id)
            if not result:
                return {k: False for k in ['joint', 'position', 'orientation', 'velocity', 'metadata']}
            return {
                'joint':       result['has_joint'],
                'position':    result['has_position'],
                'orientation': result['has_orientation'],
                'velocity':    result['has_velocity'],
                'metadata':    result['has_metadata'],
            }
        except Exception as e:
            logger.error(f"Error checking embeddings for {target_id}: {e}")
            return {k: False for k in ['joint', 'position', 'orientation', 'velocity', 'metadata']}


# ── Candidate (unsaved) variant ───────────────────────────────────────────

def _array_to_vector_str(arr) -> str:
    """Same format asyncpg would return for a real vector column."""
    if isinstance(arr, np.ndarray):
        arr = arr.tolist()
    return '[' + ','.join(str(x) for x in arr) + ']'


class ShapeSearcherCandidate(ShapeSearcher):
    """
    Drop-in for ShapeSearcher when the QUERY side is an unsaved candidate.
    Only get_target_embedding and check_embeddings_exist are overridden.
    Previously lived in shape_searcher_ext.py as ShapeSearcherExternal.
    """

    def __init__(self, connection: asyncpg.Connection, embeddings: Dict[str, list], candidate_id: str):
        super().__init__(connection)
        self._embeddings    = embeddings
        self._candidate_id  = candidate_id

    async def get_target_embedding(self, target_id: str, mode: str) -> Optional[Dict]:
        embedding = self._embeddings.get(mode)
        if embedding is None:
            return None
        return {"embedding": _array_to_vector_str(embedding), "traj_id": self._candidate_id}

    async def check_embeddings_exist(self, target_id: str) -> Dict[str, bool]:
        return {
            mode: (self._embeddings.get(mode) is not None)
            for mode in ['joint', 'position', 'orientation', 'velocity', 'metadata']
        }