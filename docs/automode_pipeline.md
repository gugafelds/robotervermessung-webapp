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
│  for _ in range(ucb_k):                                             │
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
│  │ 3. POST /api/similarity/search/candidate                       │ │
│  │    → Stage 1: RRF-Suche über Segmente (schnell)                │ │
│  │    → Stage 2 (optional): DTW-Reranking (genauer, langsamer)    │ │
│  │    → Rückgabe: segment_similarity + prognosis                  │ │
│  │                                                                │ │
│  │ 4. Score berechnen (Akquisitionsfunktion)                      │ │
│  │    → score = mean( σᵢ · dᵢ )  für alle Segmente i             │ │
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

$$\text{score} = \frac{1}{N} \sum_{i=1}^{N} \sigma_i \cdot d_{\min,i}$$

| Symbol       | Bedeutung |
|--------------|-----------|
| $N$          | Anzahl der Segmente des Kandidaten |
| $\sigma_i$   | Unsicherheit der k-NN-Prognose für Segment $i$ (aus `prognosis.segments[i].sigma`) |
| $d_{\min,i}$ | DTW-Abstand zum nächsten Nachbarn von Segment $i$ (aus `segment_similarity[i].similar_segments.results[0].dtw_distance`) |

**Interpretation:**  
Ein Kandidat erhält einen hohen Score, wenn er **unbekannte** Regionen des
Fehlerraums abdeckt ($d_{\min,i}$ groß = weit von bekannten Trajektorien
entfernt) **und** die Prognose dort **unsicher** ist ($\sigma_i$ groß = wenig
Vertrauen in den vorhergesagten Fehler).

Beide Faktoren müssen gleichzeitig hoch sein — eine Region, die zwar
unbekannt, aber gut extrapoliert werden kann, wird nicht bevorzugt.

### Kommentierte Alternative: UCB (Snoek et al. 2012)

$$\text{score} = \hat{p} + \kappa \cdot \sigma$$

Globales $\hat{p}$ (erwarteter Fehler) + globale Unsicherheit $\sigma$.
Wurde durch die segmentweise Formel ersetzt, da $\hat{p}$ für externe
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
| `similarity_client.py` | `…/generators/similarity_client.py` | HTTP-Client für `/api/similarity/search/candidate` |
| `analytical_simulator.py` | `…/generators/` | Schnelle analytische Simulation der Kandidaten |
| `validation_rv2.py` | `backend/scripts/` | Offline-Validierung: LOO + externe Validierung der Wissensbasis |
| `calibration_set_builder.py` | `backend/scripts/` | Aufbau der initialen Wissensbasis |
