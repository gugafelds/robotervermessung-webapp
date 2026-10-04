# backend/scripts/calculators/embedding_calculator.py

import json
import numpy as np
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Metadata embedding: z-scale (mean/std) and weights (sqrt of ExtraTrees importances for the SIDTW) fitted on
# the measured DB by backend/scripts/update_metadata_embeddings.py, separately for segments and whole
# trajectories -- no robot constants. Stored vectors depend on this file: refit and recompute together.
METADATA_SCALE_PATH = Path(__file__).with_name('metadata_scale.json')
METADATA_FEATURES = ['circular', 'max_vel', 'mean_vel', 'std_vel', 'duration', 'length', 'weight',
                     'position_x', 'position_y', 'position_z']


@lru_cache(maxsize=1)
def _metadata_scale() -> Dict[str, Dict[str, np.ndarray]]:
    raw = json.loads(METADATA_SCALE_PATH.read_text())
    assert raw['features'] == METADATA_FEATURES, f'{METADATA_SCALE_PATH} was fitted for other features'
    return {level: {k: np.asarray(raw[level][k]) for k in ('mean', 'std', 'weight')} for level in ('segment', 'trajectory')}


def metadata_features(metadata: Dict) -> np.ndarray:
    """Raw METADATA_FEATURES of one motion.traj_metadata-shaped row; circular = share of circular segments."""
    movement = (metadata.get('movement_type') or '').lower().strip()
    if movement in ('linear', 'circular'):
        circular = float(movement == 'circular')
    else:  # 'l' / 'c' / per-segment string like 'llc'
        n = movement.count('l') + movement.count('c')
        circular = movement.count('c') / n if n else 0.0
    return np.array([circular] + [float(metadata.get(f) or 0.0) for f in METADATA_FEATURES[1:]])


class EmbeddingCalculator:
    """
    Universal Embedding Calculator
    Berechnet Joint, Position, Orientation, Velocity und Metadata Embeddings
    """

    def __init__(
            self,
            n_samples: int = 10,
            robot_info: Optional[Dict] = None  # unused since the metadata embedding is z-scored (metadata_scale.json)
    ):
        self.n_samples = n_samples

    def compute_joint_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Joint Angles extrahieren
        traj = np.array([
            [r['joint_1'], r['joint_2'], r['joint_3'],
             r['joint_4'], r['joint_5'], r['joint_6']]
            for r in data
        ], dtype=np.float32)

        resampled = self._resample(traj, self.n_samples)
        flat = resampled.flatten()

        return self._l2_normalize(flat)

    def compute_position_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Position extrahieren
        traj = np.array([[r['x_cmd'], r['y_cmd'], r['z_cmd']]
                         for r in data], dtype=np.float32)

        # Normalisierung zu Startpunkt
        traj_normalized = traj - traj[0]

        # max_extent Normalisierung
        norms = np.linalg.norm(traj_normalized, axis=1)
        max_extent = np.max(norms)
        if max_extent > 1e-6:
            traj_normalized = traj_normalized / max_extent

        resampled = self._resample(traj, self.n_samples)
        flat = resampled.flatten()

        return self._l2_normalize(flat)

    def compute_orientation_embedding(self, data: List[Dict]) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Quaternions extrahieren [qx, qy, qz, qw] für scipy
        quats = np.array([
            [r['qx_cmd'], r['qy_cmd'], r['qz_cmd'], r['qw_cmd']]
            for r in data
        ], dtype=np.float32)

        # Zu Rotation Vectors konvertieren (3D)
        from scipy.spatial.transform import Rotation
        rot_vectors = Rotation.from_quat(quats).as_rotvec()

        # Relativ zum Start normalisieren
        rot_vectors_normalized = rot_vectors - rot_vectors[0]

        resampled = self._resample(rot_vectors_normalized, self.n_samples)
        flat = resampled.flatten()

        return self._l2_normalize(flat)

    def compute_velocity_embeddings(
            self,
            data: List[Dict]
    ) -> Optional[np.ndarray]:
        if len(data) < 10:
            return None

        # Position extrahieren
        positions = np.array([
            [r['x_cmd'], r['y_cmd'], r['z_cmd']]
            for r in data
        ], dtype=np.float32)

        # Künstliche Zeitstempel (gleichmäßig 0 bis 1, wie MATLAB)
        n_points = len(positions)
        timestamps = np.linspace(0, 1, n_points)

        # Savitzky-Golay Filter für Position
        from scipy.signal import savgol_filter

        window_length = min(33, n_points if n_points % 2 == 1 else n_points - 1)
        window_length = max(window_length, 3)

        positions_smooth = np.zeros_like(positions)
        for dim in range(3):
            positions_smooth[:, dim] = savgol_filter(
                positions[:, dim],
                window_length=window_length,
                polyorder=3
            )

        # Velocity aus geglätteter Position
        delta_pos = np.diff(positions_smooth, axis=0)
        delta_time = np.diff(timestamps)
        delta_time = np.where(delta_time == 0, 1e-9, delta_time)
        velocity = delta_pos / delta_time[:, np.newaxis]

        # Velocity nochmal glätten
        n = len(velocity)
        vel_window = min(33, n if n % 2 == 1 else n - 1)
        vel_window = max(vel_window, 3)

        velocity_smooth = np.zeros_like(velocity)
        for dim in range(3):
            velocity_smooth[:, dim] = savgol_filter(
                velocity[:, dim],
                window_length=vel_window,
                polyorder=2
            )

        resampled = self._resample(velocity_smooth, self.n_samples)
        flat = resampled.flatten()

        return self._l2_normalize(flat)

    def compute_metadata_embedding(self, metadata: Dict) -> Optional[np.ndarray]:
        """10-D (METADATA_FEATURES), z-scored and weighted with metadata_scale.json -- whole-trajectory rows
        (seg_id == traj_id) with the trajectory scale. No accelerations: for simulated candidates they disagree
        with the stored values (r 0.2-0.6), and they carry no information beyond the velocities."""
        level = 'trajectory' if metadata.get('seg_id') == metadata.get('traj_id') else 'segment'
        s = _metadata_scale()[level]
        z = (metadata_features(metadata) - s['mean']) / s['std'] * s['weight']
        return self._l2_normalize(z.astype(np.float32))


    # Helper methods
    @staticmethod
    def _resample(trajectory: np.ndarray, n_samples: int) -> np.ndarray:
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

    @staticmethod
    def _l2_normalize(vec: np.ndarray) -> np.ndarray:
        """
        L2 normalization

        Args:
            vec: input vector
        Returns:
            normalized vector
        """
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    

# ── Candidate (unsaved) embeddings ───────────────────────────────────────

CANDIDATE_SEG_ID = 'externalcandidate'

def _build_candidate_metadata(payload: Dict[str, Any], seg_id: str = CANDIDATE_SEG_ID) -> Dict[str, Any]:
    """
    Computes metadata features for an unsaved, simulated candidate segment.

    Mirrors MetadataCalculatorService._calculate_all_metadata_in_memory()
    for a single segment. If that method's arithmetic ever changes, this
    needs updating too — kept separate because that method is written for
    multi-segment DB trajectories, not single-payload candidates.
    """
    traj       = payload['trajectory']
    positions  = np.array(traj['positions'],  dtype=np.float64)
    timestamps = np.array(traj['timestamps'], dtype=np.float64)

    deltas      = np.diff(positions, axis=0)
    dt          = np.diff(timestamps)
    dt[dt == 0] = 1e-6

    seg_lengths = np.linalg.norm(deltas, axis=1)
    length      = float(np.sum(seg_lengths))
    duration    = float(timestamps[-1] - timestamps[0])

    twist = seg_lengths / dt
    accel = np.diff(twist) / dt[1:] if len(twist) > 1 else np.array([0.0])
    centroid = positions.mean(axis=0)

    return {
        'seg_id':        seg_id,
        'traj_id':       CANDIDATE_SEG_ID,
        'movement_type': payload['movement_type'],
        'duration':      round(duration, 3),
        'weight':        round(float(payload['weight']), 3),
        'length':        round(length, 3),
        'min_vel':       round(float(np.min(twist)),    3) if len(twist) else 0.0,
        'max_vel':       round(float(np.max(twist)),    3) if len(twist) else 0.0,
        'mean_vel':      round(float(np.mean(twist)),   3) if len(twist) else 0.0,
        'median_vel':    round(float(np.median(twist)), 3) if len(twist) else 0.0,
        'std_vel':       round(float(np.std(twist)),    3) if len(twist) else 0.0,
        'min_accel':     round(float(np.min(accel)),    3) if len(accel) else 0.0,
        'max_accel':     round(float(np.max(accel)),    3) if len(accel) else 0.0,
        'mean_accel':    round(float(np.mean(accel)),   3) if len(accel) else 0.0,
        'median_accel':  round(float(np.median(accel)), 3) if len(accel) else 0.0,
        'std_accel':     round(float(np.std(accel)),    3) if len(accel) else 0.0,
        'position_x':    round(float(centroid[0]), 3),
        'position_y':    round(float(centroid[1]), 3),
        'position_z':    round(float(centroid[2]), 3),
    }


def build_candidate_embeddings(
    payload:              Dict[str, Any],
    embedding_calculator: 'EmbeddingCalculator',
    seg_id:               str = CANDIDATE_SEG_ID,  # NEU
) -> Optional[Dict[str, Any]]:
    """
    Builds all embeddings for an unsaved, simulated candidate segment.

    Uses the same EmbeddingCalculator methods as the real ingestion
    pipeline — no duplicated math, just a different data source
    (in-memory payload instead of DB rows).

    Returns a single embedding row (dict) in the same shape as
    MetadataCalculatorService's embedding_rows entries, or None if
    too few points exist (< 10, matching EmbeddingCalculator's minimum).
    """
    traj = payload['trajectory']

    pos_data = [
        {'x_cmd': p[0], 'y_cmd': p[1], 'z_cmd': p[2]}
        for p in traj['positions']
    ]
    joint_data = [
        {f'joint_{i+1}': j[i] for i in range(6)}
        for j in traj.get('joints', [])
    ]
    ori_data = [
        {'qw_cmd': q[0], 'qx_cmd': q[1], 'qy_cmd': q[2], 'qz_cmd': q[3]}
        for q in traj.get('quats', [])
    ]
    vel_data = [
        {'x_cmd': p[0], 'y_cmd': p[1], 'z_cmd': p[2], 'timestamp': t}
        for p, t in zip(traj['positions'], traj['timestamps'])
    ]

    joint_emb = embedding_calculator.compute_joint_embedding(joint_data)      if joint_data  else None
    pos_emb   = embedding_calculator.compute_position_embedding(pos_data)     if pos_data    else None
    ori_emb   = embedding_calculator.compute_orientation_embedding(ori_data)  if ori_data    else None
    vel_emb   = embedding_calculator.compute_velocity_embeddings(vel_data)    if vel_data    else None

    metadata_row = _build_candidate_metadata(payload, seg_id=seg_id)
    logger.debug(f"[build_candidate_embeddings] seg_id={seg_id} metadata_row: {metadata_row}")

    meta_emb = embedding_calculator.compute_metadata_embedding(metadata_row)

    if all(e is None for e in [joint_emb, pos_emb, ori_emb, vel_emb, meta_emb]):
        logger.warning("build_candidate_embeddings: all embeddings None (< 10 points?) — seg_id=%s", seg_id)
        return None

    return {
        'seg_id':               seg_id,
        'traj_id':              CANDIDATE_SEG_ID,
        'joint_embedding':       joint_emb,
        'position_embedding':    pos_emb,
        'orientation_embedding': ori_emb,
        'velocity_embedding':    vel_emb,
        'metadata_embedding':    meta_emb,
        'metadata_row':          metadata_row,
    }


def build_candidate_embeddings_segmented(
    payload:              Dict[str, Any],
    embedding_calculator: 'EmbeddingCalculator',
    segment_indices:      list[int],
) -> Optional[list[Dict[str, Any]]]:
    """
    Builds one embedding row per segment, plus one for the full trajectory.

    segment_indices = [end_idx_seg0, end_idx_seg1, ...] aus
    analytical_simulator.segment_indices (ohne Home-Segment, also [1:]).

    Gibt zurück:
      rows[0]    = Gesamttrajektorie  (seg_id == traj_id == CANDIDATE_SEG_ID)
      rows[1..n] = ein Row pro Segment (seg_id = CANDIDATE_SEG_ID_0, _1, ...)
    """
    traj       = payload['trajectory']
    positions  = traj['positions']
    timestamps = traj['timestamps']
    quats      = traj.get('quats', [])
    joints     = traj.get('joints', [])

    # ── Gesamttrajektorie ─────────────────────────────────────────────────
    full_row = build_candidate_embeddings(payload, embedding_calculator, seg_id=CANDIDATE_SEG_ID)
    if full_row is None:
        logger.warning("build_candidate_embeddings_segmented: full trajectory embedding failed.")
        return None

    rows = [full_row]

    # Optional pro Segment 'linear'/'circular' (wie motion.traj_metadata je
    # Segment) — ohne das bekäme jedes Segment den Gesamt-String (z. B. 'llc').
    seg_types = payload.get('segment_movement_types') or []

    # ── Pro Segment ───────────────────────────────────────────────────────
    boundaries = [0] + segment_indices
    for i in range(len(segment_indices)):
        start  = boundaries[i]
        end    = boundaries[i + 1] + 1
        seg_id = f"{CANDIDATE_SEG_ID}_{i}"

        seg_payload = {
            "trajectory": {
                "timestamps": timestamps[start:end],
                "positions":  positions[start:end],
                "quats":      quats[start:end],
                "joints":     joints[start:end],
            },
            "movement_type": seg_types[i] if i < len(seg_types) else payload['movement_type'],
            "weight":        payload['weight'],
        }

        row = build_candidate_embeddings(seg_payload, embedding_calculator, seg_id=seg_id)
        if row is None:
            logger.warning(
                "build_candidate_embeddings_segmented: segment %d failed (too few points?) — skipping.", i
            )
            continue

        rows.append(row)

    if len(rows) == 1:
        # Nur Gesamttrajektorie, keine Segmente — sinnlos
        logger.warning("build_candidate_embeddings_segmented: no segment rows built.")
        return None

    logger.info("[segmented] total rows built: %d (1 full + %d segments)", len(rows), len(rows) - 1)

    return rows