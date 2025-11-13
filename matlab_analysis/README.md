# DTW Baseline Analysis für Roboter-Trajektorien

Dieser Ordner enthält alle Skripte zur **DTW-Baseline-Analyse** für den Vergleich mit euren Embedding-basierten Ähnlichkeitssuche.

## 📁 Struktur

```
matlab_analysis/
├── README.md                          # Diese Datei
├── dtw_baseline_analysis.m            # Hauptskript: DTW-Baseline Analyse
├── compute_multivariate_dtw.m         # Helper: 6D DTW-Berechnung
├── analyze_specific_query.m           # Helper: Detailanalyse einzelner Queries
└── (Ergebnisse werden hier gespeichert)
```

## 🚀 Quick Start

### Schritt 1: Daten exportieren (Python)

Zuerst müssen die Trajektorien aus der PostgreSQL-Datenbank exportiert werden:

```bash
cd ../backend/scripts
python export_trajectories_for_matlab.py --output ./matlab_data --limit 100
```

**Parameter:**
- `--output`: Output-Verzeichnis (default: `./matlab_data`)
- `--limit`: Anzahl Trajektorien (default: alle)
- `--all-segments`: Auch Segmente exportieren (default: nur Bahnen)

**Output:**
- `matlab_data/trajectories.mat` - MATLAB-Daten mit Trajektorien und Embeddings
- `matlab_data/metadata.csv` - Metadaten (Duration, Length, etc.)

### Schritt 2: DTW-Analyse in MATLAB

Öffne MATLAB und führe aus:

```matlab
cd /path/to/matlab_analysis

% Hauptanalyse ausführen
dtw_baseline_analysis
```

**Das Skript:**
1. Lädt die exportierten Daten
2. Berechnet DTW-Distanz-Matrix (N×N)
3. Berechnet Embedding-Cosine-Distanzen
4. Vergleicht DTW vs Embeddings (Korrelation, Precision@K)
5. Erstellt Visualisierungen
6. Speichert Ergebnisse

**Output:**
- `dtw_baseline_results.mat` - Alle Distanz-Matrizen und Metriken
- `dtw_vs_embedding_scatter.png` - Scatter Plot DTW vs Embeddings
- `distance_distributions.png` - Verteilungen beider Distanzen
- `precision_at_k_distribution.png` - Ranking-Übereinstimmung
- `distance_comparison.csv` - CSV für weitere Analysen

### Schritt 3 (Optional): Detailanalyse einzelner Queries

```matlab
% Analysiere Query #5
analyze_specific_query(5, ...
    '../backend/scripts/matlab_data/trajectories.mat', ...
    'dtw_baseline_results.mat');
```

**Zeigt:**
- Top-K ähnlichste Trajektorien nach DTW
- Top-K ähnlichste Trajektorien nach Embeddings
- Visualisierung der Trajektorien
- DTW Warping Paths

---

## 📊 Erwartete Ergebnisse

### Interpretation der Metriken

#### **Spearman Correlation (ρ)**
Misst Ranking-Korrelation zwischen DTW und Embeddings:
- **ρ > 0.8**: Starke Korrelation → Embeddings approximieren DTW sehr gut
- **ρ = 0.6-0.8**: Moderate Korrelation → Embeddings fangen Haupttrends ein
- **ρ = 0.4-0.6**: Schwache Korrelation → Embeddings unterscheiden sich
- **ρ < 0.4**: Keine Korrelation → Embeddings messen etwas anderes

#### **Precision@K**
Wie viele DTW-Top-K sind auch in Embedding-Top-K?
- **P@K > 0.7**: Hohe Übereinstimmung → Embeddings für Retrieval geeignet
- **P@K = 0.4-0.7**: Moderate Übereinstimmung → Embeddings brauchbar
- **P@K < 0.4**: Niedrige Übereinstimmung → Embeddings nicht optimal

### Mögliche Szenarien

**Szenario 1: Hohe Korrelation (ρ > 0.8, P@K > 0.7)**
- ✅ Embeddings sind gute Approximation für DTW
- ✅ Schnellere Suche ohne Qualitätsverlust
- 💡 **Interpretation:** Embeddings lernen DTW-ähnliche Distanzmetrik

**Szenario 2: Moderate Korrelation (ρ = 0.5-0.7)**
- ⚠️ Embeddings fangen Hauptähnlichkeiten ein, aber mit Unterschieden
- 💡 **Hypothese:** Embeddings sind robuster gegen Zeitverschiebungen
- 💡 **Nächster Schritt:** Analysiere, welche Paare unterschiedlich gerankt werden

**Szenario 3: Niedrige Korrelation (ρ < 0.5)**
- ❌ Embeddings und DTW messen sehr unterschiedliche Ähnlichkeit
- 💡 **Hypothese:** Embeddings sind eher "semantisch" (Bewegungstyp), DTW eher "exakt"
- 💡 **Nächster Schritt:** Untersuche, ob Embeddings andere nützliche Ähnlichkeit finden

---

## ⚙️ Konfiguration

### DTW-Parameter in `dtw_baseline_analysis.m`

```matlab
dtw_options = struct();
dtw_options.normalize = true;              % Z-Score Normalisierung
dtw_options.use_constrained_dtw = true;    % Sakoe-Chiba Band
dtw_options.window_size = 0.15;            % 15% Window
dtw_options.joint_weights = [1, 1, 1, 1, 1, 1];  % Gleiche Gewichte
```

**Empfehlungen:**
- `normalize = true`: Wichtig für Trajektorien mit unterschiedlichen Skalen
- `window_size = 0.10-0.20`: Verhindert zu extreme Warpings
- `joint_weights`: Setze höhere Gewichte für wichtigere Joints (z.B. J1-J3)

### Performance

**Laufzeit:**
- 100 Trajektorien: ~2-5 Minuten
- 500 Trajektorien: ~30-60 Minuten
- 1000 Trajektorien: ~2-4 Stunden

**Tipp:** Starte mit `--limit 50` für schnelle Tests!

---

## 🔬 Weiterführende Analysen

### 1. Per-Joint DTW

Welches Joint trägt am meisten zur Ähnlichkeit bei?

```matlab
% In compute_multivariate_dtw.m:
% Setze joint_weights = [1, 0, 0, 0, 0, 0] für nur Joint 1
% Wiederhole für alle Joints
```

### 2. DTW-Varianten testen

- **Derivative DTW (DDTW)**: Vergleicht Änderungsraten
  ```matlab
  % Berechne Ableitungen:
  traj_A_deriv = diff(traj_A);
  ```

- **Weighted DTW**: Unterschiedliche Wichtigkeit verschiedener Zeitpunkte

### 3. Hybrid-Ansatz

Kombiniere DTW + Embeddings:

```matlab
% Pre-filter mit Embeddings (schnell)
% Re-rank Top-100 mit DTW (langsam aber präzise)
```

---

## 🐛 Troubleshooting

### Problem: "Data file not found"
**Lösung:** Führe zuerst `export_trajectories_for_matlab.py` aus

### Problem: MATLAB out of memory
**Lösung:**
- Reduziere `--limit` beim Export
- Oder berechne DTW-Matrix blockweise:
  ```matlab
  for i = 1:100:n_traj
      % Berechne nur Block [i:i+100, :]
  end
  ```

### Problem: DTW dauert zu lange
**Lösung:**
- Setze `window_size` kleiner (z.B. 0.10)
- Verwende `use_constrained_dtw = true`
- Oder verwende FastDTW (externe Library)

---

## 📝 Nächste Schritte

Nach der Baseline-Analyse:

1. **Wenn DTW ≈ Embeddings** (ρ > 0.8):
   - ✅ Embeddings sind validiert
   - Fokus auf Geschwindigkeits-Optimierung

2. **Wenn DTW ≠ Embeddings** (ρ < 0.6):
   - Untersuche Unterschiede qualitativ
   - Frage: Welche Metrik ist "besser" für euren Use-Case?
   - Eventuell: DTW-informiertes Embedding-Training

3. **Hybrid-System**:
   - Embedding-basiertes Pre-Filtering (schnell)
   - DTW Re-Ranking für Top-K (präzise)

---

## 📚 Referenzen

- **DTW**: Sakoe & Chiba (1978) - "Dynamic programming algorithm optimization for spoken word recognition"
- **Multivariate DTW**: Shokoohi-Yekta et al. (2017) - "Generalizing DTW to the multi-dimensional case"
- **Sakoe-Chiba Band**: Ratanamahatana & Keogh (2004) - "Everything you know about DTW is wrong"

---

## 💬 Support

Bei Fragen oder Problemen:
1. Check das Logfile: MATLAB sollte detaillierte Progress-Ausgaben zeigen
2. Prüfe Datenqualität: `metadata.csv` öffnen und checken
3. Visualisiere einzelne Queries mit `analyze_specific_query.m`

---

**Viel Erfolg mit der Baseline! 🚀**
