# backend/app/utils/multi_modal_searcher.py

import asyncpg
from typing import Dict, List, Optional
import logging
from .shape_searcher import ShapeSearcher
from .rrf_ranker import RRFRanker
from .filter_searcher import FilterSearcher

logger = logging.getLogger(__name__)


class MultiModalSearcher:
    """
    Orchestrator für HIERARCHICAL Multi-Modal Similarity Search

    Flow:
    1. Bahn-Level: Finde ähnliche Bahnen (segment_id = bahn_id)
    2. Segment-Level: Für jedes Target-Segment, finde ähnliche Segmente
    """

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection
        self.shape = ShapeSearcher(connection)
        self.prefilter = FilterSearcher(connection)
        self.ranker = RRFRanker(k=60)

    async def search_similar(
            self,
            target_id: str,
            modes: Optional[List[str]] = None,
            weights: Optional[Dict[str, float]] = None,
            prefilter_features: Optional[List[str]] = None,
            limit: int = 10
    ) -> Dict:
        """
        HIERARCHICAL Similarity Search

        Phase 1: Target BAHN vs andere Bahnen
        Phase 2: Target SEGMENTE vs andere Segmente
        """
        try:
            # Defaults
            if modes is None:
                modes = ['joint', 'position', 'orientation', 'velocity', 'metadata']

            if weights is None:
                weights = {mode: 1.0 / len(modes) for mode in modes}

            if prefilter_features is None:
                prefilter_features = []

            # Ermittle bahn_id
            target_bahn_id = await self._get_bahn_id(target_id)
            if not target_bahn_id:
                return {
                    'error': f"Target {target_id} not found",
                    'bahn_similarity': {},
                    'segment_similarity': []
                }

            # ✅ NEU: Hole Target Bahn Features
            target_bahn_features = await self._get_features(target_bahn_id)

            result = {
                'target_id': target_id,
                'target_bahn_id': target_bahn_id,
                'target_bahn_features': target_bahn_features,  # ✅ NEU!
                'modes': modes,
                'weights': weights,
                'bahn_similarity': {},
                'segment_similarity': [],
                'metadata': {}
            }
            
            #if 'velocity' in modes:
            #    prefilter_features.append('velocity_profile')

            #if 'acceleration' in modes:
            #    prefilter_features.append('acceleration_profile')

            # ===== PHASE 1: BAHN-LEVEL SEARCH =====
            logger.info(f"[Phase 1] Bahn-Level Search: {target_bahn_id} vs other Bahnen")

            bahn_results = await self._search_bahnen(
                target_bahn_id=target_bahn_id,
                modes=modes,
                weights=weights,
                limit=limit,
                prefilter_features=prefilter_features
            )

            result['bahn_similarity'] = bahn_results

            # ===== PHASE 2: SEGMENT-LEVEL SEARCH =====
            logger.info(f"[Phase 2] Segment-Level Search for Bahn {target_bahn_id}")

            # Hole alle Segmente der Target-Bahn
            target_segments = await self._get_bahn_segments(target_bahn_id)

            if not target_segments:
                logger.warning(f"No segments found for bahn {target_bahn_id}")
                result['metadata']['target_segments_count'] = 0
                return result

            result['metadata']['target_segments_count'] = len(target_segments)

            # Für jedes Target-Segment: Finde ähnliche Segmente
            segment_results = []

            for target_segment_id in target_segments:
                logger.info(f"  → Searching similar segments for {target_segment_id}")

                # ✅ NEU: Hole Target Segment Features
                target_segment_features = await self._get_features(target_segment_id)

                segment_result = await self._search_segments(
                    target_segment_id=target_segment_id,
                    modes=modes,
                    weights=weights,
                    limit=limit,
                    prefilter_features=prefilter_features
                )

                segment_results.append({
                    'target_segment': target_segment_id,
                    'target_segment_features': target_segment_features,  # ✅ NEU!
                    'similar_segments': segment_result
                })

            result['segment_similarity'] = segment_results
            result['metadata']['segments_processed'] = len(segment_results)

            logger.info(
                f"Hierarchical search complete for {target_id}: "
                f"{len(bahn_results.get('results', []))} bahnen, "
                f"{len(segment_results)} segment groups"
            )

            return result

        except Exception as e:
            logger.error(f"Error in hierarchical search for {target_id}: {e}")
            return {
                'target_id': target_id,
                'error': str(e),
                'bahn_similarity': {},
                'segment_similarity': []
            }

    async def _get_bahn_id(self, target_id: str) -> Optional[str]:
        """Ermittelt bahn_id für gegebene target_id"""
        try:
            query = """
                    SELECT bahn_id
                    FROM bewegungsdaten.bahn_metadata
                    WHERE segment_id = $1 \
                    """
            result = await self.connection.fetchrow(query, target_id)
            return result['bahn_id'] if result else None
        except Exception as e:
            logger.error(f"Error getting bahn_id for {target_id}: {e}")
            return None

    async def _get_bahn_segments(self, bahn_id: str) -> List[str]:
        """Holt alle Segment-IDs einer Bahn (segment_id != bahn_id)"""
        try:
            query = """
                    SELECT segment_id
                    FROM bewegungsdaten.bahn_metadata
                    WHERE bahn_id = $1
                      AND segment_id != bahn_id
                    ORDER BY segment_id \
                    """
            results = await self.connection.fetch(query, bahn_id)
            return [row['segment_id'] for row in results]
        except Exception as e:
            logger.error(f"Error getting segments for bahn {bahn_id}: {e}")
            return []

    async def _get_features(self, segment_id: str) -> Optional[Dict]:
        """
        ✅ NEU: Holt Features für eine beliebige segment_id (Bahn oder Segment)

        Returns:
            Dict mit allen Features oder None
        """
        try:
            query = """
                SELECT 
                    bm.segment_id,
                    bm.bahn_id,
                    bm.duration,
                    bm.weight,
                    bm.length,
                    bm.movement_type,
                    bm.mean_twist_ist,
                    bm.max_twist_ist,
                    bm.std_twist_ist,
                    bm.min_acceleration_ist,
                    bm.mean_acceleration_ist,
                    bm.max_acceleration_ist,
                    bm.std_acceleration_ist,
                    bm.position_x,
                    bm.position_y,
                    bm.position_z,
                    si.sidtw_average_distance
                FROM bewegungsdaten.bahn_metadata bm
                LEFT JOIN auswertung.info_sidtw si 
                    ON bm.segment_id = si.segment_id
                WHERE bm.segment_id = $1
            """

            result = await self.connection.fetchrow(query, segment_id)

            if result:
                return dict(result)

            logger.warning(f"No features found for {segment_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting features for {segment_id}: {e}")
            return None

    async def _search_bahnen(
            self,
            target_bahn_id: str,
            modes: List[str],
            weights: Dict[str, float],
            limit: int,
            prefilter_features: List[str]
    ) -> Dict:
        """
        Sucht ähnliche BAHNEN

        Target: target_bahn_id (wo segment_id = bahn_id)
        Compare: Nur andere Bahnen (segment_id = bahn_id)
        """
        try:
            # Check ob BAHN-Embedding existiert
            embedding_status = await self.shape.check_embeddings_exist(target_bahn_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            if not available_modes:
                return {
                    'error': f"No embeddings available for bahn {target_bahn_id}",
                    'results': []
                }
                        
            candidate_ids = None
            if prefilter_features:
                logger.info(f"[Pre-Filter Bahn] Features: {prefilter_features}")
                candidate_ids = await self.prefilter.get_filtered_candidates(
                    target_bahn_id,
                    features_to_use=prefilter_features
                )
                
                # Filter: Nur Bahnen (segment_id = bahn_id)
                bahn_candidates = await self.prefilter._filter_only_bahnen(candidate_ids)
                logger.info(f"[Pre-Filter Bahn] {len(bahn_candidates)} candidates")
                
                if not bahn_candidates:
                    return {'error': 'No candidates after pre-filter', 'results': []}
                
                candidate_ids = bahn_candidates

            # Shape Search mit Filter: NUR Bahnen!
            rankings = {}
            for mode in available_modes:
                mode_results = await self.shape.search_by_embedding(
                    target_id=target_bahn_id,
                    mode=mode,
                    limit=limit,
                    candidate_ids=candidate_ids,
                    only_bahnen=True
                )

                rankings[mode] = mode_results

            # RRF Fusion
            fused = self.ranker.fuse_rankings(rankings, weights)
            final = fused[:limit]

            # Enrich
            enriched = await self._enrich_results(final)

            return {
                'target': target_bahn_id,
                'results': enriched,
                'metadata': {
                    'modes': available_modes,
                    'weights': weights
                }
            }

        except Exception as e:
            logger.error(f"Error searching bahnen for {target_bahn_id}: {e}")
            return {'error': str(e), 'results': []}

    async def _search_segments(
            self,
            target_segment_id: str,
            modes: List[str],
            weights: Dict[str, float],
            limit: int,
            prefilter_features: List[str]
    ) -> Dict:
        """
        Sucht ähnliche SEGMENTE

        Target: target_segment_id (ein Segment)
        Compare: Nur andere Segmente (segment_id != bahn_id)
        """
        try:
            # Check ob SEGMENT-Embedding existiert
            embedding_status = await self.shape.check_embeddings_exist(target_segment_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            if not available_modes:
                return {
                    'error': f"No embeddings for segment {target_segment_id}",
                    'results': []
                }
            
            candidate_ids = None
            if prefilter_features:
                logger.info(f"[Pre-Filter Segment] Features: {prefilter_features}")
                candidate_ids = await self.prefilter.get_filtered_candidates(
                    target_segment_id,
                    features_to_use=prefilter_features
                )
                
                # Filter: Nur Segmente (segment_id != bahn_id)
                segment_candidates = await self.prefilter._filter_only_segments(candidate_ids)
                logger.info(f"[Pre-Filter Segment] {len(segment_candidates)} candidates")
                
                if not segment_candidates:
                    return {'error': 'No candidates after pre-filter', 'results': []}
                
                candidate_ids = segment_candidates
            
            # Shape Search mit Filter: NUR Segmente!
            rankings = {}
            for mode in available_modes:
                mode_results = await self.shape.search_by_embedding(
                    target_id=target_segment_id,
                    mode=mode,
                    limit=limit,
                    candidate_ids=candidate_ids,
                    only_segments=True
                )

                rankings[mode] = mode_results

            # RRF Fusion
            fused = self.ranker.fuse_rankings(rankings, weights)
            final = fused[:limit]

            # Enrich
            enriched = await self._enrich_results(final)

            return {
                'target': target_segment_id,
                'results': enriched,
                'metadata': {
                    'modes': available_modes,
                    'weights': weights
                }
            }

        except Exception as e:
            logger.error(f"Error searching segments for {target_segment_id}: {e}")
            return {'error': str(e), 'results': []}

    async def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """Reichert Ergebnisse mit Features aus bahn_metadata an"""
        if not results:
            return []

        segment_ids = [r['segment_id'] for r in results]

        try:
            query = """
                SELECT 
                    bm.segment_id,
                    bm.bahn_id,
                    bm.duration,
                    bm.weight,
                    bm.length,
                    bm.movement_type,
                    bm.mean_twist_ist,
                    bm.max_twist_ist,
                    bm.std_twist_ist,
                    bm.min_acceleration_ist,
                    bm.mean_acceleration_ist,
                    bm.max_acceleration_ist,
                    bm.std_acceleration_ist,
                    bm.position_x,
                    bm.position_y,
                    bm.position_z,
                    si.sidtw_average_distance
                FROM bewegungsdaten.bahn_metadata bm
                LEFT JOIN auswertung.info_sidtw si 
                    ON bm.segment_id = si.segment_id
                WHERE bm.segment_id = ANY ($1)
            """

            metadata_rows = await self.connection.fetch(query, segment_ids)
            metadata_lookup = {row['segment_id']: dict(row) for row in metadata_rows}

            # Merge
            enriched = []
            for result in results:
                segment_id = result['segment_id']
                if segment_id in metadata_lookup:
                    result['features'] = metadata_lookup[segment_id]
                enriched.append(result)

            return enriched

        except Exception as e:
            logger.error(f"Error enriching results: {e}")
            return results
    
    async def _apply_post_filter(
            self,
            results: List[Dict],
            target_id: str,
            features_to_use: List[str]
    ) -> List[Dict]:
        """Post-Filter"""
        if not results or not features_to_use:
            return results
        
        try:
            logger.info(f"[Post-Filter] Starting with {len(results)} results")  # ✅
            logger.info(f"[Post-Filter] Features: {features_to_use}")  # ✅
            
            # Hole valide IDs
            valid_ids = await self.prefilter.get_filtered_candidates(
                target_id,
                features_to_use=features_to_use
            )
            
            logger.info(f"[Post-Filter] Valid candidates: {len(valid_ids)}")  # ✅
            
            valid_ids_set = set(valid_ids)
            
            # Filter
            filtered = [r for r in results if r['segment_id'] in valid_ids_set]
            
            logger.info(f"[Post-Filter] After filter: {len(filtered)} results")  # ✅
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error in post-filter: {e}")
            return results