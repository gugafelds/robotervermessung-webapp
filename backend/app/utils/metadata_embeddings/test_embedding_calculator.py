import numpy as np

from .embedding_calculator import EmbeddingCalculator, METADATA_FEATURES, _metadata_scale, metadata_features


def test_metadata_embedding():
    row = {'seg_id': 't_1', 'traj_id': 't', 'movement_type': 'circular', 'max_vel': 900.0, 'mean_vel': 450.0,
           'std_vel': 200.0, 'duration': 1.2, 'length': 500.0, 'weight': 12.0,
           'position_x': 1250.0, 'position_y': 0.0, 'position_z': 1050.0, 'max_accel': 1e9}
    assert metadata_features(row)[0] == 1.0
    assert metadata_features({**row, 'movement_type': 'llc'})[0] == 1 / 3
    assert metadata_features({**row, 'movement_type': 'l'})[0] == 0.0

    calc = EmbeddingCalculator()
    seg = calc.compute_metadata_embedding(row)
    traj = calc.compute_metadata_embedding({**row, 'seg_id': 't'})  # whole trajectory -> trajectory scale
    assert seg.shape == (len(METADATA_FEATURES),) and np.isclose(np.linalg.norm(seg), 1.0)
    s = _metadata_scale()['segment']
    z = (metadata_features(row) - s['mean']) / s['std'] * s['weight']
    assert np.allclose(seg, z / np.linalg.norm(z), atol=1e-6)
    assert not np.allclose(seg, traj)
    # accelerations are not part of the embedding
    assert np.allclose(seg, calc.compute_metadata_embedding({**row, 'max_accel': 0.0}))
