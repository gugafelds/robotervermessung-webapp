"""Berechnet ED, SIDTW, GD, QDTW aus bereits geparsten CSV-Daten
und schreibt die Ergebnisse in die evaluation.*-Tabellen.

Wird direkt aus batch_processor.py aufgerufen nachdem die Bewegungsdaten
erfolgreich in die DB geschrieben wurden.
"""
import sys
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

# trajectory_evaluation Package aus dem Recorder laden
_EVAL_PATH = os.path.expanduser(
    '~/robotervermessung-recorder/src/trajectory_evaluation'
)
if _EVAL_PATH not in sys.path:
    sys.path.insert(0, _EVAL_PATH)

try:
    from trajectory_evaluation.evaluator import evaluate
    _EVAL_AVAILABLE = True
except ImportError as e:
    logger.warning(f'trajectory_evaluation nicht verfügbar: {e}')
    _EVAL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Hilfsfunktionen: processed_data → numpy arrays
# ---------------------------------------------------------------------------

def _extract_arrays(traj_data: dict):
    """Extrahiert Soll/Ist-Arrays aus dem geparsten CSV-Daten-Dict.

    Returns:
        soll_pos:    [M x 3]  x_cmd, y_cmd, z_cmd
        ist_pos:     [N x 3]  x_act, y_act, z_act
        soll_ori:    [M x 4]  qx_cmd, qy_cmd, qz_cmd, qw_cmd
        ist_ori:     [N x 4]  qx_act, qy_act, qz_act, qw_act
        seg_ids_pos: [M]      seg_id pro Soll-Punkt
        seg_ids_ori: [N]      seg_id pro Ist-Punkt
    """
    pos_cmd = traj_data.get('POSITION_CMD_MAPPING', [])
    ori_cmd = traj_data.get('ORIENTATION_CMD_MAPPING', [])
    transf  = traj_data.get('TRANSFORM_MAPPING', [])

    if not pos_cmd or not transf:
        return None

    # POSITION_CMD: [traj_id, seg_id, timestamp, x_cmd, y_cmd, z_cmd]
    soll_pos    = np.array([[r[3], r[4], r[5]] for r in pos_cmd], dtype=float)
    seg_ids_pos = [r[1] for r in pos_cmd]

    # TRANSFORM_MAPPING: [traj_id, seg_id, timestamp, x_act, y_act, z_act, qx_act, qy_act, qz_act, qw_act]
    ist_pos     = np.array([[r[3], r[4], r[5]]         for r in transf], dtype=float)
    ist_ori     = np.array([[r[6], r[7], r[8], r[9]]   for r in transf], dtype=float)
    seg_ids_ori = [r[1] for r in transf]

    # ORIENTATION_CMD: [traj_id, seg_id, timestamp, qx_cmd, qy_cmd, qz_cmd, qw_cmd]
    if ori_cmd:
        soll_ori = np.array([[r[3], r[4], r[5], r[6]] for r in ori_cmd], dtype=float)
    else:
        soll_ori = None

    return soll_pos, ist_pos, soll_ori, ist_ori, seg_ids_pos, seg_ids_ori


# ---------------------------------------------------------------------------
# DB-Upload Hilfsfunktionen
# ---------------------------------------------------------------------------

async def _insert_info(conn, schema_method: str, traj_id: str, seg_id: str,
                       min_d: float, max_d: float, avg_d: float, std_d: float):
    """Schreibt einen Info-Eintrag (Gesamtbahn oder Segment)."""
    col_prefix = schema_method
    await conn.execute(f"""
        INSERT INTO evaluation.{col_prefix}_info
            (traj_id, seg_id,
             {col_prefix}_min_distance, {col_prefix}_max_distance,
             {col_prefix}_average_distance, {col_prefix}_standard_deviation)
        VALUES ($1,$2,
                ROUND($3::numeric,7), ROUND($4::numeric,7),
                ROUND($5::numeric,7), ROUND($6::numeric,7))
    """, traj_id, seg_id, min_d, max_d, avg_d, std_d)


async def _insert_pos_deviations(conn, method: str, traj_id: str,
                                 distances, soll_aligned, ist_aligned, seg_ids):
    """Schreibt Positions-Abweichungen (ED, SIDTW)."""
    table = f'{method}_evaluation'
    dev_col   = f'{method}_deviation'
    cmd_cols  = f'{method}_cmd_x, {method}_cmd_y, {method}_cmd_z'
    act_cols  = f'{method}_act_x, {method}_act_y, {method}_act_z'

    records = []
    for k in range(len(distances)):
        seg_id = seg_ids[k] if seg_ids and k < len(seg_ids) else traj_id
        records.append((
            traj_id, seg_id,
            float(distances[k]),
            float(soll_aligned[k, 0]), float(soll_aligned[k, 1]), float(soll_aligned[k, 2]),
            float(ist_aligned[k, 0]),  float(ist_aligned[k, 1]),  float(ist_aligned[k, 2]),
            k + 1,
        ))

    await conn.copy_records_to_table(
        table,
        records=records,
        schema_name='evaluation',
        columns=['traj_id', 'seg_id', dev_col,
                 f'{method}_cmd_x', f'{method}_cmd_y', f'{method}_cmd_z',
                 f'{method}_act_x', f'{method}_act_y', f'{method}_act_z',
                 'points_order'],
    )


async def _insert_ori_deviations(conn, method: str, traj_id: str,
                                 distances, soll_aligned, ist_aligned, seg_ids):
    """Schreibt Orientierungs-Abweichungen (GD, QDTW)."""
    table = f'{method}_evaluation'
    dev_col = f'{method}_deviation'

    records = []
    for k in range(len(distances)):
        seg_id = seg_ids[k] if seg_ids and k < len(seg_ids) else traj_id
        records.append((
            traj_id, seg_id,
            float(distances[k]),
            float(soll_aligned[k, 0]), float(soll_aligned[k, 1]),
            float(soll_aligned[k, 2]), float(soll_aligned[k, 3]),
            float(ist_aligned[k, 0]),  float(ist_aligned[k, 1]),
            float(ist_aligned[k, 2]),  float(ist_aligned[k, 3]),
            k + 1,
        ))

    await conn.copy_records_to_table(
        table,
        records=records,
        schema_name='evaluation',
        columns=['traj_id', 'seg_id', dev_col,
                 f'{method}_cmd_x', f'{method}_cmd_y', f'{method}_cmd_z', f'{method}_cmd_w',
                 f'{method}_act_x', f'{method}_act_y', f'{method}_act_z', f'{method}_act_w',
                 'points_order'],
    )


# ---------------------------------------------------------------------------
# Haupt-Einstiegspunkt
# ---------------------------------------------------------------------------

async def evaluate_and_upload(conn, traj_id: str, traj_data: dict):
    """Berechnet alle Metriken für eine Bahn und schreibt sie in die DB.

    Wird aus batch_processor.py aufgerufen.
    """
    if not _EVAL_AVAILABLE:
        logger.warning(f'Evaluation für {traj_id} übersprungen (trajectory_evaluation nicht verfügbar)')
        return

    extracted = _extract_arrays(traj_data)
    if extracted is None:
        logger.warning(f'Keine Positions-/Ist-Daten für {traj_id} — Evaluation übersprungen')
        return

    soll_pos, ist_pos, soll_ori, ist_ori, seg_ids_pos, seg_ids_ori = extracted

    use_ori = soll_ori is not None and len(soll_ori) > 0 and len(ist_ori) > 0

    logger.info(f'Starte Evaluation für {traj_id}: soll={soll_pos.shape}, ist={ist_pos.shape}')

    try:
        results = evaluate(
            soll_pos=soll_pos,
            ist_pos=ist_pos,
            soll_ori=soll_ori if use_ori else np.zeros((1, 4)),
            ist_ori=ist_ori if use_ori else np.zeros((1, 4)),
            segment_ids_pos=seg_ids_pos,
            segment_ids_ori=seg_ids_ori,
            use_ed=True,
            use_sidtw=True,
            use_gd=use_ori,
            use_qdtw=use_ori,
        )
    except Exception as e:
        logger.error(f'Evaluation fehlgeschlagen für {traj_id}: {e}')
        return

    try:
        async with conn.transaction():
            for method, result in results.items():
                d = result.distances
                seg_ids = result.segment_ids  # one entry per distance point

                # Eine Zeile pro Segment
                if seg_ids and len(seg_ids) == len(d):
                    seen = []
                    for sid in seg_ids:
                        if sid not in seen:
                            seen.append(sid)
                    for sid in seen:
                        mask = [i for i, s in enumerate(seg_ids) if s == sid]
                        seg_d = d[mask]
                        await _insert_info(conn, method, traj_id, str(sid),
                                           round(float(np.min(seg_d)), 7),
                                           round(float(np.max(seg_d)), 7),
                                           round(float(np.mean(seg_d)), 7),
                                           round(float(np.std(seg_d)), 7))

                # Gesamtbahn-Zeile (seg_id == traj_id)
                await _insert_info(conn, method, traj_id, traj_id,
                                   round(float(np.min(d)), 7),
                                   round(float(np.max(d)), 7),
                                   round(float(np.mean(d)), 7),
                                   round(float(np.std(d)), 7))

                # Abweichungen pro Punkt
                if method in ('ed', 'sidtw'):
                    await _insert_pos_deviations(
                        conn, method, traj_id,
                        d, result.soll_aligned, result.ist_aligned,
                        seg_ids,
                    )
                else:
                    await _insert_ori_deviations(
                        conn, method, traj_id,
                        d, result.soll_aligned, result.ist_aligned,
                        seg_ids,
                    )

        logger.info(f'✓ Evaluation hochgeladen für {traj_id}: '
                    f'ED avg={results["ed"].avg_distance:.3f} '
                    f'SIDTW avg={results["sidtw"].avg_distance:.3f}'
                    + (f' GD avg={results["gd"].avg_distance:.3f}'
                       f' QDTW avg={results["qdtw"].avg_distance:.3f}' if use_ori else ''))

    except Exception as e:
        logger.error(f'DB-Upload Evaluation fehlgeschlagen für {traj_id}: {e}')
