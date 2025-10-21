# backend/scripts/calculators/embedding_calculator.py

import numpy as np
from typing import List, Dict, Optional, Literal
import logging

logger = logging.getLogger(__name__)


class EmbeddingCalculator:
    """
    Universal Embedding Calculator
    Berechnet Joint, Position und Orientation Embeddings
    """

    def __init__(
            self,
            joint_samples: int = 50,  # 50 × 6 = 300
            position_samples: int = 50,  # 50 × 3 = 150
            orientation_samples: int = 38  # 38 × 4 = 152 ≈ 150
    ):
        self.joint_samples = joint_samples
        self.position_samples = position_samples
        self.orientation_samples = orientation_samples

    def compute_joint_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Args: List[Dict] mit joint_1..joint_6
        Returns: np.ndarray(300,)
        """
        if len(data) < 10:
            return None

        # NumPy array (n_points, 6)
        traj = np.array([
            [r['joint_1'], r['joint_2'], r['joint_3'],
             r['joint_4'], r['joint_5'], r['joint_6']]
            for r in data
        ], dtype=np.float32)

        # Resample + flatten + normalize
        resampled = self._resample(traj, self.joint_samples)
        flat = resampled.flatten()
        return self._l2_normalize(flat)

    def compute_position_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Position Embedding MIT Normalisierung auf Startpunkt
        """
        if len(data) < 10:
            return None

        # NumPy array (n_points, 3)
        traj = np.array([
            [r['x_soll'], r['y_soll'], r['z_soll']]
            for r in data
        ], dtype=np.float32)

        # ✅ NORMALISIERUNG: Startpunkt auf (0,0,0) verschieben
        start_point = traj[0]
        traj_normalized = traj - start_point

        # Resample + flatten + L2 normalize
        resampled = self._resample(traj_normalized, self.position_samples)
        flat = resampled.flatten()
        return self._l2_normalize(flat)

    def compute_orientation_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Args: List[Dict] mit qw_soll, qx_soll, qy_soll, qz_soll
        Returns: np.ndarray(152,) ≈ 150
        """
        if len(data) < 10:
            return None

        traj = np.array([
            [r['qw_soll'], r['qx_soll'], r['qy_soll'], r['qz_soll']]
            for r in data
        ], dtype=np.float32)

        resampled = self._resample(traj, self.orientation_samples)
        flat = resampled.flatten()
        return self._l2_normalize(flat)

    # Helper methods
    def _resample(self, trajectory: np.ndarray, n_samples: int) -> np.ndarray:
        """Resample trajectory to n_samples"""
        indices = np.linspace(0, len(trajectory) - 1, n_samples, dtype=int)
        return trajectory[indices]

    def _l2_normalize(self, vec: np.ndarray) -> np.ndarray:
        """L2 normalization"""
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec