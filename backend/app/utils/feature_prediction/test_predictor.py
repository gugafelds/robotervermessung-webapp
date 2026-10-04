"""Run from backend/:  python -m app.utils.feature_prediction.test_predictor"""
import asyncio

from app.utils.feature_prediction.predictor import (
    DTW_SWITCH_D_PER_LENGTH, _aggregate_trajectory_decomposed, _weighted_median, predict_performance,
)


def test_weighted_median():
    assert _weighted_median([1.0, 2.0, 10.0], [1, 1, 1]) == 2.0           # outlier doesn't pull it up
    assert _weighted_median([1.0, 2.0, 10.0], [1, 1, 5]) == 10.0          # heavy weight wins
    assert _weighted_median([3.0, 1.0, 2.0], [1, 2, 1]) == 1.0            # unsorted input, cum weight hits 1/2 at 1.0


def test_duration_weighting():
    segs = [{'p_hat': 0.2, 'sigma': 0.1}, {'p_hat': 0.6, 'sigma': 0.1}]
    # 3 s slow segment vs 1 s fast one -> time-weighted 0.3 (path length would have favoured the fast one)
    assert _aggregate_trajectory_decomposed(segs, weights=[3.0, 1.0])['p_hat'] == 0.3


def _prognosis(stage2: bool, best_dtw: float) -> dict:
    """One 100 mm segment: shape neighbours measured 0.5, metadata neighbours measured 0.2."""
    shape = [{'seg_id': f's{i}', 'rrf_score': 0.03, 'dtw_distance': best_dtw + i, 'features': {'mean_distance': 0.5}}
             for i in range(3)]
    meta = [{'seg_id': f'm{i}', 'rrf_score': 1 / (61 + i), 'features': {'mean_distance': 0.2}} for i in range(3)]
    result = {'stage2_active': stage2, 'segment_similarity': [{
        'target_segment': 'q_1', 'target_segment_features': {'length': 100.0, 'duration': 1.0},
        'similar_segments': {'results': shape}}]}
    out = asyncio.run(predict_performance(result, {}, conn=None, conformal_active=False, meta_groups={'q_1': meta}))
    return out['prognosis']


def test_switch_rule():
    near, far = 0.5 * DTW_SWITCH_D_PER_LENGTH * 100, 2 * DTW_SWITCH_D_PER_LENGTH * 100
    p = _prognosis(stage2=True, best_dtw=near)            # near-identical path -> DTW neighbours
    assert p['segments'][0]['source'] == 'dtw' and p['decomposed']['p_hat'] == 0.5
    p = _prognosis(stage2=True, best_dtw=far)             # otherwise metadata neighbours, DTW match stats kept
    seg = p['segments'][0]
    assert seg['source'] == 'metadata' and seg['p_hat'] == 0.2 and seg['d_min'] == far
    assert seg['neighbor_ids'] == ['m0', 'm1', 'm2']
    p = _prognosis(stage2=False, best_dtw=near)           # Stage 1 always metadata
    assert p['segments'][0]['source'] == 'metadata' and p['s1_decomposed']['p_hat'] == 0.2


if __name__ == '__main__':
    test_weighted_median()
    test_duration_weighting()
    test_switch_rule()
    print('ok')
