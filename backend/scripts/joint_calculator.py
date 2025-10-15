# backend/scripts/joint_calculator.py

import asyncpg
import numpy as np
from typing import Optional, List, Dict, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class FastJointEmbeddingCalculator:
    """
    SCHNELLE Joint Embedding Berechnung
    Unterstützt sowohl Segment-Level als auch Bahn-Level
    """

    def __init__(
            self,
            db_pool: asyncpg.Pool,
            samples_per_joint: int = 25,
            downsample_factor: int = 15
    ):
        self.db_pool = db_pool
        self.samples_per_joint = samples_per_joint
        self.downsample_factor = downsample_factor
        self.total_dimensions = 6 * samples_per_joint

    def _create_embedding_from_trajectory(self, joint_states_data: List) -> Optional[np.ndarray]:
        """
        Erstellt Embedding aus Joint States Daten

        Args:
            joint_states_data: Liste von Dicts mit joint_1 bis joint_6

        Returns:
            np.ndarray (150,) oder None
        """
        if len(joint_states_data) < 10:
            return None

        # Zu NumPy
        traj = np.array([
            [row['joint_1'], row['joint_2'], row['joint_3'],
             row['joint_4'], row['joint_5'], row['joint_6']]
            for row in joint_states_data
        ], dtype=np.float32)

        # Downsample
        traj = traj[::self.downsample_factor]

        if len(traj) < 5:
            return None

        # Normalisierung: Startpunkt auf 0
        traj_norm = traj - traj[0]

        # Resample auf feste Anzahl
        indices = np.linspace(
            0,
            len(traj_norm) - 1,
            self.samples_per_joint,
            dtype=int
        )
        resampled = traj_norm[indices]

        # Flatten + L2-Normalize
        vec = resampled.flatten()
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.astype(np.float32)

    async def calculate_segment_embedding(self, segment_id: str) -> Optional[np.ndarray]:
        """
        Berechnet Embedding für EIN Segment

        Args:
            segment_id: ID des Segments

        Returns:
            np.ndarray (150,) oder None
        """
        async with self.db_pool.acquire() as conn:
            # Lade Joint States für Segment
            joint_states = await conn.fetch("""
                                            SELECT joint_1,
                                                   joint_2,
                                                   joint_3,
                                                   joint_4,
                                                   joint_5,
                                                   joint_6
                                            FROM bewegungsdaten.bahn_joint_states
                                            WHERE segment_id = $1
                                            """, segment_id)

            if not joint_states:
                return None

            return self._create_embedding_from_trajectory(joint_states)

    async def calculate_bahn_embedding(self, bahn_id: str) -> Optional[np.ndarray]:
        """
        Berechnet Embedding für GANZE Bahn
        Lädt ALLE Joint States der Bahn und sampelt auf 25 Punkte runter

        Args:
            bahn_id: ID der Bahn

        Returns:
            np.ndarray (150,) oder None
        """
        async with self.db_pool.acquire() as conn:
            # Lade ALLE Joint States der gesamten Bahn!
            joint_states = await conn.fetch("""
                                            SELECT joint_1,
                                                   joint_2,
                                                   joint_3,
                                                   joint_4,
                                                   joint_5,
                                                   joint_6
                                            FROM bewegungsdaten.bahn_joint_states
                                            WHERE bahn_id = $1
                                            ORDER BY segment_id, timestamp
                                            """, bahn_id)

            if not joint_states:
                return None

            logger.debug(
                f"Bahn {bahn_id}: {len(joint_states)} Joint States "
                f"→ resample auf {self.samples_per_joint} Punkte"
            )

            return self._create_embedding_from_trajectory(joint_states)

    async def calculate_embedding_batch(
            self,
            segment_ids: List[str]
    ) -> Dict[str, np.ndarray]:
        """
        BATCH-Berechnung für mehrere Segmente

        Args:
            segment_ids: Liste von Segment IDs

        Returns:
            Dictionary {segment_id: embedding}
        """
        async with self.db_pool.acquire() as conn:
            # Eine Query für ALLE Segmente!
            all_states = await conn.fetch("""
                                          SELECT segment_id,
                                                 joint_1,
                                                 joint_2,
                                                 joint_3,
                                                 joint_4,
                                                 joint_5,
                                                 joint_6
                                          FROM bewegungsdaten.bahn_joint_states
                                          WHERE segment_id = ANY ($1)
                                          """, segment_ids)

            # Gruppiere nach segment_id
            segments_data = defaultdict(list)
            for row in all_states:
                segments_data[row['segment_id']].append(dict(row))

            # Berechne Embeddings
            embeddings = {}
            for segment_id in segment_ids:
                if segment_id not in segments_data:
                    continue

                embedding = self._create_embedding_from_trajectory(
                    segments_data[segment_id]
                )

                if embedding is not None:
                    embeddings[segment_id] = embedding

            return embeddings

    async def calculate_bahn_embeddings_batch(
            self,
            bahn_ids: List[str]
    ) -> Dict[str, np.ndarray]:
        """
        BATCH-Berechnung für mehrere Bahnen

        Args:
            bahn_ids: Liste von Bahn IDs

        Returns:
            Dictionary {bahn_id: embedding}
        """
        async with self.db_pool.acquire() as conn:
            # Lade alle Joint States für alle Bahnen
            all_states = await conn.fetch("""
                                          SELECT bahn_id,
                                                 segment_id,
                                                 joint_1,
                                                 joint_2,
                                                 joint_3,
                                                 joint_4,
                                                 joint_5,
                                                 joint_6
                                          FROM bewegungsdaten.bahn_joint_states
                                          WHERE bahn_id = ANY ($1)
                                          ORDER BY bahn_id, segment_id, timestamp
                                          """, bahn_ids)

            # Gruppiere nach bahn_id
            bahnen_data = defaultdict(list)
            for row in all_states:
                bahnen_data[row['bahn_id']].append(dict(row))

            # Berechne Embeddings
            embeddings = {}
            for bahn_id in bahn_ids:
                if bahn_id not in bahnen_data:
                    continue

                embedding = self._create_embedding_from_trajectory(
                    bahnen_data[bahn_id]
                )

                if embedding is not None:
                    embeddings[bahn_id] = embedding

            return embeddings

    async def store_embeddings_batch(
            self,
            embeddings: Dict[str, np.ndarray],
            segment_to_bahn: Dict[str, str]
    ) -> int:
        """
        BATCH-Insert für Embeddings

        Args:
            embeddings: Dictionary {segment_id: embedding}
            segment_to_bahn: Dictionary {segment_id: bahn_id}

        Returns:
            Anzahl gespeicherter Embeddings
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            count = 0
            for segment_id, embedding in embeddings.items():
                try:
                    # Konvertiere zu String
                    embedding_list = embedding.tolist()
                    embedding_str = '[' + ','.join(str(x) for x in embedding_list) + ']'

                    await conn.execute("""
                                       INSERT INTO bahn_joint_embeddings
                                           (segment_id, bahn_id, joint_embedding, sample_count)
                                       VALUES ($1, $2, $3, $4) ON CONFLICT (segment_id) 
                        DO
                                       UPDATE SET
                                           joint_embedding = EXCLUDED.joint_embedding,
                                           updated_at = NOW()
                                       """,
                                       segment_id,
                                       segment_to_bahn.get(segment_id),
                                       embedding_str,
                                       self.samples_per_joint
                                       )
                    count += 1
                except Exception as e:
                    logger.error(f"Fehler bei {segment_id}: {e}")

            return count

    async def store_bahn_embeddings_batch(
            self,
            embeddings: Dict[str, np.ndarray]
    ) -> int:
        """
        BATCH-Insert für Bahn-Embeddings
        Speichert mit bahn_id = segment_id!

        Args:
            embeddings: Dictionary {bahn_id: embedding}

        Returns:
            Anzahl gespeicherter Embeddings
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            count = 0
            for bahn_id, embedding in embeddings.items():
                try:
                    # Konvertiere zu String
                    embedding_list = embedding.tolist()
                    embedding_str = '[' + ','.join(str(x) for x in embedding_list) + ']'

                    # bahn_id = segment_id für Bahn-Level!
                    await conn.execute("""
                                       INSERT INTO bahn_joint_embeddings
                                           (segment_id, bahn_id, joint_embedding, sample_count)
                                       VALUES ($1, $2, $3, $4) ON CONFLICT (segment_id) 
                        DO
                                       UPDATE SET
                                           joint_embedding = EXCLUDED.joint_embedding,
                                           updated_at = NOW()
                                       """,
                                       bahn_id,  # segment_id = bahn_id!
                                       bahn_id,  # bahn_id
                                       embedding_str,
                                       self.samples_per_joint
                                       )
                    count += 1
                except Exception as e:
                    logger.error(f"Fehler bei Bahn {bahn_id}: {e}")

            return count

    async def find_similar(
        self,
        target_segment_id: str,
        limit: int = 10,
        bahn_id_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """Ähnlichkeitssuche"""
        async with self.db_pool.acquire() as conn:
            target = await conn.fetchrow("""
                SELECT joint_embedding, bahn_id
                FROM bewegungsdaten.bahn_joint_embeddings
                WHERE segment_id = $1
            """, target_segment_id)

            if not target:
                return []

            target_embedding = target['joint_embedding']

            if bahn_id_filter:
                results = await conn.fetch("""
                    SELECT 
                        segment_id,
                        bahn_id,
                        joint_embedding <-> $1 AS distance
                    FROM bewegungsdaten.bahn_joint_embeddings
                    WHERE segment_id != $2
                      AND bahn_id = ANY($3)
                    ORDER BY distance
                    LIMIT $4
                """, target_embedding, target_segment_id, bahn_id_filter, limit)
            else:
                results = await conn.fetch("""
                    SELECT 
                        segment_id,
                        bahn_id,
                        joint_embedding <-> $1 AS distance
                    FROM bewegungsdaten.bahn_joint_embeddings
                    WHERE segment_id != $2
                    ORDER BY distance
                    LIMIT $3
                """, target_embedding, target_segment_id, limit)

            return [
                {
                    'segment_id': row['segment_id'],
                    'bahn_id': row['bahn_id'],
                    'distance': float(row['distance'])
                }
                for row in results
            ]

    async def find_similar_bahn(
            self,
            target_bahn_id: str,
            limit: int = 10
    ) -> Dict[str, Any]:
        """
        Bahn-Level Similarity: Vergleicht ALLE Segmente einer Bahn
        Aggregiert die Embeddings zu einem Bahn-Vektor

        Args:
            target_bahn_id: ID der Ziel-Bahn
            limit: Anzahl ähnlicher Bahnen

        Returns:
            Dictionary mit ähnlichen Bahnen
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            # 1. Lade alle Embeddings der Target-Bahn
            target_embeddings = await conn.fetch("""
                                                 SELECT joint_embedding
                                                 FROM bahn_joint_embeddings
                                                 WHERE bahn_id = $1
                                                 """, target_bahn_id)

            if not target_embeddings:
                return {
                    "error": f"Bahn {target_bahn_id} hat keine Embeddings!",
                    "target_bahn_id": target_bahn_id
                }

            # 2. Konvertiere Strings zu NumPy Arrays
            target_vectors = []
            for row in target_embeddings:
                vec_str = row['joint_embedding']
                if isinstance(vec_str, str):
                    vec_list = [float(x) for x in vec_str.strip('[]').split(',')]
                    target_vectors.append(vec_list)
                else:
                    target_vectors.append(vec_str)

            # 3. Aggregiere zu Bahn-Vektor (Mittelwert)
            target_bahn_vector = np.mean(target_vectors, axis=0)

            logger.info(
                f"Bahn {target_bahn_id}: "
                f"{len(target_embeddings)} Segmente aggregiert"
            )

            # 4. Lade ALLE anderen Bahnen mit Embeddings
            all_bahnen = await conn.fetch("""
                                          SELECT bahn_id,
                                                 joint_embedding
                                          FROM bahn_joint_embeddings
                                          WHERE bahn_id != $1
                                          """, target_bahn_id)

            # 5. Gruppiere nach bahn_id und berechne Distanzen in Python
            from collections import defaultdict

            bahn_embeddings = defaultdict(list)
            for row in all_bahnen:
                vec_str = row['joint_embedding']
                if isinstance(vec_str, str):
                    vec_list = [float(x) for x in vec_str.strip('[]').split(',')]
                else:
                    vec_list = vec_str
                bahn_embeddings[row['bahn_id']].append(vec_list)

            # 6. Berechne Distanzen für jede Bahn
            bahn_distances = []
            for bahn_id, vectors in bahn_embeddings.items():
                avg_vec = np.mean(vectors, axis=0)
                distance = np.linalg.norm(target_bahn_vector - avg_vec)  # L2 distance
                bahn_distances.append({
                    'bahn_id': bahn_id,
                    'segment_count': len(vectors),
                    'distance': float(distance)
                })

            # 7. Sortiere und limitiere
            bahn_distances.sort(key=lambda x: x['distance'])
            results = bahn_distances[:limit]

            # 8. Lade zusätzliche Info für Top-Ergebnisse
            similar_bahnen = []
            for row in results:
                bahn_id = row['bahn_id']

                # Lade Bahn-Info
                bahn_info = await conn.fetchrow("""
                                                SELECT bi.robot_model,
                                                       bi.recording_date,
                                                       bm.meta_value
                                                FROM bahn_info bi
                                                         LEFT JOIN bahn_meta bm
                                                                   ON bi.bahn_id = bm.bahn_id
                                                                       AND bi.bahn_id = bm.segment_id
                                                WHERE bi.bahn_id = $1
                                                """, bahn_id)

                similar_bahnen.append({
                    'bahn_id': bahn_id,
                    'segment_count': row['segment_count'],
                    'distance': row['distance'],
                    'robot_model': bahn_info['robot_model'] if bahn_info else None,
                    'recording_date': bahn_info['recording_date'] if bahn_info else None,
                    'meta_value': float(bahn_info['meta_value']) if bahn_info and bahn_info['meta_value'] else None
                })

            # 9. Target Info
            target_info = await conn.fetchrow("""
                                              SELECT bi.robot_model,
                                                     bi.recording_date,
                                                     bm.meta_value,
                                                     COUNT(DISTINCT bje.segment_id) as segment_count
                                              FROM bahn_info bi
                                                       LEFT JOIN bahn_meta bm
                                                                 ON bi.bahn_id = bm.bahn_id
                                                                     AND bi.bahn_id = bm.segment_id
                                                       LEFT JOIN bahn_joint_embeddings bje
                                                                 ON bi.bahn_id = bje.bahn_id
                                              WHERE bi.bahn_id = $1
                                              GROUP BY bi.robot_model, bi.recording_date, bm.meta_value
                                              """, target_bahn_id)

            return {
                "target_bahn_id": target_bahn_id,
                "target_info": {
                    'segment_count': target_info['segment_count'] if target_info else 0,
                    'robot_model': target_info['robot_model'] if target_info else None,
                    'recording_date': target_info['recording_date'] if target_info else None,
                    'meta_value': float(target_info['meta_value']) if target_info and target_info[
                        'meta_value'] else None
                },
                "similar_bahnen": similar_bahnen,
                "total_found": len(similar_bahnen)
            }

    async def find_similar_segments_for_bahn(
            self,
            target_bahn_id: str,
            segment_limit: int = 5
    ) -> Dict[str, Any]:
        """
        Segment-Level Similarity: Für JEDES Segment der Bahn

        Args:
            target_bahn_id: ID der Ziel-Bahn
            segment_limit: Anzahl ähnlicher Segmente pro Target-Segment

        Returns:
            Dictionary mit Ergebnissen pro Segment
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute("SET search_path TO bewegungsdaten, public")

            # 1. Lade alle Segmente der Target-Bahn
            target_segments = await conn.fetch("""
                                               SELECT segment_id, joint_embedding
                                               FROM bahn_joint_embeddings
                                               WHERE bahn_id = $1
                                               ORDER BY segment_id
                                               """, target_bahn_id)

            if not target_segments:
                return {
                    "error": f"Bahn {target_bahn_id} hat keine Embeddings!",
                    "segment_results": []
                }

            logger.info(
                f"Bahn {target_bahn_id}: "
                f"Suche ähnliche Segmente für {len(target_segments)} Segmente"
            )

            # 2. Lade ALLE anderen Segmente (von anderen Bahnen)
            all_other_segments = await conn.fetch("""
                                                  SELECT segment_id,
                                                         bahn_id,
                                                         joint_embedding
                                                  FROM bahn_joint_embeddings
                                                  WHERE bahn_id != $1
                                                  """, target_bahn_id)

            # 3. Konvertiere alle Embeddings zu NumPy Arrays (einmalig!)
            other_segments_data = []
            for row in all_other_segments:
                vec_str = row['joint_embedding']
                if isinstance(vec_str, str):
                    vec_array = np.array([float(x) for x in vec_str.strip('[]').split(',')], dtype=np.float32)
                else:
                    vec_array = np.array(vec_str, dtype=np.float32)

                other_segments_data.append({
                    'segment_id': row['segment_id'],
                    'bahn_id': row['bahn_id'],
                    'embedding': vec_array
                })

            logger.info(f"Vergleiche mit {len(other_segments_data)} anderen Segmenten")

            # 4. Für jedes Target-Segment: Finde ähnliche
            segment_results = []

            for target_seg in target_segments:
                segment_id = target_seg['segment_id']
                vec_str = target_seg['joint_embedding']

                # Konvertiere Target-Embedding
                if isinstance(vec_str, str):
                    target_embedding = np.array([float(x) for x in vec_str.strip('[]').split(',')], dtype=np.float32)
                else:
                    target_embedding = np.array(vec_str, dtype=np.float32)

                # Berechne Distanzen zu allen anderen Segmenten (in Python!)
                distances = []
                for other in other_segments_data:
                    distance = np.linalg.norm(target_embedding - other['embedding'])  # L2 distance
                    distances.append({
                        'segment_id': other['segment_id'],
                        'bahn_id': other['bahn_id'],
                        'distance': float(distance)
                    })

                # Sortiere und nimm Top K
                distances.sort(key=lambda x: x['distance'])
                top_similar = distances[:segment_limit]

                # Lade Segment-Info für Target
                target_info = await conn.fetchrow("""
                                                  SELECT bm.length,
                                                         bm.duration,
                                                         bm.meta_value
                                                  FROM bahn_meta bm
                                                  WHERE bm.segment_id = $1
                                                  """, segment_id)

                # Lade Info für ähnliche Segmente
                similar_segments = []
                for sim in top_similar:
                    sim_info = await conn.fetchrow("""
                                                   SELECT bm.length,
                                                          bm.duration,
                                                          bm.meta_value,
                                                          bi.robot_model
                                                   FROM bahn_meta bm
                                                            JOIN bahn_info bi ON bm.bahn_id = bi.bahn_id
                                                   WHERE bm.segment_id = $1
                                                   """, sim['segment_id'])

                    similar_segments.append({
                        'segment_id': sim['segment_id'],
                        'bahn_id': sim['bahn_id'],
                        'distance': sim['distance'],
                        'length': float(sim_info['length']) if sim_info and sim_info['length'] else None,
                        'duration': float(sim_info['duration']) if sim_info and sim_info['duration'] else None,
                        'meta_value': float(sim_info['meta_value']) if sim_info and sim_info['meta_value'] else None,
                        'robot_model': sim_info['robot_model'] if sim_info else None
                    })

                segment_results.append({
                    "target_segment_id": segment_id,
                    "target_info": {
                        'length': float(target_info['length']) if target_info and target_info['length'] else None,
                        'duration': float(target_info['duration']) if target_info and target_info['duration'] else None,
                        'meta_value': float(target_info['meta_value']) if target_info and target_info[
                            'meta_value'] else None
                    },
                    "similar_segments": similar_segments,
                    "total_found": len(similar_segments)
                })

            return {
                "target_bahn_id": target_bahn_id,
                "segment_results": segment_results,
                "total_segments": len(segment_results)
            }

    async def find_similar_hierarchical(
            self,
            target_bahn_id: str,
            bahn_limit: int = 10,
            segment_limit: int = 5
    ) -> Dict[str, Any]:
        """
        HIERARCHICAL Search: Bahn-Level + Segment-Level
        Wie Ihr SimilaritySearcher.find_similar_bs()

        Args:
            target_bahn_id: ID der Ziel-Bahn
            bahn_limit: Anzahl ähnlicher Bahnen
            segment_limit: Anzahl ähnlicher Segmente pro Target-Segment

        Returns:
            Vollständiges hierarchisches Ergebnis
        """
        logger.info("=" * 70)
        logger.info("HIERARCHICAL JOINT SIMILARITY SEARCH")
        logger.info("=" * 70)
        logger.info(f"Target Bahn: {target_bahn_id}")
        logger.info(f"Bahn Limit: {bahn_limit}")
        logger.info(f"Segment Limit: {segment_limit}")
        logger.info("=" * 70)

        # Phase 1: Bahn-Level Similarity
        logger.info("\n[Phase 1/2] Bahn-Level Similarity...")
        bahn_results = await self.find_similar_bahn(target_bahn_id, bahn_limit)

        if "error" in bahn_results:
            return bahn_results

        logger.info(f"✓ Gefunden: {bahn_results['total_found']} ähnliche Bahnen")

        # Phase 2: Segment-Level Similarity
        logger.info("\n[Phase 2/2] Segment-Level Similarity...")
        segment_results = await self.find_similar_segments_for_bahn(
            target_bahn_id,
            segment_limit
        )

        if "error" in segment_results:
            logger.warning(f"Segment-Suche fehlgeschlagen: {segment_results['error']}")
            segment_results = {"segment_results": [], "total_segments": 0}
        else:
            logger.info(
                f"✓ Bearbeitet: {segment_results['total_segments']} Segmente"
            )

        logger.info("=" * 70)
        logger.info("FERTIG!")
        logger.info("=" * 70)

        return {
            "target_bahn_id": target_bahn_id,
            "bahn_similarity": bahn_results,
            "segment_similarity": segment_results,
            "summary": {
                "total_similar_bahnen": bahn_results.get('total_found', 0),
                "total_target_segments": segment_results.get('total_segments', 0),
                "method": "joint_embedding_pgvector",
                "dimensions": self.total_dimensions
            }
        }