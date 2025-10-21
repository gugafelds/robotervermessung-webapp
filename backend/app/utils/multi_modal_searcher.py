# backend/app/utils/multi_modal_searcher.py

import asyncpg
from typing import Dict, List, Optional
import logging
from .prefilter_searcher import PreFilterSearcher
from .shape_searcher import ShapeSearcher
from .rrf_ranker import RRFRanker

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
        self.prefilter = PreFilterSearcher(connection)
        self.shape = ShapeSearcher(connection)
        self.ranker = RRFRanker(k=60)

    async def search_similar(
            self,
            target_id: str,
            modes: Optional[List[str]] = None,
            weights: Optional[Dict[str, float]] = None,
            use_prefilter: bool = True,
            prefilter_tolerance: float = 0.25,
            bahn_limit: int = 10,
            segment_limit: int = 5
    ) -> Dict:
        """
        HIERARCHICAL Similarity Search

        Phase 1: Target BAHN vs andere Bahnen
        Phase 2: Target SEGMENTE vs andere Segmente
        """
        try:
            # Defaults
            if modes is None:
                modes = ['joint', 'position', 'orientation']

            if weights is None:
                weights = {mode: 1.0 / len(modes) for mode in modes}

            # Ermittle bahn_id
            target_bahn_id = await self._get_bahn_id(target_id)
            if not target_bahn_id:
                return {
                    'error': f"Target {target_id} not found",
                    'bahn_similarity': {},
                    'segment_similarity': []
                }

            result = {
                'target_id': target_id,
                'target_bahn_id': target_bahn_id,
                'modes': modes,
                'weights': weights,
                'bahn_similarity': {},
                'segment_similarity': [],
                'metadata': {}
            }

            # ===== PHASE 1: BAHN-LEVEL SEARCH =====
            # Target: Die BAHN selbst (target_bahn_id mit segment_id = bahn_id)
            logger.info(f"[Phase 1] Bahn-Level Search: {target_bahn_id} vs other Bahnen")

            bahn_results = await self._search_bahnen(
                target_bahn_id=target_bahn_id,  # ✅ BAHN als Target!
                modes=modes,
                weights=weights,
                use_prefilter=use_prefilter,
                prefilter_tolerance=prefilter_tolerance,
                limit=bahn_limit
            )

            result['bahn_similarity'] = bahn_results

            # ===== PHASE 2: SEGMENT-LEVEL SEARCH =====
            # Für jedes SEGMENT der Target-Bahn
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

                segment_result = await self._search_segments(
                    target_segment_id=target_segment_id,  # ✅ SEGMENT als Target!
                    modes=modes,
                    weights=weights,
                    use_prefilter=use_prefilter,
                    prefilter_tolerance=prefilter_tolerance,
                    limit=segment_limit
                )

                segment_results.append({
                    'target_segment': target_segment_id,
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

    async def _search_bahnen(
            self,
            target_bahn_id: str,  # ✅ Die BAHN ID (wo segment_id = bahn_id!)
            modes: List[str],
            weights: Dict[str, float],
            use_prefilter: bool,
            prefilter_tolerance: float,
            limit: int
    ) -> Dict:
        """
        Sucht ähnliche BAHNEN

        Target: target_bahn_id (wo segment_id = bahn_id)
        Compare: Nur andere Bahnen (segment_id = bahn_id)
        """
        try:
            # ✅ Check ob BAHN-Embedding existiert (segment_id = bahn_id)
            embedding_status = await self.shape.check_embeddings_exist(target_bahn_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            if not available_modes:
                return {
                    'error': f"No embeddings available for bahn {target_bahn_id}",
                    'results': []
                }

            # Pre-Filter: Hole Kandidaten basierend auf Bahn-Features
            candidate_ids = None
            if use_prefilter:
                all_candidates = await self.prefilter.get_filtered_candidates(
                    target_id=target_bahn_id,  # ✅ Nutze BAHN features für Filter
                    tolerance=prefilter_tolerance,
                    exclude_target=True
                )

                # ✅ Filter: Nur Bahnen (segment_id = bahn_id)
                if all_candidates:
                    candidate_ids = await self._filter_bahnen_only(all_candidates)
                    logger.info(f"Pre-filter Bahnen: {len(all_candidates)} → {len(candidate_ids)} bahnen")

            # Shape Search: Target BAHN vs Kandidaten Bahnen
            rankings = {}
            for mode in available_modes:
                mode_results = await self.shape.search_by_embedding(
                    target_id=target_bahn_id,  # ✅ BAHN als Target!
                    mode=mode,
                    limit=limit * 10,
                    candidate_ids=candidate_ids
                )

                # ✅ WICHTIG: Immer nur Bahnen behalten!
                mode_results = await self._filter_results_bahnen_only(mode_results)

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
                    'weights': weights,
                    'prefilter_enabled': use_prefilter,
                    'candidates_filtered': len(candidate_ids) if candidate_ids else 0
                }
            }

        except Exception as e:
            logger.error(f"Error searching bahnen for {target_bahn_id}: {e}")
            return {'error': str(e), 'results': []}

    async def _search_segments(
            self,
            target_segment_id: str,  # ✅ Ein SEGMENT (segment_id != bahn_id)
            modes: List[str],
            weights: Dict[str, float],
            use_prefilter: bool,
            prefilter_tolerance: float,
            limit: int
    ) -> Dict:
        """
        Sucht ähnliche SEGMENTE

        Target: target_segment_id (ein Segment)
        Compare: Nur andere Segmente (segment_id != bahn_id)
        """
        try:
            # ✅ Check ob SEGMENT-Embedding existiert
            embedding_status = await self.shape.check_embeddings_exist(target_segment_id)
            available_modes = [m for m in modes if embedding_status.get(m, False)]

            if not available_modes:
                return {
                    'error': f"No embeddings for segment {target_segment_id}",
                    'results': []
                }

            # Pre-Filter: Hole Kandidaten basierend auf Segment-Features
            candidate_ids = None
            if use_prefilter:
                all_candidates = await self.prefilter.get_filtered_candidates(
                    target_id=target_segment_id,  # ✅ Nutze SEGMENT features
                    tolerance=prefilter_tolerance,
                    exclude_target=True
                )

                # ✅ Filter: Nur Segmente (segment_id != bahn_id)
                if all_candidates:
                    candidate_ids = await self._filter_segments_only(all_candidates)
                    logger.info(f"Pre-filter Segments: {len(all_candidates)} → {len(candidate_ids)} segments")

            # Shape Search: Target SEGMENT vs Kandidaten Segmente
            rankings = {}
            for mode in available_modes:
                mode_results = await self.shape.search_by_embedding(
                    target_id=target_segment_id,  # ✅ SEGMENT als Target!
                    mode=mode,
                    limit=limit * 10,
                    candidate_ids=candidate_ids
                )

                # ✅ WICHTIG: Immer nur Segmente behalten!
                mode_results = await self._filter_results_segments_only(mode_results)

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

    async def _filter_bahnen_only(self, segment_ids: List[str]) -> List[str]:
        """Filtert Liste: Nur Bahnen (segment_id = bahn_id)"""
        if not segment_ids:
            return []

        try:
            query = """
                    SELECT segment_id
                    FROM bewegungsdaten.bahn_metadata
                    WHERE segment_id = ANY ($1)
                      AND segment_id = bahn_id \
                    """
            results = await self.connection.fetch(query, segment_ids)
            return [row['segment_id'] for row in results]
        except Exception as e:
            logger.error(f"Error filtering bahnen: {e}")
            return []

    async def _filter_segments_only(self, segment_ids: List[str]) -> List[str]:
        """Filtert Liste: Nur Segmente (segment_id != bahn_id)"""
        if not segment_ids:
            return []

        try:
            query = """
                    SELECT segment_id
                    FROM bewegungsdaten.bahn_metadata
                    WHERE segment_id = ANY ($1)
                      AND segment_id != bahn_id \
                    """
            results = await self.connection.fetch(query, segment_ids)
            return [row['segment_id'] for row in results]
        except Exception as e:
            logger.error(f"Error filtering segments: {e}")
            return []

    async def _filter_results_bahnen_only(self, results: List[Dict]) -> List[Dict]:
        """Filtert Results: Nur Bahnen behalten"""
        segment_ids = [r['segment_id'] for r in results]
        bahn_ids = await self._filter_bahnen_only(segment_ids)
        bahn_set = set(bahn_ids)
        return [r for r in results if r['segment_id'] in bahn_set]

    async def _filter_results_segments_only(self, results: List[Dict]) -> List[Dict]:
        """Filtert Results: Nur Segmente behalten"""
        segment_ids = [r['segment_id'] for r in results]
        seg_ids = await self._filter_segments_only(segment_ids)
        seg_set = set(seg_ids)
        return [r for r in results if r['segment_id'] in seg_set]

    async def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """Reichert Ergebnisse mit Features aus bahn_metadata an"""
        if not results:
            return []

        segment_ids = [r['segment_id'] for r in results]

        try:
            query = """
                    SELECT segment_id, \
                           bahn_id, \
                           duration, \
                           length, \
                           median_twist_ist, \
                           median_acceleration_ist, \
                           movement_type
                    FROM bewegungsdaten.bahn_metadata
                    WHERE segment_id = ANY ($1) \
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

    async def search_adaptive(
            self,
            target_id: str,
            modes: Optional[List[str]] = None,
            weights: Optional[Dict[str, float]] = None,
            bahn_limit: int = 10,
            segment_limit: int = 5
    ) -> Dict:
        """
        ADAPTIVE Hierarchical Search
        """
        try:
            candidate_ids, tolerance = await self.prefilter.adaptive_prefilter(
                target_id=target_id,
                max_candidates=10000,
                min_candidates=10
            )

            return await self.search_similar(
                target_id=target_id,
                modes=modes,
                weights=weights,
                use_prefilter=True,
                prefilter_tolerance=tolerance,
                bahn_limit=bahn_limit,
                segment_limit=segment_limit
            )

        except Exception as e:
            logger.error(f"Error in adaptive search: {e}")
            return {
                'target_id': target_id,
                'error': str(e),
                'bahn_similarity': {},
                'segment_similarity': []
            }