# backend/app/utils/rrf_ranker.py

from typing import List, Dict, Optional
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RRFRanker:
    """
    Reciprocal Rank Fusion (RRF) für Multi-Modal Ranking

    RRF Formula: score(d) = sum_i [ weight_i / (k + rank_i(d)) ]

    Paper: "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"
    """

    def __init__(self, k: int = 50):
        """
        Args:
            k: RRF constant (default: 60, aus dem Paper)
                Kleinere k = mehr Gewicht auf Top-Ranks
                Größere k = gleichmäßigere Verteilung
        """
        self.k = k

    def fuse_rankings(
            self,
            rankings: Dict[str, List[Dict]],
            weights: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Kombiniert mehrere Rankings mit RRF

        Args:
            rankings: Dict[mode_name, List[results]]
                z.B. {'joint': [...], 'position': [...], 'orientation': [...]}
                Jedes result dict muss 'segment_id' und 'rank' haben

            weights: Optional Dict[mode_name, weight]
                z.B. {'joint': 0.5, 'position': 0.3, 'orientation': 0.2}
                Default: Gleiche Gewichtung (1.0 für alle)

        Returns:
            List[Dict] sortiert nach RRF score (höchster zuerst)
            Jedes Dict enthält: segment_id, rrf_score, rank, mode_scores
        """
        if not rankings:
            logger.warning("No rankings provided for fusion")
            return []

        # Default: Gleiche Gewichtung
        if weights is None:
            weights = {mode: 1.0 for mode in rankings.keys()}

        # Normalize weights (optional, für klarere Interpretation)
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
        else:
            normalized_weights = weights

        # RRF Score Berechnung
        rrf_scores = defaultdict(float)
        mode_details = defaultdict(lambda: {})  # Für Debugging/Transparency
        all_segment_ids = set()

        for mode, results in rankings.items():
            weight = normalized_weights.get(mode, 0.0)

            if weight == 0.0:
                logger.info(f"Skipping mode '{mode}' (weight=0)")
                continue

            for result in results:
                segment_id = result.get('segment_id')
                rank = result.get('rank')

                if segment_id is None or rank is None:
                    logger.warning(f"Missing segment_id or rank in {mode} result")
                    continue

                # RRF Formula
                rrf_contribution = weight / (self.k + rank)
                rrf_scores[segment_id] += rrf_contribution

                # Details speichern
                if segment_id not in mode_details:
                    mode_details[segment_id] = {}

                mode_details[segment_id][mode] = {
                    'rank': rank,
                    'distance': result.get('distance'),
                    'rrf_contribution': rrf_contribution
                }

                all_segment_ids.add(segment_id)

        if not rrf_scores:
            logger.warning("No valid RRF scores computed")
            return []

        # Sortiere nach RRF Score (höchster = bester)
        sorted_segments = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Format Output
        fused_results = []
        for final_rank, (segment_id, rrf_score) in enumerate(sorted_segments, start=1):
            fused_results.append({
                'segment_id': segment_id,
                'rrf_score': round(rrf_score, 6),
                'rank': final_rank,
                'mode_scores': mode_details[segment_id]
            })

        logger.info(
            f"RRF Fusion complete: {len(fused_results)} results, "
            f"modes={list(rankings.keys())}, "
            f"weights={normalized_weights}"
        )

        return fused_results

    def explain_score(self, result: Dict, weights: Dict[str, float] = None) -> str:
        """
        Erklärt wie der RRF Score zustande kam (für Debugging)

        Args:
            result: Ein Result-Dict aus fuse_rankings()
            weights: Die verwendeten Weights

        Returns:
            Human-readable Erklärung
        """
        segment_id = result['segment_id']
        rrf_score = result['rrf_score']
        mode_scores = result.get('mode_scores', {})

        lines = [
            f"Segment: {segment_id}",
            f"Final RRF Score: {rrf_score:.6f}",
            f"Final Rank: {result['rank']}",
            "",
            "Breakdown by mode:"
        ]

        for mode, details in mode_scores.items():
            rank = details['rank']
            contrib = details['rrf_contribution']
            distance = details.get('distance', 'N/A')

            weight = weights.get(mode, 1.0) if weights else 1.0

            lines.append(
                f"  {mode.upper()}: "
                f"rank={rank}, distance={distance}, "
                f"weight={weight:.2f}, "
                f"contribution={contrib:.6f}"
            )

        return "\n".join(lines)

    def batch_fuse(
            self,
            batch_rankings: Dict[str, Dict[str, List[Dict]]],
            weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, List[Dict]]:
        """
        Fusioniert Rankings für mehrere Targets auf einmal

        Args:
            batch_rankings: Dict[target_id, Dict[mode, results]]
            weights: Weights für alle Targets

        Returns:
            Dict[target_id, fused_results]
        """
        fused_batch = {}

        for target_id, rankings in batch_rankings.items():
            fused = self.fuse_rankings(rankings, weights)
            fused_batch[target_id] = fused

        logger.info(f"Batch fusion complete: {len(fused_batch)} targets")

        return fused_batch

    def filter_by_threshold(
            self,
            results: List[Dict],
            min_score: float = 0.0,
            max_results: Optional[int] = None
    ) -> List[Dict]:
        """
        Filtert Results nach min RRF Score

        Args:
            results: Output von fuse_rankings()
            min_score: Minimum RRF Score
            max_results: Optional max Anzahl

        Returns:
            Gefilterte Results
        """
        filtered = [r for r in results if r['rrf_score'] >= min_score]

        if max_results:
            filtered = filtered[:max_results]

        logger.info(
            f"Filtered {len(results)} → {len(filtered)} results "
            f"(min_score={min_score}, max={max_results})"
        )

        return filtered