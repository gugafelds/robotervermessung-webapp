"""
Work area envelopes for the dashboard: the robot's reach (ABB workspace STL, from the recorder's robots/<robot>/
workspace.stl) intersected with the measured workspace box of motion.robot_info (ws_x/y/z_min/max), so the plot shows
the region the database covers, with closed cut faces. Writes backend/app/utils/robot_models/<robot>_workspace.stl
(ASCII, read by the dashboard's /workarea/robot-mesh). Re-run after changing robot_info's workspace.

Needs trimesh + manifold3d (boolean intersection) and DATABASE_URL (read only).
Usage: python scripts/cut_workspace_envelopes.py [path to robotervermessung-recorder]
"""
import os
import sys
from pathlib import Path

import numpy as np
import psycopg2
import trimesh
from dotenv import load_dotenv

RECORDER = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'robotervermessung-recorder')
OUT = Path(__file__).resolve().parents[1] / 'app' / 'utils' / 'robot_models'

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.set_session(readonly=True)
cur = conn.cursor()
cur.execute('SELECT robot_model, ws_x_min, ws_x_max, ws_y_min, ws_y_max, ws_z_min, ws_z_max FROM motion.robot_info')
for robot, x0, x1, y0, y1, z0, z1 in cur.fetchall():
    src = RECORDER / 'src' / 'trajectory_generation' / 'trajectory_generation' / 'robots' / robot / 'workspace.stl'
    if not src.is_file() or None in (x0, x1, y0, y1, z0, z1):
        print(f'{robot}: no envelope or workspace in robot_info, skipped')
        continue
    reach = trimesh.load(src)
    box = trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]])
    cut = trimesh.boolean.intersection([reach, box], engine='manifold')
    assert cut.is_watertight and np.all(cut.bounds[0] >= [x0 - 1e-3, y0 - 1e-3, z0 - 1e-3])
    text = trimesh.exchange.stl.export_stl_ascii(cut).replace(
        'solid ', f'solid {robot} reach within robot_info workspace ', 1)
    (OUT / f'{robot}_workspace.stl').write_text(text)
    print(f'{robot}: {len(reach.faces)} -> {len(cut.faces)} triangles, '
          f'volume {reach.volume / 1e9:.2f} -> {cut.volume / 1e9:.2f} m³')
