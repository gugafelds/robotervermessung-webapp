# AutoMode — Aktive Trajektorienselektion

## Überblick

AutoMode wählt Messtrajektorien **informationstheoretisch optimal** aus:
Statt Trajektorien zufällig oder manuell zu definieren, werden pro Runde
`ucb_k` Kandidaten zufällig generiert, über die Ähnlichkeitssuche bewertet
und der informativste Kandidat gemessen.

Ziel: Mit möglichst wenigen Messungen eine möglichst gute Abdeckung des
Fehlerraums des Roboters erreichen.

---

## Parameter

| Parameter          | Default | Bedeutung |
|--------------------|---------|-----------|
| `number_of_batches`| 5       | Wie viele Batches (= Messungen) insgesamt aufgenommen werden |
| `batch_size`       | 2       | Waypoints pro Batch (Segmente der Trajektorie) |
| `ucb_k`            | 5       | Kandidaten pro Runde, aus denen der beste ausgewählt wird |
| `kappa`            | 1.0     | (reserviert für UCB-Formel, aktuell nicht aktiv) |
| `move_type`        | linear  | Bewegungstyp der generierten Trajektorien |
| `plane`            | 3D      | Raumebene für die Kandidatengenerierung |
| `min_distance`     | —       | Mindestabstand zwischen Waypoints |
| `weight`           | 12.0    | Nutzlast [kg] für die Ähnlichkeitssuche |
| `include_tags`     | []      | Filtert die Wissensbasis auf bestimmte Datensätze |
| `calibration_tag`  | all     | Kalibrierungstag für die konforme Prognose |
| `similarity_k`     | 10      | Anzahl nächster Nachbarn in der Ähnlichkeitssuche |
| `stage2_active`    | False   | Aktiviert DTW-Reranking (Stage 2) |

---

## Pipeline pro Runde

```
┌─────────────────────────────────────────────────────────────────────┐
│  Runde (while batches_accepted < number_of_batches)                 │
│                                                                     │
│  ucb_k Kandidaten parallel (RoboDK-Connection-Pool, siehe            │
│  recorder_parameters.py: PARALLEL_ROBODK_CONNECTIONS):              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 1. Kandidat generieren                                         │ │
│  │    generate_auto_batch(batch_size, move_type, seen_positions)  │ │
│  │    → zufällige Waypoints im Roboterarbeitsraum                 │ │
│  │    → seen_positions verhindert Duplikate mit bereits           │ │
│  │      gemessenen Positionen                                     │ │
│  │                                                                │ │
│  │ 2. Analytisch simulieren                                       │ │
│  │    → Zeitreihe (Position, Orientierung, Joints, Geschw.)       │ │
│  │    → kein RoboDK nötig, sehr schnell                           │ │
│  │                                                                │ │
│  │ 3. POST /api/similarity/search/candidates_batch                │ │
│  │    (alle ucb_k Kandidaten in einem Request, siehe unten)       │ │
│  │    → Stage 1: RRF-Suche über Segmente (schnell)                │ │
│  │    → Stage 2 (optional): DTW-Reranking (genauer, langsamer)    │ │
│  │    → Rückgabe: segment_similarity + prognosis                  │ │
│  │                                                                │ │
│  │ 4. Score berechnen (Akquisitionsfunktion, siehe unten)         │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  → bester Kandidat (max score) weiter                               │
│                                                                     │
│  5. RoboDK-Validierung                                              │
│     _validate_batch_robodk()                                        │
│     → kollisionsfrei? Gelenklimits ok? Erreichbar?                  │
│     → nein: Runde wiederholen                                       │
│                                                                     │
│  6. Batch akzeptiert → accepted_batches.append(best_batch)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Akquisitionsfunktion

### Aktuell: Gulimov & Kalinichenko (2022) — pro Segment

```
score = Σ(σᵢ · dᵢ · lᵢ) / Σ(lᵢ)      — Summe über alle Segmente i=1..N
```

| Symbol  | Bedeutung |
|---------|-----------|
| `N`     | Anzahl der Segmente des Kandidaten |
| `σᵢ`    | Unsicherheit der k-NN-Prognose für Segment i (aus `prognosis.segments[i].sigma`) |
| `lᵢ`    | Länge von Segment i [mm] — längengewichtetes Mittel statt einfachem Mittel |
| `dᵢ`    | Abstand zum nächsten Nachbarn von Segment i: bei `stage2_active=True` der DTW-Abstand (`dtw_distance`); bei `stage2_active=False` gibt es keine DTW-Distanz — stattdessen `1 / RRF-Score` des besten Treffers (RRF ist eine Ähnlichkeit, hoch = nah; invertiert, damit hoch weiterhin "weit weg" bedeutet) |

**Bekannte Einschränkung:** `σᵢ` und `dᵢ` sind unnormalisiert und liegen auf
sehr unterschiedlichen Skalen (σ ≈ 0.1-0.3, DTW-Distanz oft im Bereich
mehrerer Zehntausend) — der Score wird dadurch praktisch nur von `dᵢ`
getrieben. Eine globale Normalisierung ist in Arbeit.

**Interpretation:**  
Ein Kandidat erhält einen hohen Score, wenn er **unbekannte** Regionen des
Fehlerraums abdeckt (`dᵢ` groß = weit von bekannten Trajektorien entfernt)
**und** die Prognose dort **unsicher** ist (`σᵢ` groß = wenig Vertrauen in
den vorhergesagten Fehler).

Beide Faktoren müssen gleichzeitig hoch sein — eine Region, die zwar
unbekannt, aber gut extrapoliert werden kann, wird nicht bevorzugt.

### Kommentierte Alternative: UCB (Snoek et al. 2012)

```
score = p_hat + kappa · σ
```

Globales `p_hat` (erwarteter Fehler) + globale Unsicherheit `σ`.
Wurde durch die segmentweise Formel ersetzt, da `p_hat` für externe
Kandidaten keinen direkten Informationsgewinn über die räumliche
Lage kodiert.

---

## Ähnlichkeitssuche: Was passiert im Backend

### Stage 1 — RRF (Reciprocal Rank Fusion)

- Für jeden Kandidaten werden die Segmente einzeln gegen die Wissensbasis gesucht
- Metrik: SIDTW (Scale-Invariant DTW) über Position, Orientierung, Joints, Geschwindigkeit
- Rückgabe: `segment_similarity[i].similar_segments` mit Ranking und `dtw_distance`
- `traj_similarity` ist bei externen Kandidaten (POST /candidate) **immer leer**

### Stage 2 — DTW-Reranking (optional)

- Reranking der Top-K Ergebnisse mit echten metrischen DTW-Distanzen
- Genauer, aber langsamer
- `stage2_active=True` empfohlen für die Akquisitionsfunktion, da $d_{\min,i}$ dann metrisch korrekt ist

### Prognose

- `prognosis.segments[i]` enthält pro Segment:
  - `p_hat` — erwarteter Positionsfehler [mm]
  - `sigma` — Unsicherheit der Prognose
- `prognosis.decomposed` — längengewichtetes Aggregat über alle Segmente (global)
- `conformal_active=False` → k-NN-Schätzer direkt, ohne konformes Intervall (schneller)

---

## Cold Start

Wenn noch keine Trajektorien in der Wissensbasis sind (oder `include_tags`
filtert alles weg), gibt die Prognose kein `p_hat`/`sigma` zurück.

In diesem Fall: **erster zufällig generierter Kandidat** wird als Fallback
akzeptiert (kein Score-Vergleich möglich).

---

## Kollisionscheck (RoboDK)

Nach der Score-Auswahl wird `_validate_batch_robodk()` aufgerufen:

- RoboDK simuliert die Bewegung des Roboters
- Kollisionserkennung + Gelenklimit-Prüfung
- Bei Fehler: Runde wird wiederholt (max. `number_of_batches × 10` Versuche)

---

## Ausgabe

- RAPID-Programm (`.mod`) wird geschrieben via `RapidWriter.write_auto_mode()`
- `_waypoints` wird im Config gespeichert (für Logging / Metadaten)
- Alle akzeptierten Positionen werden in `seen_positions` geführt,
  sodass Duplikate in späteren Runden ausgeschlossen werden

---

## Verwandte Komponenten

| Komponente | Pfad | Rolle |
|---|---|---|
| `trajectory_builder.py` | `src/trajectory_generation/…` | AutoMode-Logik, Akquisitionsfunktion |
| `similarity_client.py` | `…/generators/similarity_client.py` | HTTP-Client für `/api/similarity/search/candidates_batch` |
| `analytical_simulator.py` | `…/generators/` | Schnelle analytische Simulation der Kandidaten |
| `validation_rv2.py` | `backend/scripts/` | Offline-Validierung: LOO + externe Validierung der Wissensbasis |
| `calibration_set_builder.py` | `backend/scripts/` | Aufbau der initialen Wissensbasis |
