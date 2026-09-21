"""
fix_soll_values.py
===================
Korrigiert Kommunikationsfehler in Soll-Position, -Orientierung und
-Gelenkwerten: der Socket liefert für ein oder mehrere Samples exakt 0.0
statt des echten Werts -- bei Gelenkwerten oft 2, 3 oder alle 6 Spalten
gleichzeitig, bei der Orientierung eine oder mehrere Quaternion-Komponenten.
Echte, kontinuierliche Soll-Werte landen praktisch nie durch Zufall exakt
auf 0.0, daher reicht eine exakte Gleichheitsprüfung pro Spalte -- keine
Fenster-Statistik/Schwellwerte nötig.

Ohne --update: reine Vorschau, schreibt NICHTS in die DB (Report + optional
Plot). Mit --update: iteriert die gefundenen Bahnen einzeln, zeigt pro Bahn
die Korrekturen und fragt vor jedem Schreiben nach (Enter = übernehmen,
s + Enter = überspringen) -- wie der manuelle Ablauf im MATLAB-Skript
correct_spikes_orientation.m, nur für alle 3 Soll-Tabellen zusammen.

Verwendung:
    python fix_soll_values.py --traj-id 1765989370
    python fix_soll_values.py --traj-id 1765989370 --plot
    python fix_soll_values.py --date 20260724_15
    python fix_soll_values.py --date 20260724_15 --update
    python fix_soll_values.py --selftest
"""

import argparse
import asyncio
import os
import sys

import asyncpg
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.interpolate import PchipInterpolator

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# Für den Evaluation-Recompute (GD/QDTW) nach einer Soll-Orientierungs-
# Korrektur: dieselbe Berechnung + Insert-Logik wiederverwenden wie beim
# Upload, statt sie zu duplizieren (backend/app/utils/upload_data/
# evaluation_processor.py importiert trajectory_evaluation selbst).
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
try:
    from app.utils.upload_data.evaluation_processor import _insert_info, _insert_ori_deviations
    from trajectory_evaluation.evaluator import evaluate as _evaluate_trajectory
    _EVAL_AVAILABLE = True
except ImportError as e:
    print(f"Hinweis: Evaluation-Recompute nicht verfügbar ({e}) -- GD/QDTW werden nach "
          f"Orientierungs-Korrekturen nicht neu berechnet.")
    _EVAL_AVAILABLE = False

# Bahn-ID -> diese 3 Tabellen, je mit den Soll-Spalten, die korrigiert werden.
TABLES = {
    "Soll-Position":     ("traj_position_cmd",    ["x_cmd", "y_cmd", "z_cmd"]),
    "Soll-Orientierung": ("traj_orientation_cmd", ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"]),
    "Soll-Gelenkwerte":  ("traj_joint_states",    ["joint_1", "joint_2", "joint_3",
                                                    "joint_4", "joint_5", "joint_6"]),
}

# ── Tuning-Parameter für die Dropout-Erkennung ──────────────────────────────
# Hier zum Testen anpassen -- wirkt auf alle 3 Tabellen.
ZERO_EPS     = 1e-9   # "== 0.0" (Kommunikationsfehler), Toleranz für Rundung
MAX_HORIZON  = 30      # so viele Samples maximal nach dem Dropout nach dem Rückkehrpunkt suchen
N_SUPPORT    = 30     # Stützpunkte links/rechts des korrupierten Bereichs für die PCHIP-Korrektur
PRE_BUFFER   = 1       # so viele Samples VOR dem exakten Null-Dropout ebenfalls als korrupiert
                       # behandeln -- der Kommunikationsfehler betrifft oft 2 Samples: erst ein
                       # "Halbwert" (z.B. exakt die Hälfte der echten Baseline), dann die exakte
                       # Null (siehe Chat-Beleg traj_id=1789659812, joint_4: 11.21->5.605->0.0).
                       # Ohne diesen Puffer wird die Baseline aus dem bereits korrumpierten
                       # Halbwert genommen und die Rückwärtssuche "fängt sich" zu früh.


# ── Ausreißer-Erkennung (Null-Dropout + Aufhol-Rampe) ───────────────────────

def _detect_zero_dropout(values: np.ndarray) -> np.ndarray:
    """
    Kommunikationsfehler: der Socket liefert exakt 0.0 statt des echten
    Werts. Echte kontinuierliche Soll-Werte (Position in mm, Orientierung
    als Quaternion-Komponente, Gelenkwerte in Grad) landen praktisch nie
    durch Zufall exakt auf 0.0 -- ein Vergleich mit einem Winkel-Schwellwert
    (z.B. "Euler-Winkel nahe 0") wäre dagegen unzuverlässig: an echten Daten
    (traj_id=1789659450) erzeugte das 57 Fehlalarme durch normale Bewegung,
    die zufällig durch Pitch~0° läuft, gegenüber nur 1 echtem Dropout.
    """
    return np.abs(values) < ZERO_EPS


def _detect_dropout_span(values: np.ndarray) -> np.ndarray:
    """
    Auf den exakten Null-Dropout folgt oft noch eine kurze "Aufhol"-Rampe,
    bis die Bahn wieder zum echten Verlauf zurückfindet (siehe Chat-Beleg
    traj_id=1789660854, joint_3: 28.29->0->28.29->42.4->...->56.58). Nur den
    Nullpunkt zu fixen lässt diese Rampe als Fehler stehen.

    Deshalb: Start = exakter Null-Dropout, minus PRE_BUFFER Samples davor
    (siehe oben), Ende = der Punkt danach (innerhalb von MAX_HORIZON
    Samples), der dieser (weiter zurückliegenden) Baseline am ähnlichsten
    ist -- die Bahn hat sich dort wieder eingefangen. Dieser Rückkehrpunkt
    selbst dient als Stützpunkt und wird nicht mehr angetastet; alles
    dazwischen gilt als korrupiert.
    """
    zero_mask = _detect_zero_dropout(values)
    n = len(values)
    span_mask = np.zeros(n, dtype=bool)
    for bs, be in _dropout_blocks(zero_mask):
        bs = max(0, bs - PRE_BUFFER)
        if bs == 0:
            continue  # keine Baseline vor dem Dropout verfügbar
        baseline = values[bs - 1]
        lo, hi = be + 1, min(n, be + 1 + MAX_HORIZON)
        if lo >= hi:
            span_mask[bs:be + 1] = True  # kein Rückkehrpunkt im Horizont: nur den Dropout selbst
            continue
        window = values[lo:hi]
        j = lo + int(np.argmin(np.abs(window - baseline)))
        span_mask[bs:j] = True  # bs..j-1 korrupiert, j ist der Rückkehrpunkt (Stützpunkt)
    return span_mask


def _dropout_blocks(mask: np.ndarray) -> list:
    """Fasst zusammenhängende Dropout-Indizes zu (start, end)-Blöcken zusammen."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [idx.size - 1]))
    return [(idx[s], idx[e]) for s, e in zip(starts, ends)]


def _find_support(mask: np.ndarray, start: int, end: int, n_support: int) -> list:
    """n_support gültige (Nicht-Dropout-)Punkte direkt vor und nach einem Block."""
    pre = []
    k = start - 1
    while k >= 0 and len(pre) < n_support:
        if not mask[k]:
            pre.insert(0, k)
        k -= 1
    post = []
    k = end + 1
    while k < len(mask) and len(post) < n_support:
        if not mask[k]:
            post.append(k)
        k += 1
    return pre + post


# ── Korrektur ────────────────────────────────────────────────────────────────

def fix_dropouts_scalar(df: pd.DataFrame, columns: list, n_support: int = N_SUPPORT) -> tuple:
    """PCHIP-Spline-Korrektur direkt auf Skalarwerten (Position, Gelenkwerte).
    Jede Spalte unabhängig -- ein Dropout kann 1, mehrere oder alle Spalten
    einer Zeile gleichzeitig betreffen."""
    df = df.copy()
    changes = []
    for col in columns:
        vals = df[col].to_numpy(dtype=float)
        mask = _detect_dropout_span(vals)
        if not mask.any():
            continue
        fixed = vals.copy()
        for bs, be in _dropout_blocks(mask):
            support = _find_support(mask, bs, be, n_support)
            if not support or support[0] > bs or support[-1] < be:
                continue  # Rand: kein Stützpunkt auf einer Seite
            block_idx = np.arange(bs, be + 1)
            new_vals = PchipInterpolator(support, fixed[support])(block_idx)
            for i, v in zip(block_idx, new_vals):
                changes.append((col, int(i), vals[i], float(v)))
            fixed[block_idx] = new_vals
        df[col] = fixed
    return df, changes


def fix_dropouts_orientation(df: pd.DataFrame, columns: list, n_support: int = N_SUPPORT) -> tuple:
    """
    Erkennung direkt auf den rohen Quaternion-Komponenten (== 0.0), nicht auf
    den daraus berechneten Euler-Winkeln (siehe _detect_zero_dropout).
    Korrektur per PCHIP-Spline direkt auf den Quaternion-Komponenten
    (Vorzeichen-Konsistenz gegen Antipoden + Renormierung). columns muss die
    Reihenfolge [qx, qy, qz, qw] haben.
    """
    df = df.copy()
    Q = df[columns].to_numpy(dtype=float)
    Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)

    mask = np.zeros(len(df), dtype=bool)
    for c in range(4):
        mask |= _detect_dropout_span(Q[:, c])

    changes = []
    if not mask.any():
        return df, changes

    Q_fixed = Q.copy()
    touched = np.zeros(len(df), dtype=bool)
    for bs, be in _dropout_blocks(mask):
        support = _find_support(mask, bs, be, n_support)
        if not support or support[0] > bs or support[-1] < be:
            continue

        # Vorzeichen-Konsistenz: Stützpunkte auf dieselbe Quaternion-Hemisphäre
        # spiegeln wie der erste, sonst mittelt die Spline über den Antipoden.
        support_q = Q_fixed[support].copy()
        flip = (support_q @ support_q[0]) < 0
        support_q[flip] *= -1

        block_idx = np.arange(bs, be + 1)
        new_q = np.column_stack([
            PchipInterpolator(support, support_q[:, c])(block_idx) for c in range(4)
        ])
        new_q /= np.linalg.norm(new_q, axis=1, keepdims=True)

        for i, old_row, new_row in zip(block_idx, Q[block_idx], new_q):
            for c, col in enumerate(columns):
                changes.append((col, int(i), float(old_row[c]), float(new_row[c])))
        Q_fixed[block_idx] = new_q
        touched[block_idx] = True

    # Nur tatsächlich korrigierte Zeilen zurückschreiben -- sonst bekommt jede
    # unveränderte Zeile die eingangs berechnete Renormierung (Q/|Q|)
    # aufgedrückt und weicht durch Rundung minimal vom Rohwert ab.
    for c, col in enumerate(columns):
        df.loc[touched, col] = Q_fixed[touched, c]
    return df, changes


def fix_dropouts(df: pd.DataFrame, columns: list) -> tuple:
    """Dispatcht auf die Quaternion-Variante für die Orientierungs-Spalten,
    sonst die skalare Variante (Position, Gelenkwerte)."""
    if set(columns) == {"qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"}:
        return fix_dropouts_orientation(df, columns)
    return fix_dropouts_scalar(df, columns)


# ── Datenbank ────────────────────────────────────────────────────────────────

async def fetch_table(conn, table: str, columns: list, traj_id: str) -> pd.DataFrame:
    query = f"""
        SELECT seg_id, timestamp, {', '.join(columns)}
        FROM motion.{table}
        WHERE traj_id = $1
        ORDER BY timestamp
    """
    rows = await conn.fetch(query, traj_id)
    return pd.DataFrame(rows, columns=["seg_id", "timestamp"] + columns)


async def fetch_traj_ids_by_date(conn, date_pattern: str, max_trajs: int | None) -> list:
    rows = await conn.fetch(
        "SELECT DISTINCT traj_id FROM motion.traj_info WHERE record_filename LIKE $1 ORDER BY traj_id",
        f"%{date_pattern}%",
    )
    ids = [r["traj_id"] for r in rows]
    if max_trajs:
        ids = ids[:max_trajs]
    return ids


async def apply_changes(conn, table: str, df: pd.DataFrame, changes: list, traj_id: str) -> int:
    """Schreibt korrigierte Zellen zurück in die DB -- ein UPDATE pro betroffener Zeile."""
    if not changes:
        return 0
    by_row = {}
    for col, i, _old, new in changes:
        by_row.setdefault(i, {})[col] = new

    updated = 0
    for i, col_values in by_row.items():
        seg_id = df.iloc[i]["seg_id"]
        timestamp = df.iloc[i]["timestamp"]
        cols = list(col_values.keys())
        set_clause = ", ".join(f"{col} = ${n + 1}" for n, col in enumerate(cols))
        params = [col_values[c] for c in cols] + [traj_id, seg_id, timestamp]
        query = f"""
            UPDATE motion.{table} SET {set_clause}
            WHERE traj_id = ${len(params) - 2} AND seg_id = ${len(params) - 1}
              AND timestamp = ${len(params)}
        """
        result = await conn.execute(query, *params)
        updated += int(result.split()[-1])
    return updated


async def recompute_orientation_evaluation(conn, traj_id: str) -> None:
    """
    Nach einer Soll-Orientierungs-Korrektur sind evaluation.gd_evaluation/
    qdtw_evaluation (+ _info) veraltet -- sie werden einmalig beim Upload aus
    den damals unkorrigierten Werten berechnet und nie automatisch neu
    gerechnet. Deshalb hier: alte Zeilen löschen und mit den jetzt
    korrigierten Werten neu berechnen (dieselbe evaluate()-Funktion wie beim
    Upload, siehe evaluation_processor.py).

    GD/QDTW rechnen immer über die GESAMTE Bahn (SLERP-Resampling bzw. DTW
    über alle Segmente hinweg), nie pro Segment -- deshalb immer die ganze
    traj_id neu rechnen, auch wenn nur ein Segment korrigiert wurde.
    """
    if not _EVAL_AVAILABLE:
        print("  Evaluation-Recompute übersprungen (trajectory_evaluation nicht verfügbar).")
        return

    soll_df = await fetch_table(conn, "traj_orientation_cmd", TABLES["Soll-Orientierung"][1], traj_id)
    ist_rows = await conn.fetch("""
        SELECT seg_id, qx_act, qy_act, qz_act, qw_act
        FROM motion.traj_pose_act
        WHERE traj_id = $1
        ORDER BY timestamp
    """, traj_id)
    if soll_df.empty or not ist_rows:
        print("  Evaluation-Recompute übersprungen (keine Soll-/Ist-Orientierungsdaten).")
        return

    soll_ori = soll_df[["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"]].to_numpy(dtype=float)
    ist_ori = np.array([[r["qx_act"], r["qy_act"], r["qz_act"], r["qw_act"]] for r in ist_rows], dtype=float)
    seg_ids_ori = [r["seg_id"] for r in ist_rows]

    results = _evaluate_trajectory(
        soll_pos=np.zeros((1, 3)), ist_pos=np.zeros((1, 3)),
        soll_ori=soll_ori, ist_ori=ist_ori,
        segment_ids_pos=None, segment_ids_ori=seg_ids_ori,
        use_ed=False, use_sidtw=False, use_gd=True, use_qdtw=True,
    )

    for method in ("gd", "qdtw"):
        await conn.execute(f"DELETE FROM evaluation.{method}_evaluation WHERE traj_id = $1", traj_id)
        await conn.execute(f"DELETE FROM evaluation.{method}_info WHERE traj_id = $1", traj_id)

        result = results[method]
        d = result.distances
        seg_ids = result.segment_ids

        seen = []
        for sid in seg_ids:
            if sid not in seen:
                seen.append(sid)
        for sid in seen:
            mask = [i for i, s in enumerate(seg_ids) if s == sid]
            seg_d = d[mask]
            await _insert_info(conn, method, traj_id, str(sid),
                                round(float(np.min(seg_d)), 7), round(float(np.max(seg_d)), 7),
                                round(float(np.mean(seg_d)), 7), round(float(np.std(seg_d)), 7))
        await _insert_info(conn, method, traj_id, traj_id,
                            round(float(np.min(d)), 7), round(float(np.max(d)), 7),
                            round(float(np.mean(d)), 7), round(float(np.std(d)), 7))

        await _insert_ori_deviations(conn, method, traj_id, d,
                                      result.soll_aligned, result.ist_aligned, seg_ids)

    print(f"  Evaluation neu berechnet: GD avg={results['gd'].avg_distance:.3f}° "
          f"QDTW avg={results['qdtw'].avg_distance:.3f}°")


# ── Report ───────────────────────────────────────────────────────────────────

def print_report(label: str, df: pd.DataFrame, changes: list) -> None:
    print(f"\n{'='*60}\n  {label} ({len(df)} Punkte)\n{'='*60}")
    if not changes:
        print("  Keine Korrekturen.")
        return
    print(f"  {len(changes)} Werte korrigiert:")
    for col, i, old, new in changes:
        seg_id = df.iloc[i]["seg_id"]
        ts = df.iloc[i]["timestamp"]
        print(f"    [{col:9s}] seg={seg_id} t={ts}  {old:.4f} -> {new:.4f}")


# ── Plot ─────────────────────────────────────────────────────────────────────

def plot_before_after(label: str, df: pd.DataFrame, df_fixed: pd.DataFrame, columns: list) -> None:
    import matplotlib.pyplot as plt

    n = len(columns)
    n_cols = min(3, n)
    n_rows = -(-n // n_cols)  # ceil
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 3.5 * n_rows), squeeze=False)
    fig.suptitle(label, fontsize=13)

    x = np.arange(len(df))
    for i, col in enumerate(columns):
        ax = axes[i // n_cols][i % n_cols]
        before = df[col].to_numpy(dtype=float)
        after = df_fixed[col].to_numpy(dtype=float)
        changed = before != after

        ax.plot(x, before, color='lightgray', lw=1.5, label='vorher')
        ax.plot(x, after, color='tab:blue', lw=1, label='nachher')
        if changed.any():
            ax.scatter(x[changed], after[changed], color='tab:red', s=18, zorder=5, label='korrigiert')
        ax.set_title(col, fontsize=9)
        ax.set_xlabel('Punkt-Index', fontsize=7)
        ax.tick_params(labelsize=6)
        ax.legend(fontsize=6)

    for i in range(n, n_rows * n_cols):
        axes[i // n_cols][i % n_cols].set_visible(False)

    plt.tight_layout()


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(args) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        if args.traj_id:
            traj_ids = [args.traj_id]
        else:
            traj_ids = await fetch_traj_ids_by_date(conn, args.date, args.max_trajs)
            print(f"{len(traj_ids)} Bahnen für Muster '%{args.date}%'")

        total_applied = 0
        for idx, traj_id in enumerate(traj_ids, 1):
            print(f"\n[{idx}/{len(traj_ids)}] Bahn-ID: {traj_id}")
            pending = []
            for label, (table, columns) in TABLES.items():
                df = await fetch_table(conn, table, columns, traj_id)
                if df.empty:
                    continue
                df_fixed, changes = fix_dropouts(df, columns)
                if not changes:
                    continue
                print_report(label, df, changes)
                pending.append((label, table, df, changes))
                if args.plot:
                    plot_before_after(label, df, df_fixed, columns)

            if not pending:
                print("  Keine Korrekturen.")
                continue

            if args.plot:
                import matplotlib.pyplot as plt
                plt.show(block=True)

            if not args.update:
                continue

            resp = input("  Enter = übernehmen, s + Enter = überspringen: ").strip().lower()
            if resp == "s":
                print("  Übersprungen.")
                continue

            async with conn.transaction():
                for label, table, df, changes in pending:
                    n = await apply_changes(conn, table, df, changes, traj_id)
                    total_applied += n
                    print(f"  {label}: {n} Zeilen aktualisiert.")

                if any(label == "Soll-Orientierung" for label, table, df, changes in pending):
                    await recompute_orientation_evaluation(conn, traj_id)

        if args.update:
            print(f"\nFertig: {total_applied} Zeilen aktualisiert.")
        else:
            print("\nDry-Run -- nichts geschrieben (--update zum tatsächlichen Anwenden).")
    finally:
        await conn.close()


def _selftest() -> None:
    """Kein DB-Zugriff: prüft die Dropout-Erkennung + Korrektur."""
    # Einzelner Null-Dropout auf einer sonst wechselnden, aber nie exakt
    # nulldurchlaufenden Baseline wird per PCHIP-Spline auf die Umgebung
    # zurückgezogen.
    n = 60
    smooth = 100 + 5 * np.sin(np.linspace(0, 3, n))  # bleibt immer > 0
    dropped = smooth.copy()
    dropped[30] = 0.0
    df_drop = pd.DataFrame({"seg_id": ["s1"] * n, "timestamp": range(n), "x_cmd": dropped})
    out1, changes1 = fix_dropouts_scalar(df_drop, ["x_cmd"])
    assert any(i == 30 for _, i, _, _ in changes1), changes1
    assert abs(out1["x_cmd"].iloc[30] - smooth[30]) < 1.0, out1["x_cmd"].iloc[30]

    # unverändertes Signal, das nie exakt 0.0 erreicht, bleibt unangetastet
    out2, changes2 = fix_dropouts_scalar(
        pd.DataFrame({"seg_id": ["s1"] * n, "timestamp": range(n), "x_cmd": smooth}),
        ["x_cmd"],
    )
    assert changes2 == []

    print("OK: fix_dropouts_scalar Einzel-Dropout selftest passed")

    # Fehlalarm-Test: Signal, das GLATT durch 0 hindurchläuft (z.B. ein
    # Vorzeichenwechsel bei echter Bewegung), darf nicht angefasst werden --
    # nur eine exakte 0.0 zählt als Dropout, nicht "nahe an 0".
    smooth_crossing = np.linspace(-5.0, 5.0, n)
    smooth_crossing = np.delete(smooth_crossing, np.argmin(np.abs(smooth_crossing)))  # exakte 0 vermeiden
    df_cross = pd.DataFrame({
        "seg_id": ["s1"] * len(smooth_crossing), "timestamp": range(len(smooth_crossing)),
        "x_cmd": smooth_crossing,
    })
    out3, changes3 = fix_dropouts_scalar(df_cross, ["x_cmd"])
    assert changes3 == [], changes3

    print("OK: fix_dropouts_scalar Fehlalarm (glatter Nulldurchgang) selftest passed")

    # Mehrere Spalten gleichzeitig betroffen (wie bei echten Gelenkwerten:
    # 2, 3 oder alle 6 Spalten fallen an derselben Zeile gleichzeitig auf 0).
    joint_a = 56.58 + np.sin(np.linspace(0, 2, n))
    joint_b = -57.8 + np.cos(np.linspace(0, 2, n))
    joint_a[25] = 0.0
    joint_b[25] = 0.0
    df_multi = pd.DataFrame({
        "seg_id": ["s1"] * n, "timestamp": range(n), "joint_a": joint_a, "joint_b": joint_b,
    })
    out4, changes4 = fix_dropouts_scalar(df_multi, ["joint_a", "joint_b"])
    changed4 = {(col, i) for col, i, _, _ in changes4}
    assert ("joint_a", 25) in changed4 and ("joint_b", 25) in changed4, changes4

    print("OK: fix_dropouts_scalar Mehrspalten-Dropout selftest passed")

    # Orientierung: eine oder mehrere Quaternion-Komponenten fallen auf 0
    # (siehe Chat-Beleg traj_id=1789659450, Index 974: qy_cmd UND qz_cmd
    # gleichzeitig exakt 0). Nur die tatsächlich korrigierten Zeilen dürfen
    # sich ändern (Regression: vorher wurde beim Zurückschreiben versehentlich
    # die GANZE Spalte mit der Renormierung überschrieben).
    n_q = 40
    qx = np.linspace(0.4, 0.42, n_q)
    qy = np.linspace(0.66, 0.64, n_q)
    qz = np.linspace(0.36, 0.35, n_q)
    qw = np.sqrt(np.clip(1 - qx**2 - qy**2 - qz**2, 0, None))
    qy[20] = 0.0
    qz[20] = 0.0
    df_quat = pd.DataFrame({
        "seg_id": ["s1"] * n_q, "timestamp": range(n_q),
        "qx_cmd": qx, "qy_cmd": qy, "qz_cmd": qz, "qw_cmd": qw,
    })
    raw = df_quat.copy()
    out5, changes5 = fix_dropouts_orientation(df_quat, ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"])
    changed_rows5 = {i for _, i, _, _ in changes5}
    assert 20 in changed_rows5, changes5
    for i in range(n_q):
        if i in changed_rows5:
            continue
        for col in ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"]:
            assert out5[col].iloc[i] == raw[col].iloc[i], (i, col, out5[col].iloc[i], raw[col].iloc[i])

    print("OK: fix_dropouts_orientation Mehrkomponenten-Dropout / untouched-rows selftest passed")

    # Aufhol-Rampe: auf den Dropout folgt eine mehrsamplige Erholung, bevor
    # die Bahn wieder zur Baseline (56.58) zurückfindet -- die GESAMTE Rampe
    # muss mitkorrigiert werden, nicht nur der einzelne Nullpunkt (siehe
    # Chat-Herleitung, traj_id=1789660854, joint_3).
    hold = 56.58
    ramp = [0.0, 28.29, 42.435, 49.5075, 53.04375, 54.811875, 55.695938,
            56.137969, 56.358984, 56.469492, 56.524746, 56.552373]
    vals = [hold] * 12 + ramp + [hold] * 10
    df_ramp = pd.DataFrame({"seg_id": ["s1"] * len(vals), "timestamp": range(len(vals)), "x_cmd": vals})
    dropout_idx = 12  # Index von ramp[0] == 0.0 in vals
    out6, changes6 = fix_dropouts_scalar(df_ramp, ["x_cmd"])
    changed_idx6 = {i for _, i, _, _ in changes6}
    assert dropout_idx in changed_idx6, changes6
    for offset in (1, 2, 3, 4):  # Teile der Rampe müssen mitkorrigiert werden
        assert (dropout_idx + offset) in changed_idx6, (offset, changes6)
    # der korrigierte Dropout-Wert muss nahe an der echten Baseline liegen,
    # nicht an der (selbst schon verzerrten) Rampe
    fixed_val = next(v for c, i, _o, v in changes6 if i == dropout_idx)
    assert abs(fixed_val - hold) < 1.0, fixed_val

    print("OK: fix_dropouts_scalar Aufhol-Rampe selftest passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Korrigiert Kommunikations-Dropouts (Wert==0.0) in Soll-Position/-Orientierung/-Gelenkwerten."
    )
    parser.add_argument("--traj-id", help="Bahn-ID (einzelne Bahn)")
    parser.add_argument("--date", help="record_filename-Muster (LIKE %%wert%%), z.B. 20260724_15 "
                                        "-- iteriert alle passenden Bahnen")
    parser.add_argument("--max-trajs", type=int, help="Max. Anzahl Bahnen bei --date")
    parser.add_argument("--update", action="store_true",
                         help="Korrekturen nach Bestätigung (Enter) in die DB schreiben. "
                              "Ohne dieses Flag reine Vorschau, es wird nichts geschrieben.")
    parser.add_argument("--plot", action="store_true", help="Vorher/Nachher-Plot pro Tabelle anzeigen")
    parser.add_argument("--selftest", action="store_true", help="Nur den Selbsttest ausführen")
    args = parser.parse_args()

    if args.selftest:
        _selftest()
    elif args.traj_id or args.date:
        asyncio.run(main(args))
    else:
        parser.error("Entweder --traj-id, --date oder --selftest angeben.")
