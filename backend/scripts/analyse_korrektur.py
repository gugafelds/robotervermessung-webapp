"""
analyse_korrektur.py
====================
Vergleicht Control- und Korrektur-Bahnen anhand eines Tags.

Verwendung:
    python analyse_korrektur.py --tag ba-mueller-correction-2
    python analyse_korrektur.py --tag mein-tag --last-points 5
    python analyse_korrektur.py --tag mein-tag --ref cmd-mean
"""

import argparse
import asyncio
import math
import os

import asyncpg
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

PAIR_THRESHOLD_MM = 1.0  # Euklidischer Abstand zweier Zielpunkte für Paar-Erkennung


# ── Hilfsfunktionen ────────────────────────────────────────────────────────

def is_control_point(x, y, z) -> bool:
    """Sollwert ohne Korrektur: alle Koordinaten enden auf .0 oder .5"""
    def rounded(v):
        return abs(float(v) - round(float(v) * 2) / 2) < 0.01
    return rounded(x) and rounded(y) and rounded(z)


def euclidean(ax, ay, az, rx, ry, rz) -> float:
    return math.sqrt(
        (float(ax) - float(rx)) ** 2 +
        (float(ay) - float(ry)) ** 2 +
        (float(az) - float(rz)) ** 2
    )


def dtw_distance(seq_a: list, seq_b: list) -> float:
    """DTW zwischen zwei 3D-Punktsequenzen. n=10 -> O(100), kein Framework nötig."""
    n, m = len(seq_a), len(seq_b)
    cost = [[math.inf] * m for _ in range(n)]
    cost[0][0] = euclidean(*seq_a[0], *seq_b[0])
    for i in range(1, n):
        cost[i][0] = cost[i-1][0] + euclidean(*seq_a[i], *seq_b[0])
    for j in range(1, m):
        cost[0][j] = cost[0][j-1] + euclidean(*seq_a[0], *seq_b[j])
    for i in range(1, n):
        for j in range(1, m):
            cost[i][j] = euclidean(*seq_a[i], *seq_b[j]) + min(
                cost[i-1][j], cost[i][j-1], cost[i-1][j-1]
            )
    return cost[n-1][m-1]


def seg_order(seg_id: str) -> int:
    try:
        return int(seg_id.rsplit("_", 1)[-1])
    except ValueError:
        return 0


# ── Datenbankabfragen ───────────────────────────────────────────────────────

async def fetch_setpoints(conn, tag: str) -> pd.DataFrame:
    rows = await conn.fetch("""
        SELECT s.traj_id, s.seg_id, s.x_reached, s.y_reached, s.z_reached
        FROM motion.traj_setpoints s
        INNER JOIN motion.traj_info i ON i.traj_id = s.traj_id
        WHERE i.tag = $1
    """, tag)
    return pd.DataFrame(rows, columns=["traj_id", "seg_id", "x_reached", "y_reached", "z_reached"])


async def fetch_actual_points(conn, seg_ids: list, last_points: int) -> pd.DataFrame:
    rows = await conn.fetch("""
        SELECT seg_id, sidtw_act_x AS x_act, sidtw_act_y AS y_act, sidtw_act_z AS z_act
        FROM (
            SELECT seg_id, sidtw_act_x, sidtw_act_y, sidtw_act_z,
                   ROW_NUMBER() OVER (
                       PARTITION BY seg_id ORDER BY points_order DESC
                   ) AS rn
            FROM evaluation.sidtw_evaluation
            WHERE seg_id = ANY($1::text[])
        ) t
        WHERE rn <= $2
    """, seg_ids, last_points)
    return pd.DataFrame(rows, columns=["seg_id", "x_act", "y_act", "z_act"])


async def fetch_cmd_mean(conn, seg_ids: list, last_points: int) -> pd.DataFrame:
    """Mittelwert der letzten N CMD-Punkte des Control-Segments als Referenz."""
    rows = await conn.fetch("""
        SELECT seg_id,
               AVG(sidtw_cmd_x) AS x_ref,
               AVG(sidtw_cmd_y) AS y_ref,
               AVG(sidtw_cmd_z) AS z_ref
        FROM (
            SELECT seg_id, sidtw_cmd_x, sidtw_cmd_y, sidtw_cmd_z,
                   ROW_NUMBER() OVER (
                       PARTITION BY seg_id ORDER BY points_order DESC
                   ) AS rn
            FROM evaluation.sidtw_evaluation
            WHERE seg_id = ANY($1::text[])
        ) t
        WHERE rn <= $2
        GROUP BY seg_id
    """, seg_ids, last_points)
    return pd.DataFrame(rows, columns=["seg_id", "x_ref", "y_ref", "z_ref"])


async def fetch_ctrl_cmd_sequences(conn, seg_ids: list, last_points: int) -> dict:
    """Letzte N CMD-Punkte der Control-Segmente als Sequenz — Referenz für sidtw-Modus."""
    rows = await conn.fetch("""
        SELECT seg_id, sidtw_cmd_x AS x, sidtw_cmd_y AS y, sidtw_cmd_z AS z
        FROM (
            SELECT seg_id, sidtw_cmd_x, sidtw_cmd_y, sidtw_cmd_z,
                   ROW_NUMBER() OVER (
                       PARTITION BY seg_id ORDER BY points_order DESC
                   ) AS rn
            FROM evaluation.sidtw_evaluation
            WHERE seg_id = ANY($1::text[])
        ) t
        WHERE rn <= $2
        ORDER BY seg_id, rn DESC
    """, seg_ids, last_points)
    result = {}
    for r in rows:
        result.setdefault(r["seg_id"], []).append(
            (float(r["x"]), float(r["y"]), float(r["z"]))
        )
    return result


async def fetch_movement_types(conn, seg_ids: list) -> dict:
    rows = await conn.fetch("""
        SELECT seg_id, movement_type FROM motion.traj_metadata
        WHERE seg_id = ANY($1::text[])
    """, seg_ids)
    return {r["seg_id"]: r["movement_type"] for r in rows}


# ── Kernlogik ───────────────────────────────────────────────────────────────

def build_pairs(setpoints: pd.DataFrame):
    """
    Flow:
    1. Alle Bahnen (traj_id) nach Segment-Nummer sortieren
    2. Bahnen nach traj_id (= Zeitstempel) aufsteigend sortieren
    3. Aufeinanderfolgende Bahnen vergleichen: gleiche Anzahl Segmente + Zielpunkte < PAIR_THRESHOLD_MM
    4. Erste Bahn = Control (nicht korrigiert), zweite = Correction
    5. Segmente positional zuordnen (Position 1 <-> Position 1, usw.)
    """
    # Segmente pro Bahn sortieren, Bahnen nach traj_id (Zeitstempel) sortieren
    trajs = {}
    for traj_id, group in setpoints.groupby("traj_id"):
        trajs[traj_id] = group.sort_values(
            "seg_id", key=lambda s: s.map(seg_order)
        ).reset_index(drop=True)

    traj_ids = sorted(trajs.keys())  # aufsteigend = Aufnahmereihenfolge
    pairs = []
    unmatched = []
    i = 0

    while i < len(traj_ids) - 1:
        tid_a = traj_ids[i]
        tid_b = traj_ids[i + 1]
        df_a = trajs[tid_a]
        df_b = trajs[tid_b]

        if len(df_a) == len(df_b) and all(
            euclidean(
                ra.x_reached, ra.y_reached, ra.z_reached,
                rb.x_reached, rb.y_reached, rb.z_reached
            ) < PAIR_THRESHOLD_MM
            for ra, rb in zip(df_a.itertuples(), df_b.itertuples())
        ):
            # tid_a = Control (zuerst aufgenommen), tid_b = Correction
            for pos, (ctrl_row, corr_row) in enumerate(
                zip(df_a.itertuples(), df_b.itertuples()), start=1
            ):
                pairs.append({
                    "ctrl_seg": ctrl_row.seg_id,
                    "corr_seg": corr_row.seg_id,
                    "x_ref":    float(ctrl_row.x_reached),
                    "y_ref":    float(ctrl_row.y_reached),
                    "z_ref":    float(ctrl_row.z_reached),
                    "seg_pos":  pos,
                })
            i += 2  # beide verbraucht, weiter zum nächsten Paar
        else:
            unmatched.append(traj_ids[i])
            i += 1  # diese Bahn hat kein Paar, überspringen

    return pairs, unmatched


def compute_errors(pairs, actual: pd.DataFrame,
                   cmd_ref: pd.DataFrame = None,
                   sidtw_dev: pd.DataFrame = None) -> pd.DataFrame:
    """
    Fehler pro Segment, Referenz immer vom Control-Segment:
    - setpoint:  x_reached aus traj_setpoints (single point)
    - cmd-mean:  Mittelwert der letzten N CMD-Punkte des Control-Segments
    - sidtw:     Mittelwert der sidtw_deviation der letzten N Punkte (direkt aus DB)
    """
    act_by_seg = actual.groupby("seg_id")
    cmd_by_seg = cmd_ref.set_index("seg_id") if cmd_ref is not None else None
    records = []

    for p in pairs:
        ctrl_seg = p["ctrl_seg"]

        for mode, seg_id in [("control", ctrl_seg), ("correction", p["corr_seg"])]:
            if sidtw_dev is not None:
                # sidtw-Modus: act des Segments gegen CMD-Sequenz des Control-Segments
                ctrl_cmd_seq = sidtw_dev.get(ctrl_seg, [])
                if not ctrl_cmd_seq or seg_id not in act_by_seg.groups:
                    continue
                pts = act_by_seg.get_group(seg_id)
                act_seq = [(float(r.x_act), float(r.y_act), float(r.z_act)) for r in pts.itertuples()]
                # Mittlerer Abstand jedes Ist-Punktes zum nächsten CMD-Punkt des Control-Segments
                errors = [min(euclidean(ax, ay, az, cx, cy, cz) for cx, cy, cz in ctrl_cmd_seq)
                          for ax, ay, az in act_seq]
                error_val = np.mean(errors)
                rx = np.mean([c[0] for c in ctrl_cmd_seq])
                ry = np.mean([c[1] for c in ctrl_cmd_seq])
                rz = np.mean([c[2] for c in ctrl_cmd_seq])
                dx = np.mean([x - rx for x, y, z in act_seq])
                dy = np.mean([y - ry for x, y, z in act_seq])
                dz = np.mean([z - rz for x, y, z in act_seq])
            else:
                if seg_id not in act_by_seg.groups:
                    continue
                pts = act_by_seg.get_group(seg_id)
                act_seq = [(float(r.x_act), float(r.y_act), float(r.z_act)) for r in pts.itertuples()]

                if cmd_by_seg is not None and ctrl_seg in cmd_by_seg.index:
                    ref = cmd_by_seg.loc[ctrl_seg]
                    rx, ry, rz = float(ref["x_ref"]), float(ref["y_ref"]), float(ref["z_ref"])
                else:
                    rx, ry, rz = float(p["x_ref"]), float(p["y_ref"]), float(p["z_ref"])

                error_val = np.mean([euclidean(x, y, z, rx, ry, rz) for x, y, z in act_seq])
                dx = np.mean([x - rx for x, y, z in act_seq])
                dy = np.mean([y - ry for x, y, z in act_seq])
                dz = np.mean([z - rz for x, y, z in act_seq])

            records.append({
                "seg_id":   seg_id,
                "mode":     mode,
                "error":    error_val,
                "dx":       dx,
                "dy":       dy,
                "dz":       dz,
                "ctrl_seg": ctrl_seg,
                "seg_pos":  p["seg_pos"],
            })

    return pd.DataFrame(records)


def print_stats(errors_df: pd.DataFrame, movement_types: dict, label: str):
    def stats(arr):
        return {
            "mean":   np.mean(arr),
            "median": np.median(arr),
            "std":    np.std(arr, ddof=1),
            "min":    np.min(arr),
            "max":    np.max(arr),
            "mse":    np.mean(np.square(arr)),
        }

    def improvement(ctrl, corr):
        return (ctrl - corr) / ctrl if ctrl != 0 else float("nan")

    if movement_types:
        errors_df = errors_df.copy()
        errors_df["movement"] = errors_df["seg_id"].map(movement_types)

    subsets = {"alle": errors_df}
    for mtype in ["linear", "circular"]:
        subset = errors_df[errors_df.get("movement", pd.Series(dtype=str)) == mtype]
        if not subset.empty:
            subsets[mtype] = subset

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    for subset_name, subset in subsets.items():
        ctrl_errors = subset[subset["mode"] == "control"]["error"].values
        corr_errors = subset[subset["mode"] == "correction"]["error"].values
        if len(ctrl_errors) == 0 or len(corr_errors) == 0:
            continue

        s_ctrl = stats(ctrl_errors)
        s_corr = stats(corr_errors)

        rows = []
        for metric in ["mean", "median", "std", "min", "max", "mse"]:
            rows.append({
                "Metrik":          metric,
                "Control [mm]":    round(s_ctrl[metric], 4),
                "Korrektur [mm]":  round(s_corr[metric], 4),
                "Verbesserung":    f"{improvement(s_ctrl[metric], s_corr[metric]):.1%}",
            })

        print(f"\n--- Bewegungstyp: {subset_name} ({len(ctrl_errors)} Segmente) ---")
        print(pd.DataFrame(rows).to_string(index=False))


def print_factors(errors_df: pd.DataFrame):
    """
    Empfohlene Korrekturfaktoren aus den Vektor-Residuen.

    Idee:
    - residuum_ctrl  = mittlere Abweichung (act - ref) der Control-Bahn pro Achse
    - residuum_corr  = mittlere Abweichung (act - ref) der Korrektur-Bahn pro Achse
    - Die Korrektur hat residuum_ctrl - residuum_corr bereits wegkorrigiert.
    - Wenn residuum_corr noch != 0, dann war die Korrektur zu schwach (>1) oder zu stark (<1).
    - Faktor = residuum_ctrl / residuum_corr  (wie viel stärker müsste man korrigieren)
    - Vorzeichen-Wechsel → Überkompensation, Faktor wird auf 0.0 gesetzt mit Warnung.
    """
    ctrl = errors_df[errors_df["mode"] == "control"]
    corr = errors_df[errors_df["mode"] == "correction"]

    print(f"\n{'='*60}")
    print("  Empfohlene Korrekturfaktoren")
    print(f"{'='*60}")

    for axis in ["x", "y", "z"]:
        mean_ctrl = ctrl[f"d{axis}"].mean()
        mean_corr = corr[f"d{axis}"].mean()

        if abs(mean_ctrl) < 1e-6:
            factor = 1.0
            note = "(kein Fehler in Control)"
        elif mean_ctrl * mean_corr < 0:
            factor = 0.0
            note = "⚠ Überkompensation — Korrektur dreht Vorzeichen um"
        elif abs(mean_corr) < 1e-6:
            factor = 1.0
            note = "(perfekt korrigiert)"
        else:
            factor = round(mean_ctrl / mean_corr, 4)
            note = ""

        print(f"  CORRECTION_{axis.upper()}_FAC = {factor:.4f}  "
              f"[ctrl={mean_ctrl:+.3f} mm, corr={mean_corr:+.3f} mm]  {note}")

    print()


# ── Main ────────────────────────────────────────────────────────────────────

async def pairs_from_traj_ids(conn, ctrl_traj_id: str, corr_traj_id: str) -> list:
    """Pairt Segmente zweier explizit angegebener Bahnen positional nach Segment-Nummer."""
    rows = await conn.fetch("""
        SELECT traj_id, seg_id, x_reached, y_reached, z_reached
        FROM motion.traj_setpoints
        WHERE traj_id = ANY($1::text[])
    """, [ctrl_traj_id, corr_traj_id])

    df = pd.DataFrame(rows, columns=["traj_id", "seg_id", "x_reached", "y_reached", "z_reached"])
    ctrl_df = df[df["traj_id"] == ctrl_traj_id].sort_values(
        "seg_id", key=lambda s: s.map(seg_order)
    ).reset_index(drop=True)
    corr_df = df[df["traj_id"] == corr_traj_id].sort_values(
        "seg_id", key=lambda s: s.map(seg_order)
    ).reset_index(drop=True)

    pairs = []
    for pos, (cr, co) in enumerate(zip(ctrl_df.itertuples(), corr_df.itertuples()), start=1):
        pairs.append({
            "ctrl_seg": cr.seg_id,
            "corr_seg": co.seg_id,
            "x_ref":    float(cr.x_reached),
            "y_ref":    float(cr.y_reached),
            "z_ref":    float(cr.z_reached),
            "seg_pos":  pos,
        })
    return pairs


async def main(tag: str, last_points: int, ref_mode: str,
               ctrl_traj: str = None, corr_traj: str = None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print(f"\nletzte {last_points} Punkte | Referenz: {ref_mode}")

        if ctrl_traj and corr_traj:
            print(f"Manuelles Pairing: ctrl={ctrl_traj} | corr={corr_traj}")
            pairs = await pairs_from_traj_ids(conn, ctrl_traj, corr_traj)
            label = f"ctrl={ctrl_traj} vs corr={corr_traj}"
        else:
            print(f"Tag: '{tag}'")
            setpoints = await fetch_setpoints(conn, tag)
            if setpoints.empty:
                print(f"Keine Setpoints für Tag '{tag}' gefunden.")
                return
            print(f"Bahnen im Datensatz: {setpoints['traj_id'].nunique()}")
            pairs, unmatched = build_pairs(setpoints)
            print(f"Segment-Paare gefunden: {len(pairs)} | Bahnen ohne Paar: {len(unmatched)}")
            print("\n--- Debug: erste 5 Paare ---")
            for p in pairs[:5]:
                print(f"  ctrl={p['ctrl_seg']}  corr={p['corr_seg']}  "
                      f"ref=({p['x_ref']:.1f}, {p['y_ref']:.1f}, {p['z_ref']:.1f})  seg_pos={p['seg_pos']}")
            if unmatched:
                print("\n--- Bahnen ohne Paar ---")
                for tid in unmatched:
                    print(f"  {tid}")
            label = f"Tag: {tag}"

        if not pairs:
            print("Keine Paare — Abbruch.")
            return

        ctrl_segs = [p["ctrl_seg"] for p in pairs]
        corr_segs = [p["corr_seg"] for p in pairs]
        all_seg_ids = ctrl_segs + corr_segs

        actual = await fetch_actual_points(conn, all_seg_ids, last_points)
        movement_types = await fetch_movement_types(conn, all_seg_ids)

        cmd_ref = None
        sidtw_dev = None
        if ref_mode == "cmd-mean":
            cmd_ref = await fetch_cmd_mean(conn, ctrl_segs, last_points)
        elif ref_mode == "sidtw":
            sidtw_dev = await fetch_ctrl_cmd_sequences(conn, ctrl_segs, last_points)

        errors_df = compute_errors(pairs, actual, cmd_ref, sidtw_dev)
        print_stats(errors_df, movement_types, label)
        print_factors(errors_df)

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Korrektur-Auswertung pro Tag")
    parser.add_argument("--tag", help="Tag aus traj_info (automatisches Pairing)")
    parser.add_argument("--ctrl", help="traj_id der Control-Bahn (manuelles Pairing)")
    parser.add_argument("--corr", help="traj_id der Korrektur-Bahn (manuelles Pairing)")
    parser.add_argument("--last-points", type=int, default=10,
                        help="Anzahl der letzten Punkte für Positioniergenauigkeit (default: 10)")
    parser.add_argument("--ref", choices=["setpoint", "cmd-mean", "sidtw"], default="setpoint",
                        help="Referenz: 'setpoint' = x_reached der Control-Bahn (default), "
                             "'cmd-mean' = Mittelwert der letzten N CMD-Punkte des Control-Segments, "
                             "'sidtw' = Mittelwert der sidtw_deviation der letzten N Punkte")
    args = parser.parse_args()

    if not args.tag and not (args.ctrl and args.corr):
        parser.error("Entweder --tag oder --ctrl + --corr angeben.")

    asyncio.run(main(args.tag, args.last_points, args.ref, args.ctrl, args.corr))
