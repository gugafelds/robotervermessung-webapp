import sys
import asyncpg
from typing import Dict, List, Optional
import logging
import ast

logger = logging.getLogger(__name__)

sys.path.append(
    r"\robotervermessung-webapp\backend\app"
)
from utils.multimodal_framework.shape_searcher import ShapeSearcher
from utils.metadata_embeddings.embedding_calculator import EmbeddingCalculator


class ShapeSearcherGen(ShapeSearcher):
    def __init__(self, connection: asyncpg.Connection):
        super().__init__(connection)

    async def get_target_embedding(self, target: str, mode: str) -> Optional[Dict]:
        """
        Berechnet target embedding aus gegebener Liste (als string) von Punkten
        """
        embedding_calculator = EmbeddingCalculator()

        try:
            data = ast.literal_eval(target)

            if isinstance(target, (list, tuple)):
                data = target
            else:
                data = ast.literal_eval(target)
            
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (list, tuple)):
                data = [{'x_cmd': p[0], 'y_cmd': p[1], 'z_cmd': p[2]} for p in data]
            
            if len(data) < 10:
                import numpy as np
                positions = np.array([[d['x_cmd'], d['y_cmd'], d['z_cmd']] for d in data])
                # Lineare Interpolation auf 10 Punkte
                from scipy.interpolate import interp1d
                x_interp = interp1d(np.linspace(0, 1, len(positions)), positions[:, 0], kind='linear')
                y_interp = interp1d(np.linspace(0, 1, len(positions)), positions[:, 1], kind='linear')
                z_interp = interp1d(np.linspace(0, 1, len(positions)), positions[:, 2], kind='linear')
                
                t_new = np.linspace(0, 1, 400)
                x_new = x_interp(t_new)
                y_new = y_interp(t_new)
                z_new = z_interp(t_new)
                
                data = [{'x_cmd': x, 'y_cmd': y, 'z_cmd': z} for x, y, z in zip(x_new, y_new, z_new)]
            
            embedding = embedding_calculator.compute_position_embedding(data)

            if embedding is None:
                logger.error(f"Failed to compute embedding for {target}")
                return None

            return {
                "embedding": embedding.tolist(),   # Convert numpy array to list
                "traj_id": target
            }

        except Exception as e:
            logger.error(f"Error getting position embedding: {e}")
            return None

    async def search_by_embedding(
        self,
        target_id: str,
        mode: str,
        limit: int = 100,
        candidate_ids: Optional[List[str]] = None,
        only_traj: bool = False,
        only_segments: bool = False,
    ) -> List[Dict]:
        """
        Sucht ähnliche Bahnen/Segmente aus der DB basierend auf Embedding
        Für Koordinaten-Input: Sucht nur in DB, nicht selbst auszuschließen
        """
        mode = "position"
        try:
            target_data = await self.get_target_embedding(target_id, mode)

            if target_data is None:
                logger.error(f"Cannot get {mode} embedding for {target_id}")
                return []

            target_embedding = target_data["embedding"]
            embedding_col = f"{mode}_embedding"

            await self.connection.execute("SET hnsw.ef_search = 500;")

  
            where_conditions = [f"e.{embedding_col} IS NOT NULL"]

            if only_traj:
                where_conditions.append("e.seg_id = e.traj_id")
            elif only_segments:
                where_conditions.append("e.seg_id != e.traj_id")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT 
                    e.seg_id,
                    e.traj_id,
                    e.{embedding_col} <=> $1::vector as distance
                FROM motion.traj_embeddings e
                WHERE {where_clause}
                ORDER BY distance, e.seg_id
                LIMIT $2
            """

            results = await self.connection.fetch(
                query,
                str(target_embedding),  # $1
                limit              # $2
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
        return {
            "joint": False,
            "position": True,
            "orientation": False,
            "velocity": False,
            "metadata": False,
        }
        """try:
            return await super().check_embeddings_exist(target_id)
        except Exception as e:
            logger.error(f"Error checking for embedding: {e}")
            return None"""
