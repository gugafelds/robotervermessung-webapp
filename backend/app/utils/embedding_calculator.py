# backend/scripts/calculators/embedding_calculator.py

import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingCalculator:
    """
    Universal Embedding Calculator
    Berechnet Joint, Position, Orientation, Velocity und Acceleration Embeddings
    """

    def __init__(
            self,
            joint_samples: int = 50,        # 50 × 6 = 300
            position_samples: int = 100,    # 100 × 3 = 300
            orientation_samples: int = 50,  # 50 × 4 = 200
            velocity_samples: int = 100,    # 100 × 3 = 300
            acceleration_samples: int = 50   # 50 × 3 = 150
    ):
        self.joint_samples = joint_samples
        self.position_samples = position_samples
        self.orientation_samples = orientation_samples
        self.velocity_samples = velocity_samples
        self.acceleration_samples = acceleration_samples

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
        ✅ Shape Embedding: Nur Form, NICHT absolute Position
        
        Findet ähnliche Formen unabhängig von Position im Arbeitsraum
        """
        if len(data) < 10:
            return None

        traj = np.array([
            [r['x_soll'], r['y_soll'], r['z_soll']]
            for r in data
        ], dtype=np.float32)

        start_point = traj[0]
        traj_normalized = traj - start_point

        centroid = np.mean(traj, axis=0)
        traj_normalized = traj - centroid
        
        max_extent = np.max(np.abs(traj_normalized))
        if max_extent > 1e-6:
            traj_normalized = traj_normalized / max_extent  # [-1, 1]
        
        resampled = self._resample(traj_normalized, self.position_samples)
        flat = resampled.flatten()
        
        return self._l2_normalize(flat)

    def compute_orientation_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Args: List[Dict] mit qw_soll, qx_soll, qy_soll, qz_soll
        Returns: np.ndarray(200,)
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

    def compute_velocity_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Legacy method - ruft die neue kombinierte Methode auf
        """
        vel_emb, _ = self.compute_velocity_and_acceleration_embeddings(data)
        return vel_emb

    def compute_acceleration_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        """
        Legacy method - ruft die neue kombinierte Methode auf
        
        DEPRECATED: Nutze compute_velocity_and_acceleration_embeddings() direkt
        """
        _, acc_emb = self.compute_velocity_and_acceleration_embeddings(data)
        return acc_emb
    
    def compute_velocity_and_acceleration_embeddings(
            self, 
            data: List[Dict]
    ) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        ✅ OPTIMIERT: Berechnet Velocity UND Acceleration in einem Durchlauf
        
        Args: List[Dict] mit 'x_soll', 'y_soll', 'z_soll', 'timestamp'
        Returns: 
            (velocity_embedding, acceleration_embedding)
            - velocity_embedding: np.ndarray(300,) = 100 × 3
            - acceleration_embedding: np.ndarray(150,) = 50 × 3
        """
        if len(data) < 10:
            return None, None

        # Position und Zeit extrahieren
        positions = np.array([
            [r['x_soll'], r['y_soll'], r['z_soll']]
            for r in data
        ], dtype=np.float32)
        
        timestamps = np.array([r['timestamp'] for r in data], dtype=np.float64)
        
        # ✅ Erste Ableitung: Velocity
        delta_pos = np.diff(positions, axis=0)  # (n-1, 3)
        delta_time = np.diff(timestamps)         # (n-1,)
        delta_time = np.where(delta_time == 0, 1e-9, delta_time)
        velocity = delta_pos / delta_time[:, np.newaxis]  # (n-1, 3)
        
        # Velocity Embedding
        vel_resampled = self._resample(velocity, self.velocity_samples)  # (100, 3)
        vel_flat = vel_resampled.flatten()  # (300,)
        vel_embedding = self._l2_normalize(vel_flat)
        
        # ✅ Zweite Ableitung: Acceleration (aus bereits berechneter Velocity!)
        acceleration_embedding = None
        if len(velocity) >= 2:  # Braucht mindestens 2 Velocity-Punkte
            delta_vel = np.diff(velocity, axis=0)    # (n-2, 3)
            delta_time2 = np.diff(timestamps[1:])    # (n-2,)
            delta_time2 = np.where(delta_time2 == 0, 1e-9, delta_time2)
            acceleration = delta_vel / delta_time2[:, np.newaxis]  # (n-2, 3)
            
            # Acceleration Embedding
            acc_resampled = self._resample(acceleration, self.acceleration_samples)  # (50, 3)
            acc_flat = acc_resampled.flatten()  # (150,)
            acceleration_embedding = self._l2_normalize(acc_flat)
        
        return vel_embedding, acceleration_embedding

    # Helper methods
    def _resample(self, trajectory: np.ndarray, n_samples: int) -> np.ndarray:
        """
        Resample trajectory to n_samples (for multi-dimensional data)
        
        Args:
            trajectory: (n_points, n_dims) array
            n_samples: target number of samples
        Returns:
            (n_samples, n_dims) array
        """
        indices = np.linspace(0, len(trajectory) - 1, n_samples, dtype=int)
        return trajectory[indices]

    def _l2_normalize(self, vec: np.ndarray) -> np.ndarray:
        """
        L2 normalization
        
        Args:
            vec: input vector
        Returns:
            normalized vector
        """
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec