"""Run from backend/:  python -m app.utils.feature_prediction.test_predictor"""
from app.utils.feature_prediction.predictor import _aggregate_trajectory_decomposed, _weighted_median


def test_weighted_median():
    assert _weighted_median([1.0, 2.0, 10.0], [1, 1, 1]) == 2.0           # outlier doesn't pull it up
    assert _weighted_median([1.0, 2.0, 10.0], [1, 1, 5]) == 10.0          # heavy weight wins
    assert _weighted_median([3.0, 1.0, 2.0], [1, 2, 1]) == 1.0            # unsorted input, cum weight hits 1/2 at 1.0


def test_duration_weighting():
    segs = [{'p_hat': 0.2, 'sigma': 0.1}, {'p_hat': 0.6, 'sigma': 0.1}]
    # 3 s slow segment vs 1 s fast one -> time-weighted 0.3 (path length would have favoured the fast one)
    assert _aggregate_trajectory_decomposed(segs, weights=[3.0, 1.0])['p_hat'] == 0.3


if __name__ == '__main__':
    test_weighted_median()
    test_duration_weighting()
    print('ok')
