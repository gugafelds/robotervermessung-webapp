# backend/app/utils/metadata_embeddings/external_embedding_builder.py
"""
external_embedding_builder.py
===============================
Builds embeddings for an unsaved, RoboDK-simulated candidate (from the
recorder), using the SAME EmbeddingCalculator methods the real
ingestion pipeline uses — no duplicated math, just different data source.

A payload always represents exactly ONE segment, so this returns a
single embedding row (seg_id == traj_id == EXTERNAL_SEG_ID), analogous
to how a real single-segment trajectory is stored (seg_id == traj_id).
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

from .embedding_calculator import EmbeddingCalculator

logger = logging.getLogger(__name__)

EXTERNAL_SEG_ID = 'externalcandidate'


def _build_metadata_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mirrors the arithmetic in MetadataCalculatorService._calculate_all_metadata_in_memory()
    for a SINGLE segment. If that method's math ever changes, this needs
    to be updated too — kept separate rather than importing it directly
    since that method is written for multi-segment DB trajectories.
    """
    traj = payload['trajectory']
    positions  = np.array(traj['positions'],  dtype=np.float64)
    timestamps = np.array(traj['timestamps'], dtype=np.float64)  # already in seconds

    deltas   = np.diff(positions, axis=0)
    dt       = np.diff(timestamps)
    dt[dt == 0] = 1e-6

    seg_lengths = np.linalg.norm(deltas, axis=1)
    length      = float(np.sum(seg_lengths))
    duration    = float(timestamps[-1] - timestamps[0])

    twist = seg_lengths / dt              # mm/s per step
    accel = np.diff(twist) / dt[1:] if len(twist) > 1 else np.array([0.0])

    centroid = positions.mean(axis=0)

    return {
        'seg_id':       EXTERNAL_SEG_ID,
        'traj_id':      EXTERNAL_SEG_ID,
        'movement_type': payload['movement_type'],
        'duration':      round(duration, 3),
        'weight':        round(float(payload['weight']), 3),
        'length':        round(length, 3),
        'min_vel':       round(float(np.min(twist)), 3)    if len(twist) else 0.0,
        'max_vel':       round(float(np.max(twist)), 3)    if len(twist) else 0.0,
        'mean_vel':      round(float(np.mean(twist)), 3)   if len(twist) else 0.0,
        'median_vel':    round(float(np.median(twist)), 3) if len(twist) else 0.0,
        'std_vel':       round(float(np.std(twist)), 3)    if len(twist) else 0.0,
        'min_accel':     round(float(np.min(accel)), 3)    if len(accel) else 0.0,
        'max_accel':     round(float(np.max(accel)), 3)    if len(accel) else 0.0,
        'mean_accel':    round(float(np.mean(accel)), 3)   if len(accel) else 0.0,
        'median_accel':  round(float(np.median(accel)), 3) if len(accel) else 0.0,
        'std_accel':     round(float(np.std(accel)), 3)    if len(accel) else 0.0,
        'position_x':    round(float(centroid[0]), 3),
        'position_y':    round(float(centroid[1]), 3),
        'position_z':    round(float(centroid[2]), 3),
    }


def build_external_embeddings(
    payload:             Dict[str, Any],
    embedding_calculator: EmbeddingCalculator,
) -> Optional[Dict[str, Any]]:
    """
    Returns a single embedding row (dict) for the external candidate,
    in the same shape as MetadataCalculatorService's embedding_rows entries.
    Returns None if too few points exist for any embedding (< 10, per
    EmbeddingCalculator's own minimum — same rule as real trajectories).
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

    joint_emb = embedding_calculator.compute_joint_embedding(joint_data)       if joint_data else None
    pos_emb   = embedding_calculator.compute_position_embedding(pos_data)     if pos_data   else None
    ori_emb   = embedding_calculator.compute_orientation_embedding(ori_data)  if ori_data   else None
    vel_emb   = embedding_calculator.compute_velocity_embeddings(vel_data)    if vel_data   else None

    metadata_row = _build_metadata_dict(payload)
    print(f"[DEBUG] metadata_row: {metadata_row}")   # NEU

    meta_emb = embedding_calculator.compute_metadata_embedding(metadata_row)

    for name, emb in [('joint', joint_emb), ('position', pos_emb), ('orientation', ori_emb),
                       ('velocity', vel_emb), ('metadata', meta_emb)]:
        if emb is not None and (np.isnan(emb).any() or np.isinf(emb).any()):
            print(f"[DEBUG] {name}_embedding hat NaN/Inf: {emb}")

    if all(e is None for e in [joint_emb, pos_emb, ori_emb, vel_emb, meta_emb]):
        logger.warning("build_external_embeddings: all embeddings failed (likely < 10 points)")
        return None

    return {
        'seg_id':                EXTERNAL_SEG_ID,
        'traj_id':               EXTERNAL_SEG_ID,
        'joint_embedding':        joint_emb,
        'position_embedding':     pos_emb,
        'orientation_embedding':  ori_emb,
        'velocity_embedding':     vel_emb,
        'metadata_embedding':     meta_emb,
        'metadata_row':           metadata_row,   # zusätzlich für match_quality/d_min_per_path_length später nützlich
    }