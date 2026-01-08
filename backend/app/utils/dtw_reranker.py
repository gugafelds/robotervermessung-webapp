# backend/app/utils/dtw_reranker.py

import numpy as np
from typing import Dict, List, Tuple, Optional
from dtaidistance import dtw
import logging

logger = logging.getLogger(__name__)


class DTWReranker:
    """
    DTW-based reranking with Lower Bounds (LB_Kim + LB_Keogh)
    Implements same logic as MATLAB two_stage_retrieval.m
    """

    def __init__(
        self,
        cdtw_window: float = 0.2,
        lb_kim_keep_ratio: float = 0.9,
        lb_keogh_candidates: int = 500,
        normalize_dtw: bool = False,
        use_rotation_alignment: bool = False
    ):
        """
        Initialize DTW Reranker
        
        Args:
            cdtw_window: Constrained DTW window (default: 0.2 = 20%)
            lb_kim_keep_ratio: Keep ratio after LB_Kim (default: 0.9 = 90%)
            lb_keogh_candidates: Target count after LB_Keogh (default: 500)
            normalize_dtw: Apply normalization (default: False)
            use_rotation_alignment: Align rotation (default: False)
        """
        self.cdtw_window = cdtw_window
        self.lb_kim_keep_ratio = lb_kim_keep_ratio
        self.lb_keogh_candidates = lb_keogh_candidates
        self.normalize_dtw = normalize_dtw
        self.use_rotation_alignment = use_rotation_alignment

    def lb_kim(self, seq1: np.ndarray, seq2: np.ndarray) -> float:
        """
        LB_Kim: Ultra-fast lower bound using 4 critical points
        Based on Kim et al. (2001)
        
        Extracts 4 features:
        - First point
        - Last point
        - Minimum (per dimension)
        - Maximum (per dimension)
        
        Args:
            seq1: Query sequence (n1, d)
            seq2: Candidate sequence (n2, d)
        
        Returns:
            Lower bound distance (max of 4 feature distances)
        """
        if seq1.size == 0 or seq2.size == 0:
            return np.inf
        
        if len(seq1) < 2 or len(seq2) < 2:
            return np.inf
        
        # Resample seq2 to match seq1 length (for fair comparison)
        n1 = len(seq1)
        n2 = len(seq2)
        d = seq1.shape[1]
        
        if n1 != n2:
            # Linear interpolation for resampling
            seq2_resampled = np.zeros((n1, d))
            for dim in range(d):
                seq2_resampled[:, dim] = np.interp(
                    np.linspace(0, n2 - 1, n1),
                    np.arange(n2),
                    seq2[:, dim]
                )
            seq2 = seq2_resampled
        
        # Extract 4 features (vectorized)
        first1 = seq1[0, :]
        first2 = seq2[0, :]
        
        last1 = seq1[-1, :]
        last2 = seq2[-1, :]
        
        min1 = np.min(seq1, axis=0)
        min2 = np.min(seq2, axis=0)
        
        max1 = np.max(seq1, axis=0)
        max2 = np.max(seq2, axis=0)
        
        # Compute Euclidean distances for each feature
        d_first = np.linalg.norm(first1 - first2)
        d_last = np.linalg.norm(last1 - last2)
        d_min = np.linalg.norm(min1 - min2)
        d_max = np.linalg.norm(max1 - max2)
        
        # Lower bound = max of 4 distances
        lb_dist = max(d_first, d_last, d_min, d_max)
        
        return lb_dist

    def lb_keogh(
        self, 
        seq1: np.ndarray, 
        seq2: np.ndarray,
        window: Optional[int] = None
    ) -> float:
        """
        LB_Keogh: Envelope-based lower bound
        
        Args:
            seq1: Query sequence (n, d)
            seq2: Candidate sequence (m, d)
            window: Sakoe-Chiba window size (if None, uses self.cdtw_window)
        
        Returns:
            Lower bound distance
        """
        if seq1.size == 0 or seq2.size == 0:
            return np.inf
        
        if window is None:
            window = int(len(seq1) * self.cdtw_window)
        
        # Flatten for dtaidistance (expects 1D)
        # For multi-dimensional, compute per dimension and sum
        lb_sum = 0.0
        
        for dim in range(seq1.shape[1]):
            s1_dim = seq1[:, dim]
            s2_dim = seq2[:, dim]
            
            # Create envelope for seq2
            n = len(s2_dim)
            upper = np.zeros(n)
            lower = np.zeros(n)
            
            for i in range(n):
                start_idx = max(0, i - window)
                end_idx = min(n, i + window + 1)
                upper[i] = np.max(s2_dim[start_idx:end_idx])
                lower[i] = np.min(s2_dim[start_idx:end_idx])
            
            # Resample envelope to match seq1 length
            if len(s1_dim) != len(upper):
                upper_resampled = np.interp(
                    np.linspace(0, n - 1, len(s1_dim)),
                    np.arange(n),
                    upper
                )
                lower_resampled = np.interp(
                    np.linspace(0, n - 1, len(s1_dim)),
                    np.arange(n),
                    lower
                )
            else:
                upper_resampled = upper
                lower_resampled = lower
            
            # Compute lower bound for this dimension
            for j in range(len(s1_dim)):
                if s1_dim[j] > upper_resampled[j]:
                    lb_sum += (s1_dim[j] - upper_resampled[j]) ** 2
                elif s1_dim[j] < lower_resampled[j]:
                    lb_sum += (lower_resampled[j] - s1_dim[j]) ** 2
        
        return np.sqrt(lb_sum)

    def compute_cdtw(
        self,
        seq1: np.ndarray,
        seq2: np.ndarray
    ) -> float:
        """
        Compute constrained DTW (cDTW) with Sakoe-Chiba band
        
        Args:
            seq1: Query sequence (n, d)
            seq2: Candidate sequence (m, d)
        
        Returns:
            DTW distance
        """
        if seq1.size == 0 or seq2.size == 0:
            return np.inf
        
        # Compute window size
        window_size = int(max(len(seq1), len(seq2)) * self.cdtw_window)
        
        # dtaidistance expects 1D arrays
        # For multi-dimensional: compute DTW per dimension and sum
        total_distance = 0.0
        
        for dim in range(seq1.shape[1]):
            s1_dim = seq1[:, dim].astype(np.float64)
            s2_dim = seq2[:, dim].astype(np.float64)
            
            try:
                distance = dtw.distance(
                    s1_dim,
                    s2_dim,
                    window=window_size,
                    use_pruning=False  # We handle pruning manually with LBs
                )
                total_distance += distance ** 2
            except Exception as e:
                logger.warning(f"DTW computation failed for dimension {dim}: {e}")
                return np.inf
        
        return np.sqrt(total_distance)

    def rerank(
        self,
        query_trajectory: np.ndarray,
        candidates_data: Dict[str, np.ndarray],
        level: str = 'trajectory',
        limit: int = 50
    ) -> List[Dict]:
        """
        Rerank candidates using DTW with adaptive Lower Bounds
        
        Pipeline:
        1. Determine LB strategy based on K
        2. Apply LB_Kim (if enabled)
        3. Apply LB_Keogh (if enabled)
        4. Compute full cDTW on survivors
        5. Sort and return Top-N
        
        Args:
            query_trajectory: Query sequence (n, d)
            candidates_data: {candidate_id: trajectory_array}
            level: 'trajectory' or 'segment'
            limit: Final Top-K to return
        
        Returns:
            List of ranked results with DTW distances
        """
        K = len(candidates_data)
        candidate_ids = list(candidates_data.keys())
        
        logger.info(f"DTW Reranking: K={K}, Level={level}, Limit={limit}")
        
        # ===================================================================
        # ADAPTIVE LB STRATEGY (same as MATLAB)
        # ===================================================================
        if K <= 50:
            use_lb_kim = False
            use_lb_keogh = False
            lb_kim_keep = K
            lb_keogh_keep = K
        elif K <= 200:
            use_lb_kim = True
            use_lb_keogh = False
            lb_kim_keep = int(K * 0.6)  # Keep 60%
            lb_keogh_keep = K
        else:  # K > 200
            use_lb_kim = True
            use_lb_keogh = True
            lb_kim_keep = int(K * self.lb_kim_keep_ratio)  # 90%
            lb_keogh_keep = min(self.lb_keogh_candidates, lb_kim_keep)
        
        logger.info(
            f"LB Strategy: Kim={use_lb_kim} (keep {lb_kim_keep}), "
            f"Keogh={use_lb_keogh} (keep {lb_keogh_keep})"
        )
        
        # ===================================================================
        # PHASE 1: LB_Kim Filtering
        # ===================================================================
        candidates_after_kim = candidate_ids.copy()
        
        if use_lb_kim:
            logger.info(f"Phase 1: LB_Kim filtering ({K} → {lb_kim_keep})")
            
            lb_kim_scores = []
            for cand_id in candidate_ids:
                cand_traj = candidates_data[cand_id]
                lb_score = self.lb_kim(query_trajectory, cand_traj)
                lb_kim_scores.append((cand_id, lb_score))
            
            # Sort by LB_Kim score
            lb_kim_scores.sort(key=lambda x: x[1])
            
            # Keep top lb_kim_keep
            candidates_after_kim = [cand_id for cand_id, _ in lb_kim_scores[:lb_kim_keep]]
            
            logger.info(f"  ✓ LB_Kim: {K} → {len(candidates_after_kim)} ({100*(1-len(candidates_after_kim)/K):.1f}% pruned)")
        
        # ===================================================================
        # PHASE 2: LB_Keogh Filtering
        # ===================================================================
        candidates_after_keogh = candidates_after_kim.copy()
        
        if use_lb_keogh and len(candidates_after_kim) > lb_keogh_keep:
            logger.info(f"Phase 2: LB_Keogh filtering ({len(candidates_after_kim)} → {lb_keogh_keep})")
            
            lb_keogh_scores = []
            for cand_id in candidates_after_kim:
                cand_traj = candidates_data[cand_id]
                lb_score = self.lb_keogh(query_trajectory, cand_traj)
                lb_keogh_scores.append((cand_id, lb_score))
            
            # Sort by LB_Keogh score
            lb_keogh_scores.sort(key=lambda x: x[1])
            
            # Keep top lb_keogh_keep
            candidates_after_keogh = [cand_id for cand_id, _ in lb_keogh_scores[:lb_keogh_keep]]
            
            logger.info(f"  ✓ LB_Keogh: {len(candidates_after_kim)} → {len(candidates_after_keogh)} ({100*(1-len(candidates_after_keogh)/len(candidates_after_kim)):.1f}% pruned)")
        elif use_lb_keogh:
            logger.info(f"  ⚠ LB_Kim already filtered to target size - skipping LB_Keogh")
        
        # Total pruning
        total_pruning = 1 - (len(candidates_after_keogh) / K)
        logger.info(f"  ✓ Total Pruning: {total_pruning*100:.1f}% (from {K} to {len(candidates_after_keogh)} before DTW)")
        
        # ===================================================================
        # PHASE 3: Full cDTW Computation
        # ===================================================================
        logger.info(f"Phase 3: DTW computation on {len(candidates_after_keogh)} candidates")
        
        dtw_results = []
        num_dtw_calls = 0
        
        for cand_id in candidates_after_keogh:
            cand_traj = candidates_data[cand_id]
            
            # Compute full cDTW
            dtw_distance = self.compute_cdtw(query_trajectory, cand_traj)
            num_dtw_calls += 1
            
            # Extract bahn_id (remove segment suffix if present)
            if '_' in cand_id:
                bahn_id = cand_id.rsplit('_', 1)[0]
            else:
                bahn_id = cand_id
            
            dtw_results.append({
                'segment_id': cand_id,
                'bahn_id': bahn_id,
                'dtw_distance': float(dtw_distance),
                'similarity_score': float(1.0 / (1.0 + dtw_distance)),
                'used_lb_kim': use_lb_kim,
                'used_lb_keogh': use_lb_keogh
            })
        
        # ===================================================================
        # SORT & RETURN TOP-N
        # ===================================================================
        dtw_results.sort(key=lambda x: x['dtw_distance'])
        
        # Add ranks
        for idx, result in enumerate(dtw_results[:limit]):
            result['rank'] = idx + 1
        
        logger.info(
            f"  ✓ DTW completed: {num_dtw_calls} calls, "
            f"Top-1 distance: {dtw_results[0]['dtw_distance']:.2f}"
        )
        
        return dtw_results[:limit]

    def rerank_batch_trajectories(
        self,
        query_data: Dict,
        candidates_data: Dict[str, Dict],
        limit: int = 50
    ) -> List[Dict]:
        """
        Rerank trajectory-level candidates
        
        Args:
            query_data: {'trajectory': array, 'segments': {...}}
            candidates_data: {bahn_id: {'trajectory': array, 'segments': {...}}}
            limit: Final Top-K
        
        Returns:
            List of ranked trajectory results
        """
        query_traj = query_data['trajectory']
        
        # Extract trajectory-level data from candidates
        candidates_trajs = {
            bahn_id: data['trajectory']
            for bahn_id, data in candidates_data.items()
        }
        
        return self.rerank(
            query_trajectory=query_traj,
            candidates_data=candidates_trajs,
            level='trajectory',
            limit=limit
        )

    def rerank_batch_segments(
        self,
        query_data: Dict,
        candidates_data: Dict[str, Dict],
        limit: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        Rerank segment-level candidates (per query segment)
        
        Args:
            query_data: {'trajectory': array, 'segments': {...}}
            candidates_data: {bahn_id: {'trajectory': array, 'segments': {...}}}
            limit: Final Top-K per segment
        
        Returns:
            {query_segment_id: [ranked_results]}
        """
        query_segments = query_data['segments']
        
        # Flatten all candidate segments
        all_candidate_segments = {}
        for bahn_id, data in candidates_data.items():
            for seg_id, seg_array in data['segments'].items():
                all_candidate_segments[seg_id] = seg_array
        
        # Rerank for each query segment
        segment_results = {}
        
        for query_seg_id, query_seg_array in query_segments.items():
            logger.info(f"Reranking for query segment: {query_seg_id}")
            
            results = self.rerank(
                query_trajectory=query_seg_array,
                candidates_data=all_candidate_segments,
                level='segment',
                limit=limit
            )
            
            segment_results[query_seg_id] = results
        
        return segment_results