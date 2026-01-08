# backend/app/utils/binary_vector_writer.py

import psycopg
import numpy as np
from pgvector.psycopg import register_vector
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class BinaryVectorWriter:
    """
    Spezialisierter Writer für Binary COPY von Embeddings
    Nutzt psycopg3 statt asyncpg für schnelleres Vector-Loading
    """
    
    def __init__(self, db_url: str):
        """
        Args:
            db_url: PostgreSQL connection string
                    Format: postgresql://user:pass@host:port/dbname
        """
        self.db_url = db_url
    
    def bulk_write_embeddings(
        self, 
        embedding_rows: List[Dict]
    ) -> int:
        """
        Schreibt Embeddings mit Binary COPY (SCHNELL!)
        
        Args:
            embedding_rows: List[Dict] mit:
                - segment_id: str
                - bahn_id: str
                - joint_embedding: np.ndarray oder None
                - position_embedding: np.ndarray oder None
                - orientation_embedding: np.ndarray oder None
                - velocity_embedding: np.ndarray oder None
                - metadata_embedding: np.ndarray oder None
        
        Returns:
            Anzahl geschriebener Rows
        """
        if not embedding_rows:
            logger.info("No embeddings to write")
            return 0
        
        try:
            # Connection mit autocommit
            conn = psycopg.connect(self.db_url, autocommit=True)
            conn.execute("SET search_path TO bewegungsdaten;")
            
            # Register vector type
            register_vector(conn)
            
            logger.info(f"Writing {len(embedding_rows)} embedding rows with Binary COPY")
            
            # Binary COPY
            cur = conn.cursor()
            
            with cur.copy(
                "COPY bewegungsdaten.bahn_embeddings "
                "(segment_id, bahn_id, joint_embedding, position_embedding, "
                "orientation_embedding, velocity_embedding, metadata_embedding) "
                "FROM STDIN WITH (FORMAT BINARY)"
            ) as copy:
                
                # Set types für Binary Copy
                copy.set_types(['text', 'text', 'vector', 'vector', 'vector', 'vector', 'vector'])
                
                for i, row in enumerate(embedding_rows):
                    # Konvertiere zu numpy arrays (falls noch Strings)
                    joint_emb = self._to_numpy(row.get('joint_embedding'))
                    pos_emb = self._to_numpy(row.get('position_embedding'))
                    ori_emb = self._to_numpy(row.get('orientation_embedding'))
                    vel_emb = self._to_numpy(row.get('velocity_embedding'))
                    meta_emb = self._to_numpy(row.get('metadata_embedding'))
                    
                    copy.write_row([
                        row['segment_id'],
                        row['bahn_id'],
                        joint_emb,
                        pos_emb,
                        ori_emb,
                        vel_emb,
                        meta_emb
                    ])
                    
                    # Progress
                    if i > 0 and i % 100 == 0:
                        logger.debug(f"Progress: {i}/{len(embedding_rows)}")
            
            conn.close()
            
            logger.info(f"✓ Successfully wrote {len(embedding_rows)} embeddings via Binary COPY")
            return len(embedding_rows)
            
        except Exception as e:
            logger.error(f"Error in binary vector write: {e}")
            raise
    
    @staticmethod
    def _to_numpy(embedding) -> np.ndarray:
        """
        Konvertiert Embedding zu numpy array
        
        Args:
            embedding: np.ndarray, str '[1.2,3.4,...]', oder None
        
        Returns:
            np.ndarray or None
        """
        if embedding is None:
            return None
        
        if isinstance(embedding, np.ndarray):
            return embedding
        
        if isinstance(embedding, str):
            # Parse '[1.2,3.4,...]' zu numpy array
            embedding = embedding.strip('[]')
            values = [float(x) for x in embedding.split(',')]
            return np.array(values, dtype=np.float32)
        
        # Fallback: Try to convert
        return np.array(embedding, dtype=np.float32)