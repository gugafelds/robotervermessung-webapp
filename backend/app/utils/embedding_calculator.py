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
    ):
        self.joint_samples = joint_samples
        self.position_samples = position_samples
        self.orientation_samples = orientation_samples
        self.velocity_samples = velocity_samples

    def compute_joint_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Joint Angles extrahieren
        traj = np.array([
            [r['joint_1'], r['joint_2'], r['joint_3'],
            r['joint_4'], r['joint_5'], r['joint_6']]
            for r in data
        ], dtype=np.float32)
        
        # Multi-Scale: coarse (50) + fine (250) = 300 samples
        coarse = self._resample(traj, 50)  # 50 × 6 = 300
        fine = self._resample(traj, 250)   # 250 × 6 = 1500
        
        # Concatenate + flatten
        combined = np.vstack([coarse, fine])  # (300, 6)
        flat = combined.flatten()  # (1800,)
        
        return self._l2_normalize(flat)

    def compute_position_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Position extrahieren
        traj = np.array([[r['x_soll'], r['y_soll'], r['z_soll']] 
                        for r in data], dtype=np.float32)

        # Normalisierung zu Startpunkt
        traj_normalized = traj - traj[0]
        
        # max_extent Normalisierung
        norms = np.linalg.norm(traj_normalized, axis=1)
        max_extent = np.max(norms)
        if max_extent > 1e-6:
            traj_normalized = traj_normalized / max_extent
        
        # Multi-Scale: coarse (50) + fine (250) = 300 samples
        coarse = self._resample(traj_normalized, 50)  # 50 × 3 = 150
        fine = self._resample(traj_normalized, 250)   # 250 × 3 = 750
        
        # Concatenate + flatten
        combined = np.vstack([coarse, fine])  # (300, 3)
        flat = combined.flatten()  # (900,)
        
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
    
    def compute_velocity_and_acceleration_embeddings(
            self, 
            data: List[Dict]
    ) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        ✅ OPTIMIERT: Berechnet Velocity UND Acceleration mit Glättung
        """
        if len(data) < 10:
            return None, None

        # Position und Zeit extrahieren
        positions = np.array([
            [r['x_soll'], r['y_soll'], r['z_soll']]
            for r in data
        ], dtype=np.float32)
        
        timestamps = np.array([r['timestamp'] for r in data], dtype=np.float64)
        
        # ⭐ NEU: Savitzky-Golay Filter für Position (glättet vor Ableitung!)
        from scipy.signal import savgol_filter
        
        window_length = min(33, len(positions) // 2 * 2 + 1)  # Muss ungerade sein
        if window_length < 5:
            window_length = 5
        
        positions_smooth = np.zeros_like(positions)
        for dim in range(3):
            positions_smooth[:, dim] = savgol_filter(
                positions[:, dim], 
                window_length=window_length, 
                polyorder=3
            )
        
        # ✅ Velocity aus geglätteter Position
        delta_pos = np.diff(positions_smooth, axis=0)
        delta_time = np.diff(timestamps)
        delta_time = np.where(delta_time == 0, 1e-9, delta_time)
        velocity = delta_pos / delta_time[:, np.newaxis]
        
        velocity_smooth = np.zeros_like(velocity)
        vel_window = min(33, len(velocity) // 2 * 2 + 1)
        if vel_window < 5:
            vel_window = 5
            
        for dim in range(3):
            velocity_smooth[:, dim] = savgol_filter(
                velocity[:, dim], 
                window_length=vel_window, 
                polyorder=2
            )
        
        # Velocity Embedding
        vel_resampled = self._resample(velocity_smooth, self.velocity_samples)
        vel_flat = vel_resampled.flatten()
        vel_embedding = self._l2_normalize(vel_flat)
        
        # ✅ Acceleration aus geglätteter Velocity
        acceleration_embedding = None
        if len(velocity_smooth) >= 2:
            delta_vel = np.diff(velocity_smooth, axis=0)
            delta_time2 = np.diff(timestamps[1:])
            delta_time2 = np.where(delta_time2 == 0, 1e-9, delta_time2)
            acceleration = delta_vel / delta_time2[:, np.newaxis]
            
        
        return vel_embedding, acceleration_embedding
    
    def compute_metadata_embedding(self, metadata: Dict) -> Optional[np.ndarray]:
        """
        Berechnet Metadata Embedding (14D)
        
        Args:
            metadata: Dict mit keys:
                - movement_type: str ('linear', 'circular', 'll', etc.)
                - length: float (mm)
                - min_twist_ist, max_twist_ist, mean_twist_ist, 
                median_twist_ist, std_twist_ist: float (mm/s)
                - min_acceleration_ist, max_acceleration_ist, 
                mean_acceleration_ist, median_acceleration_ist, 
                std_acceleration_ist: float (mm/s²)
        
        Returns:
            np.ndarray(14,) - normalisierter Metadata-Vektor
        """
        
        # === 1. Movement Type Encoding ===
        movement_str = metadata.get('movement_type', '').lower()
        linear_count = movement_str.count('l') + ('linear' in movement_str)
        circular_count = movement_str.count('c') + ('circular' in movement_str)
        total_chars = linear_count + circular_count
        
        if total_chars > 0:
            linear_ratio = linear_count / total_chars
            circular_ratio = circular_count / total_chars
        else:
            linear_ratio = 0.0
            circular_ratio = 0.0
        
        # === 2. Length Normalisierung ===
        length = metadata.get('length', 0.0)
        length_norm = np.clip(length / 9000.0, 0, 1)
        
        # === 3. Twist Stats (symmetrisch um 0) ===
        twist_max = 3500.0
        min_twist = metadata.get('min_twist_ist', 0.0)
        max_twist = metadata.get('max_twist_ist', 0.0)
        mean_twist = metadata.get('mean_twist_ist', 0.0)
        median_twist = metadata.get('median_twist_ist', 0.0)
        std_twist = metadata.get('std_twist_ist', 0.0)
        
        min_twist_norm = np.clip((min_twist + twist_max) / (2 * twist_max), 0, 1)
        max_twist_norm = np.clip((max_twist + twist_max) / (2 * twist_max), 0, 1)
        mean_twist_norm = np.clip((mean_twist + twist_max) / (2 * twist_max), 0, 1)
        median_twist_norm = np.clip((median_twist + twist_max) / (2 * twist_max), 0, 1)
        std_twist_norm = np.clip(std_twist / twist_max, 0, 1)
        
        # === 4. Acceleration Stats (symmetrisch um 0) ===
        accel_max = 25000.0
        min_accel = metadata.get('min_acceleration_ist', 0.0)
        max_accel = metadata.get('max_acceleration_ist', 0.0)
        mean_accel = metadata.get('mean_acceleration_ist', 0.0)
        median_accel = metadata.get('median_acceleration_ist', 0.0)
        std_accel = metadata.get('std_acceleration_ist', 0.0)
        
        min_accel_norm = np.clip((min_accel + accel_max) / (2 * accel_max), 0, 1)
        max_accel_norm = np.clip((max_accel + accel_max) / (2 * accel_max), 0, 1)
        mean_accel_norm = np.clip((mean_accel + accel_max) / (2 * accel_max), 0, 1)
        median_accel_norm = np.clip((median_accel + accel_max) / (2 * accel_max), 0, 1)
        std_accel_norm = np.clip(std_accel / accel_max, 0, 1)
        
        # === 5. Zusammensetzen ===
        features = np.array([
            linear_ratio,
            circular_ratio,
            length_norm,
            min_twist_norm,
            max_twist_norm,
            mean_twist_norm,
            median_twist_norm,
            std_twist_norm,
            min_accel_norm,
            max_accel_norm,
            mean_accel_norm,
            median_accel_norm,
            std_accel_norm
        ], dtype=np.float32)
        
        # === 6. L2 Normalisierung ===
        return self._l2_normalize(features)

    # Helper methods
    def _resample(self, trajectory: np.ndarray, n_samples: int) -> np.ndarray:
        """Resample mit Interpolation statt Index-Selection"""
        from scipy.interpolate import interp1d
        
        n_points = len(trajectory)
        if n_points <= n_samples:
            # Padding wenn zu kurz
            pad_length = n_samples - n_points
            return np.pad(trajectory, ((0, pad_length), (0, 0)), mode='edge')
        
        # Interpolation
        x_old = np.linspace(0, 1, n_points)
        x_new = np.linspace(0, 1, n_samples)
        
        interpolator = interp1d(x_old, trajectory, axis=0, kind='linear')
        return interpolator(x_new)

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