# backend/app/utils/dtw_reranker.py

import numpy as np
from typing import Dict, List
from dtaidistance import dtw_ndim
import logging

logger = logging.getLogger(__name__)


def _cdtw(seq1: np.ndarray, seq2: np.ndarray, window_percent: float = 0.2) -> float:
    """
    Constrained DTW with Sakoe-Chiba band.
    Mirrors MATLAB cDTW.m exactly:
      - Translation removal (seq - seq[0]) for position mode
      - window = round(max(n, m) * window_percent), min = abs(n - m)
      - Multi-dimensional: norm(seq1[i] - seq2[j]) as cost

    Args:
        seq1: Query sequence (n, d) - already preprocessed
        seq2: Candidate sequence (m, d) - already preprocessed
        window_percent: Sakoe-Chiba band as fraction of max length (default: 0.2)

    Returns:
        DTW distance (float)
    """
    if seq1.size == 0 or seq2.size == 0:
        return np.inf

    n, m = len(seq1), len(seq2)
    window = max(round(max(n, m) * window_percent), abs(n - m))

    # Use dtaidistance fast C implementation for multi-dim
    # dtw_ndim expects (n, d) arrays — exactly what we have

    dist = dtw_ndim.distance_fast(
        seq1.astype(np.double),
        seq2.astype(np.double),
        window=window,
        inner_dist='euclidean'
    )
    return float(dist)


def _lb_kim(seq1: np.ndarray, seq2: np.ndarray) -> float:
    """
    LB_Kim: lower bound using 4 critical points (first, last, min, max).
    Mirrors MATLAB LB_Kim.m.
    Sequences must already be resampled to the same length.
    """
    if len(seq1) < 2 or len(seq2) < 2:
        return np.inf

    n1, n2 = len(seq1), len(seq2)
    if n1 != n2:
        # Resample seq2 to seq1 length (pchip → np.interp as approximation)
        d = seq1.shape[1]
        seq2_r = np.zeros((n1, d))
        for dim in range(d):
            seq2_r[:, dim] = np.interp(
                np.linspace(0, n2 - 1, n1), np.arange(n2), seq2[:, dim]
            )
        seq2 = seq2_r

    d_first = np.linalg.norm(seq1[0] - seq2[0])
    d_last = np.linalg.norm(seq1[-1] - seq2[-1])
    d_min = np.linalg.norm(seq1.min(axis=0) - seq2.min(axis=0))
    d_max = np.linalg.norm(seq1.max(axis=0) - seq2.max(axis=0))

    return max(d_first, d_last, d_min, d_max)


def _lb_keogh(seq1: np.ndarray, seq2: np.ndarray, window_percent: float) -> float:
    """
    LB_Keogh: envelope-based lower bound.
    Mirrors MATLAB LB_Keogh.m — vectorized with np.maximum/minimum.
    """
    if seq1.size == 0 or seq2.size == 0:
        return np.inf

    n2 = len(seq2)
    window = int(n2 * window_percent)

    lb_sum = 0.0
    for dim in range(seq1.shape[1]):
        s2 = seq2[:, dim]

        # Build envelope (vectorized)
        idx = np.arange(n2)
        i_start = np.maximum(0, idx - window)
        i_end = np.minimum(n2, idx + window + 1)
        upper = np.array([s2[i_start[i]:i_end[i]].max() for i in range(n2)])
        lower = np.array([s2[i_start[i]:i_end[i]].min() for i in range(n2)])

        # Resample envelope to seq1 length if needed
        n1 = len(seq1)
        if n1 != n2:
            x_old = np.linspace(0, n2 - 1, n2)
            x_new = np.linspace(0, n2 - 1, n1)
            upper = np.interp(x_new, x_old, upper)
            lower = np.interp(x_new, x_old, lower)

        s1 = seq1[:, dim]
        above = np.maximum(0.0, s1 - upper)
        below = np.maximum(0.0, lower - s1)
        lb_sum += np.sum(above ** 2) + np.sum(below ** 2)

    return float(np.sqrt(lb_sum))


def rerank(
        query_seq: np.ndarray,
        candidates: Dict[str, np.ndarray],
        window_percent: float = 0.2,
        lb_threshold: int = 500,
        mode: str = 'position',
        lb_kim_keep_ratio: float = 0.9,
        lb_keogh_keep: int = 500,
        limit: int = 50,
        remove_translation: bool = True,
) -> List[Dict]:
    K = len(candidates)
    use_lb = K > lb_threshold

    def _preprocess(seq: np.ndarray) -> np.ndarray:
        seq = seq.astype(np.float64)

        if mode == 'joint':
            min_vals = seq.min(axis=0)
            max_vals = seq.max(axis=0)
            range_vals = max_vals - min_vals
            range_vals[range_vals < 1e-9] = 1.0
            seq = (seq - min_vals) / range_vals

        if remove_translation and mode == 'position' and len(seq) > 0:
            seq = seq - seq[0]

        return seq

    q = _preprocess(query_seq)
    cand_ids = list(candidates.keys())
    cand_seqs = {cid: _preprocess(candidates[cid]) for cid in cand_ids}

    # Phase 1: LB_Kim
    survivors = cand_ids.copy()
    if use_lb:
        kim_keep = round(K * lb_kim_keep_ratio)
        scores = [(cid, _lb_kim(q, cand_seqs[cid])) for cid in survivors]
        scores.sort(key=lambda x: x[1])
        survivors = [cid for cid, _ in scores[:kim_keep]]
        logger.info(f"LB_Kim: {K} → {len(survivors)}")

    # Phase 2: LB_Keogh
    if use_lb and len(survivors) > lb_keogh_keep:
        scores = [(cid, _lb_keogh(q, cand_seqs[cid], window_percent)) for cid in survivors]
        scores.sort(key=lambda x: x[1])
        survivors = [cid for cid, _ in scores[:lb_keogh_keep]]
        logger.info(f"LB_Keogh: → {len(survivors)}")

    # Phase 3: Full cDTW
    results = []
    for cid in survivors:
        dist = _cdtw(q, cand_seqs[cid], window_percent)
        traj_id = cid.rsplit('_', 1)[0] if '_' in cid else cid
        results.append({
            'id': cid,
            'traj_id': traj_id,
            'dtw_distance': dist,
            'similarity_score': 1.0 / (1.0 + dist),
            'used_lb_kim': use_lb,
            'used_lb_keogh': use_lb and K > lb_keogh_keep,
        })

    results.sort(key=lambda x: x['dtw_distance'])

    for rank, r in enumerate(results[:limit], start=1):
        r['rank'] = rank

    logger.info(
        f"DTW reranking done: K={K}, DTW calls={len(survivors)}, "
        f"Top-1={results[0]['dtw_distance']:.4f}" if results else "No results"
    )

    return results[:limit]