# shape_searcher_external.py
from typing import Dict, Optional
import numpy as np
import asyncpg
from .shape_searcher import ShapeSearcher


def _array_to_vector_str(arr) -> str:
    """Same format asyncpg would return for a real vector column."""
    if isinstance(arr, np.ndarray):
        arr = arr.tolist()
    return '[' + ','.join(str(x) for x in arr) + ']'


class ShapeSearcherExternal(ShapeSearcher):
    def __init__(self, connection: asyncpg.Connection, embeddings: Dict[str, list], external_id: str):
        super().__init__(connection)
        self._embeddings  = embeddings
        self._external_id = external_id

    async def get_target_embedding(self, target_id: str, mode: str) -> Optional[Dict]:
        embedding = self._embeddings.get(mode)
        if embedding is None:
            return None
        return {"embedding": _array_to_vector_str(embedding), "traj_id": self._external_id}

    async def check_embeddings_exist(self, target_id: str) -> Dict[str, bool]:
        return {
            mode: (self._embeddings.get(mode) is not None)
            for mode in ['joint', 'position', 'orientation', 'velocity', 'metadata']
        }