"""
fix_soll_values.py
===================
Korrigiert Ausreißer in Soll-Position, -Orientierung und -Gelenkwerten.

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

import asyncpg
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.interpolate import PchipInterpolator

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# Bahn-ID -> diese 3 Tabellen, je mit den Soll-Spalten, die korrigiert werden.
TABLES = {
    "Soll-Position":     ("traj_position_cmd",    ["x_cmd", "y_cmd", "z_cmd"]),
    "Soll-Orientierung": ("traj_orientation_cmd", ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"]),
    "Soll-Gelenkwerte":  ("traj_joint_states",    ["joint_1", "joint_2", "joint_3",
                                                    "joint_4", "joint_5", "joint_6"]),
}

# ── Tuning-Parameter für die Sprung-und-Rückkehr-Erkennung ──────────────────
# Hier zum Testen anpassen -- wirkt auf alle 3 Tabellen (Position: mm,
# Orientierung: Grad im Euler-Raum, Gelenkwerte: Grad).
SIGMA_THRESH = 10.0   # Sprung muss > SIGMA_THRESH * lokale Schrittgröße sein
MIN_ABS      = 0.1   # ... UND absolut größer als das (Einheit der jeweiligen Spalte)
TOL_FRAC     = 0.1   # "zurück zur Baseline" = Abweichung <= TOL_FRAC * jump_thresh
MAX_HORIZON  = 80     # so viele Samples maximal nach Rückkehr zur Baseline suchen
STEP_WINDOW  = 50     # Fenstergröße für den robusten Schrittgrößen-Median
N_SUPPORT    = 20     # Stützpunkte links/rechts der Exkursion für die PCHIP-Korrektur


# ── Ausreißer-Erkennung ("Sprung-und-Rückkehr") ─────────────────────────────

def _detect_excursions(values: np.ndarray) -> np.ndarray:
    """
    Ein Spike beginnt mit einem einzelnen Schritt, der viel größer ist als
    die lokal übliche Schrittgröße (robuster gleitender Median von |diff|),
    und endet genau dort, wo das Signal wieder nahe an den Wert VOR dem
    Sprung ("Baseline") zurückkehrt -- egal wie viele Samples das dauert.

    Kehrt das Signal innerhalb von MAX_HORIZON Samples NICHT zur Baseline
    zurück, wird gar nichts geflaggt -- das ist dann echte Bewegung zu einem
    neuen Ziel, keine Korruption (Sicherheitsnetz gegen Fehlalarme bei
    normalen Verfahrbewegungen).
    """
    n = len(values)
    mask = np.zeros(n, dtype=bool)
    if n < 3:
        return mask

    d = np.diff(values)
    step_med = pd.Series(np.abs(d)).rolling(STEP_WINDOW, center=True, min_periods=1).median().to_numpy()

    i = 1
    while i < n:
        jump_thresh = max(SIGMA_THRESH * step_med[i - 1], MIN_ABS)
        jump = abs(d[i - 1])
        if jump > jump_thresh:
            baseline = values[i - 1]
            tol = max(TOL_FRAC * jump_thresh, MIN_ABS * 0.5)
            j = i
            found = False
            while j < min(n, i + MAX_HORIZON):
                if abs(values[j] - baseline) <= tol:
                    found = True
                    break
                j += 1
            if found:
                mask[i:j] = True
                i = j + 1
                continue
        i += 1
    return mask


def _excursion_blocks(mask: np.ndarray) -> list:
    """Fasst zusammenhängende Exkursions-Indizes zu (start, end)-Blöcken zusammen."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [idx.size - 1]))
    return [(idx[s], idx[e]) for s, e in zip(starts, ends)]


def _find_support(mask: np.ndarray, start: int, end: int, n_support: int) -> list:
    """n_support gültige (Nicht-Exkursions-)Punkte direkt vor und nach einem Block."""
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

def fix_excursions_scalar(df: pd.DataFrame, columns: list, n_support: int = N_SUPPORT) -> tuple:
    """PCHIP-Spline-Korrektur direkt auf Skalarwerten (Position, Gelenkwerte)."""
    df = df.copy()
    changes = []
    for col in columns:
        vals = df[col].to_numpy(dtype=float)
        mask = _detect_excursions(vals)
        if not mask.any():
            continue
        fixed = vals.copy()
        for bs, be in _excursion_blocks(mask):
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


def _quat_to_euler_deg(Q: np.ndarray) -> np.ndarray:
    x, y, z, w = Q[:, 0], Q[:, 1], Q[:, 2], Q[:, 3]
    roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x**2 + y**2)))
    sinp = np.clip(2 * (w * y - z * x), -1.0, 1.0)
    pitch = np.degrees(np.arcsin(sinp))
    yaw = np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y**2 + z**2)))
    return np.column_stack([roll, pitch, yaw])


def _fix_gimbal_lock(euler: np.ndarray) -> np.ndarray:
    euler = euler.copy()
    for c in range(3):
        angles = euler[:, c]
        diffs = np.abs(np.diff(angles))
        big_jumps = diffs[diffs > 180]
        if big_jumps.size:
            threshold = min(big_jumps.mean() / 2, 30)
            mask = (np.abs(np.abs(angles) - 180) < threshold) & (angles < 0)
            euler[mask, c] = angles[mask] + 360
    return euler


def fix_excursions_orientation(df: pd.DataFrame, columns: list, n_support: int = N_SUPPORT) -> tuple:
    """
    Erkennung im Euler-Raum (robuster gegen Gimbal-Lock-Sprünge als direkt
    auf den Quaternion-Komponenten), Korrektur per PCHIP-Spline direkt auf
    den Quaternion-Komponenten (Vorzeichen-Konsistenz gegen Antipoden +
    Renormierung). columns muss die Reihenfolge [qx, qy, qz, qw] haben.
    """
    df = df.copy()
    Q = df[columns].to_numpy(dtype=float)
    Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)
    euler = _fix_gimbal_lock(_quat_to_euler_deg(Q))

    mask = np.zeros(len(df), dtype=bool)
    for c in range(3):
        mask |= _detect_excursions(euler[:, c])

    changes = []
    if not mask.any():
        return df, changes

    Q_fixed = Q.copy()
    touched = np.zeros(len(df), dtype=bool)
    for bs, be in _excursion_blocks(mask):
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


def fix_excursions(df: pd.DataFrame, columns: list) -> tuple:
    """Dispatcht auf die Quaternion-Variante für die Orientierungs-Spalten,
    sonst die skalare Variante (Position, Gelenkwerte)."""
    if set(columns) == {"qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"}:
        return fix_excursions_orientation(df, columns)
    return fix_excursions_scalar(df, columns)


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
                df_fixed, changes = fix_excursions(df, columns)
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

        if args.update:
            print(f"\nFertig: {total_applied} Zeilen aktualisiert.")
        else:
            print("\nDry-Run -- nichts geschrieben (--update zum tatsächlichen Anwenden).")
    finally:
        await conn.close()


def _selftest() -> None:
    """Kein DB-Zugriff: prüft die Exkursions-Erkennung + Korrektur."""
    # Einzelner deutlicher Spike auf einer flachen Baseline (wie ein echtes
    # Dwell-Segment) wird per PCHIP-Spline auf die Umgebung zurückgezogen.
    # Flach statt driftend, damit "Rückkehr zur Baseline" bei niedrigem
    # TOL_FRAC/MIN_ABS zuverlässig sofort erfüllt ist.
    n = 60
    smooth = np.full(n, 100.0)
    spiky = smooth.copy()
    spiky[30] += 50.0
    df_spike = pd.DataFrame({"seg_id": ["s1"] * n, "timestamp": range(n), "x_cmd": spiky})
    out1, changes1 = fix_excursions_scalar(df_spike, ["x_cmd"])
    assert any(i == 30 for _, i, _, _ in changes1), changes1
    assert abs(out1["x_cmd"].iloc[30] - smooth[30]) < 1.0, out1["x_cmd"].iloc[30]

    # unverändertes, glattes Signal bleibt unangetastet
    out2, changes2 = fix_excursions_scalar(
        pd.DataFrame({"seg_id": ["s1"] * n, "timestamp": range(n), "x_cmd": smooth}),
        ["x_cmd"],
    )
    assert changes2 == []

    print("OK: fix_excursions_scalar Einzel-Spike selftest passed")

    # Dropout (Wert=0) gefolgt von echter, schneller Erholungsrampe: die
    # GESAMTE Exkursion (Sprung bis Rückkehr zur Baseline) gilt als
    # korrupiert -- die Rampe ist rein rechnerisch die Antwort eines Filters
    # auf den einen Dropout (Fehler halbiert sich pro Schritt), nicht echte
    # unabhängige Bewegung (siehe Chat-Herleitung, traj_id=1789660854).
    hold = 56.58
    ramp = [28.29, 0.0, 28.29, 42.435, 49.5075, 53.04375, 54.811875]
    vals = [hold] * 12 + ramp + [56.35, 56.47, 56.52, 56.55] + [hold] * 10
    df_ramp = pd.DataFrame({"seg_id": ["s1"] * len(vals), "timestamp": range(len(vals)), "x_cmd": vals})
    dropout_idx = 13  # Index von ramp[1] == 0.0 in vals
    out3, changes3 = fix_excursions_scalar(df_ramp, ["x_cmd"])
    changed_idx3 = {i for _, i, _, _ in changes3}
    assert dropout_idx in changed_idx3, changes3
    assert (dropout_idx - 1) in changed_idx3, changes3  # der erste Sprung-Schritt

    # Fehlalarm-Test: echte Bewegung zu einem neuen Ziel, die NICHT zur
    # Baseline zurückkehrt, darf nicht angefasst werden.
    real_move = [10.0] * 15 + list(np.linspace(10.0, 80.0, 20)) + [80.0] * 15
    df_move = pd.DataFrame({
        "seg_id": ["s1"] * len(real_move), "timestamp": range(len(real_move)), "x_cmd": real_move,
    })
    out4, changes4 = fix_excursions_scalar(df_move, ["x_cmd"])
    assert changes4 == [], changes4

    print("OK: fix_excursions_scalar Dropout+Rampe / Fehlalarm selftest passed")

    # Regression: fix_excursions_orientation durfte nur die tatsächlich
    # korrigierten Zeilen verändern (nicht die ganze Spalte per Renormierung
    # überschreiben -- siehe Chat: 1758/1758 Zeilen "geändert" bei nur 2
    # echten Fixes).
    n_q = 40
    qx = np.linspace(0.4, 0.42, n_q)
    qy = np.linspace(0.66, 0.64, n_q)
    qz = np.linspace(0.36, 0.35, n_q)
    qw = np.sqrt(np.clip(1 - qx**2 - qy**2 - qz**2, 0, None))
    qz[20] = 0.0  # deutlicher Spike an einer Stelle
    df_quat = pd.DataFrame({
        "seg_id": ["s1"] * n_q, "timestamp": range(n_q),
        "qx_cmd": qx, "qy_cmd": qy, "qz_cmd": qz, "qw_cmd": qw,
    })
    raw = df_quat.copy()
    out5, changes5 = fix_excursions_orientation(df_quat, ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"])
    changed_rows5 = {i for _, i, _, _ in changes5}
    assert changed_rows5, "Testdaten müssten mindestens eine Korrektur auslösen"
    for i in range(n_q):
        if i in changed_rows5:
            continue
        for col in ["qx_cmd", "qy_cmd", "qz_cmd", "qw_cmd"]:
            assert out5[col].iloc[i] == raw[col].iloc[i], (i, col, out5[col].iloc[i], raw[col].iloc[i])

    print("OK: fix_excursions_orientation untouched-rows selftest passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Korrigiert Ausreißer in Soll-Position/-Orientierung/-Gelenkwerten."
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
