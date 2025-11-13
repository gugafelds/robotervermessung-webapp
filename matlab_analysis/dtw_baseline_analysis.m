% DTW Baseline Analysis für Roboter-Trajektorien
% ================================================
%
% Dieses Skript berechnet DTW-Distanzen zwischen Joint-Trajektorien
% und vergleicht sie mit den Embedding-basierten Distanzen
%
% Autor: Claude
% Datum: 2025-11-13

clear all;
close all;
clc;

%% ========================================================================
%% 1. KONFIGURATION
%% ========================================================================

% Pfad zu den exportierten Daten
data_path = '../backend/scripts/matlab_data/trajectories.mat';

% Optionen für DTW
dtw_options = struct();
dtw_options.normalize = true;           % Z-Score Normalisierung pro Joint
dtw_options.use_constrained_dtw = true; % Sakoe-Chiba Band
dtw_options.window_size = 0.15;         % 15% der Trajektorienlänge
dtw_options.joint_weights = [1, 1, 1, 1, 1, 1]; % Gleiche Gewichte für alle Joints

% Analyse-Optionen
n_test_pairs = 100;      % Anzahl zufälliger Paare für Analyse
n_neighbors = 10;        % Top-K ähnlichste Trajektorien
save_results = true;     % Ergebnisse speichern?

fprintf('=======================================================\n');
fprintf('DTW BASELINE ANALYSIS\n');
fprintf('=======================================================\n\n');

%% ========================================================================
%% 2. DATEN LADEN
%% ========================================================================

fprintf('[1/6] Lade Daten...\n');

if ~exist(data_path, 'file')
    error('Data file not found: %s\nPlease run export_trajectories_for_matlab.py first!', data_path);
end

data = load(data_path);

n_traj = data.n_trajectories;
segment_ids = data.segment_ids;
trajectories = data.trajectories;
joint_embeddings = data.joint_embeddings;
position_embeddings = data.position_embeddings;

fprintf('  ✓ Loaded %d trajectories\n', n_traj);
fprintf('  ✓ Segment IDs: %s ... %s\n', segment_ids{1}, segment_ids{end});
fprintf('  ✓ Joint embeddings: %d x %d\n', size(joint_embeddings));
fprintf('\n');

%% ========================================================================
%% 3. DTW-DISTANZ-MATRIX BERECHNEN
%% ========================================================================

fprintf('[2/6] Berechne DTW-Distanz-Matrix...\n');
fprintf('  (Das kann einige Minuten dauern für %d Trajektorien)\n\n', n_traj);

% Pre-allocate
dtw_distance_matrix = zeros(n_traj, n_traj);

% Progress bar
h = waitbar(0, 'Computing DTW distances...');

tic;
for i = 1:n_traj
    for j = i:n_traj  % Nur obere Dreiecks-Matrix (symmetrisch)

        if i == j
            dtw_distance_matrix(i, j) = 0;
        else
            % Berechne DTW
            dist = compute_multivariate_dtw(...
                trajectories{i}, ...
                trajectories{j}, ...
                dtw_options);

            dtw_distance_matrix(i, j) = dist;
            dtw_distance_matrix(j, i) = dist;  % Symmetrie
        end
    end

    % Update progress
    if mod(i, 5) == 0
        waitbar(i / n_traj, h, sprintf('Computing DTW: %d/%d trajectories', i, n_traj));
    end
end

close(h);
elapsed_time = toc;

fprintf('  ✓ DTW-Matrix berechnet in %.2f Sekunden\n', elapsed_time);
fprintf('  ✓ Durchschnittliche Zeit pro Paar: %.3f ms\n', elapsed_time * 1000 / (n_traj * (n_traj-1) / 2));
fprintf('\n');

%% ========================================================================
%% 4. EMBEDDING-DISTANZ-MATRIX BERECHNEN (COSINE)
%% ========================================================================

fprintf('[3/6] Berechne Embedding-Distanzen (Cosine)...\n');

% Joint Embedding Cosine Distance
joint_embedding_distances = zeros(n_traj, n_traj);
for i = 1:n_traj
    for j = i+1:n_traj
        % Cosine distance = 1 - cosine similarity
        cos_sim = dot(joint_embeddings(i,:), joint_embeddings(j,:)) / ...
                  (norm(joint_embeddings(i,:)) * norm(joint_embeddings(j,:)));
        joint_embedding_distances(i, j) = 1 - cos_sim;
        joint_embedding_distances(j, i) = joint_embedding_distances(i, j);
    end
end

fprintf('  ✓ Joint Embedding Distanzen berechnet\n\n');

%% ========================================================================
%% 5. VERGLEICH: DTW vs EMBEDDINGS
%% ========================================================================

fprintf('[4/6] Vergleiche DTW mit Embeddings...\n');

% Korrelation zwischen DTW und Embedding-Distanzen
% (nur obere Dreiecksmatrix, ohne Diagonal)
idx_upper = triu(true(n_traj), 1);

dtw_vec = dtw_distance_matrix(idx_upper);
emb_vec = joint_embedding_distances(idx_upper);

% Spearman Correlation (Ranking-basiert)
[rho_spearman, p_spearman] = corr(dtw_vec, emb_vec, 'Type', 'Spearman');

% Pearson Correlation
[rho_pearson, p_pearson] = corr(dtw_vec, emb_vec, 'Type', 'Pearson');

fprintf('  ✓ Spearman Correlation: ρ = %.4f (p = %.4e)\n', rho_spearman, p_spearman);
fprintf('  ✓ Pearson Correlation:  r = %.4f (p = %.4e)\n', rho_pearson, p_pearson);
fprintf('\n');

%% ========================================================================
%% 6. RANKING-VERGLEICH (Precision@K)
%% ========================================================================

fprintf('[5/6] Evaluiere Rankings (Precision@K)...\n');

% Für jede Query: Top-K nach DTW vs Top-K nach Embeddings
precision_at_k = zeros(n_traj, 1);

for query_idx = 1:n_traj

    % DTW: Top-K ähnlichste (kleinste Distanzen)
    [~, dtw_ranking] = sort(dtw_distance_matrix(query_idx, :));
    dtw_top_k = dtw_ranking(2:n_neighbors+1);  % Exclude self

    % Embeddings: Top-K ähnlichste
    [~, emb_ranking] = sort(joint_embedding_distances(query_idx, :));
    emb_top_k = emb_ranking(2:n_neighbors+1);  % Exclude self

    % Precision@K: Wie viele DTW-Top-K sind in Embedding-Top-K?
    overlap = length(intersect(dtw_top_k, emb_top_k));
    precision_at_k(query_idx) = overlap / n_neighbors;
end

mean_precision = mean(precision_at_k);

fprintf('  ✓ Mean Precision@%d: %.4f\n', n_neighbors, mean_precision);
fprintf('    (1.0 = perfekte Übereinstimmung, 0.0 = keine Übereinstimmung)\n');
fprintf('\n');

%% ========================================================================
%% 7. VISUALISIERUNGEN
%% ========================================================================

fprintf('[6/6] Erstelle Visualisierungen...\n');

% Figure 1: DTW vs Embedding Scatter Plot
figure('Position', [100, 100, 800, 600]);
scatter(dtw_vec, emb_vec, 10, 'filled', 'MarkerFaceAlpha', 0.3);
xlabel('DTW Distance');
ylabel('Joint Embedding Cosine Distance');
title(sprintf('DTW vs Embedding Distance (ρ = %.3f)', rho_spearman));
grid on;

% Add regression line
hold on;
p = polyfit(dtw_vec, emb_vec, 1);
x_fit = linspace(min(dtw_vec), max(dtw_vec), 100);
y_fit = polyval(p, x_fit);
plot(x_fit, y_fit, 'r-', 'LineWidth', 2);
legend('Data', 'Linear Fit', 'Location', 'best');

if save_results
    saveas(gcf, 'dtw_vs_embedding_scatter.png');
end

% Figure 2: Distance Distributions
figure('Position', [120, 120, 1000, 400]);

subplot(1, 2, 1);
histogram(dtw_vec, 50, 'Normalization', 'probability');
xlabel('DTW Distance');
ylabel('Probability');
title('DTW Distance Distribution');
grid on;

subplot(1, 2, 2);
histogram(emb_vec, 50, 'Normalization', 'probability');
xlabel('Cosine Distance');
ylabel('Probability');
title('Embedding Distance Distribution');
grid on;

if save_results
    saveas(gcf, 'distance_distributions.png');
end

% Figure 3: Precision@K Distribution
figure('Position', [140, 140, 600, 500]);
histogram(precision_at_k, 20);
xlabel(sprintf('Precision@%d', n_neighbors));
ylabel('Count');
title(sprintf('Ranking Agreement Distribution (Mean = %.3f)', mean_precision));
xline(mean_precision, 'r--', 'LineWidth', 2, 'Label', 'Mean');
grid on;

if save_results
    saveas(gcf, 'precision_at_k_distribution.png');
end

fprintf('  ✓ Visualisierungen erstellt\n\n');

%% ========================================================================
%% 8. ERGEBNISSE ZUSAMMENFASSEN
%% ========================================================================

fprintf('=======================================================\n');
fprintf('ZUSAMMENFASSUNG\n');
fprintf('=======================================================\n');
fprintf('Dataset:\n');
fprintf('  - Anzahl Trajektorien: %d\n', n_traj);
fprintf('  - Durchschnittliche Länge: %.1f samples\n', mean(data.n_samples));
fprintf('\n');
fprintf('DTW Konfiguration:\n');
fprintf('  - Normalisierung: %s\n', string(dtw_options.normalize));
fprintf('  - Constrained DTW: %s (window=%.0f%%)\n', ...
    string(dtw_options.use_constrained_dtw), dtw_options.window_size * 100);
fprintf('\n');
fprintf('Korrelation (DTW ↔ Embeddings):\n');
fprintf('  - Spearman ρ: %.4f ***\n', rho_spearman);
fprintf('  - Pearson r:  %.4f\n', rho_pearson);
fprintf('\n');
fprintf('Ranking-Übereinstimmung:\n');
fprintf('  - Mean Precision@%d: %.4f\n', n_neighbors, mean_precision);
fprintf('\n');
fprintf('Interpretation:\n');
if rho_spearman > 0.8
    fprintf('  → STARKE Korrelation: Embeddings approximieren DTW sehr gut\n');
elseif rho_spearman > 0.6
    fprintf('  → MODERATE Korrelation: Embeddings fangen Haupttrends ein\n');
elseif rho_spearman > 0.4
    fprintf('  → SCHWACHE Korrelation: Embeddings unterscheiden sich deutlich\n');
else
    fprintf('  → KEINE Korrelation: Embeddings messen etwas anderes als DTW\n');
end
fprintf('\n');

if mean_precision > 0.7
    fprintf('  → HOHE Ranking-Übereinstimmung: Embeddings für Retrieval geeignet\n');
elseif mean_precision > 0.4
    fprintf('  → MODERATE Ranking-Übereinstimmung: Embeddings brauchbar\n');
else
    fprintf('  → NIEDRIGE Ranking-Übereinstimmung: Embeddings nicht optimal\n');
end
fprintf('=======================================================\n');

%% ========================================================================
%% 9. ERGEBNISSE SPEICHERN
%% ========================================================================

if save_results
    fprintf('\nSpeichere Ergebnisse...\n');

    results = struct();
    results.dtw_distance_matrix = dtw_distance_matrix;
    results.joint_embedding_distances = joint_embedding_distances;
    results.spearman_rho = rho_spearman;
    results.pearson_r = rho_pearson;
    results.precision_at_k = precision_at_k;
    results.mean_precision = mean_precision;
    results.segment_ids = segment_ids;
    results.dtw_options = dtw_options;
    results.computation_time = elapsed_time;

    save('dtw_baseline_results.mat', '-struct', 'results');
    fprintf('  ✓ Gespeichert: dtw_baseline_results.mat\n');

    % CSV Export für einfache Weiterverarbeitung
    T = table(dtw_vec, emb_vec, 'VariableNames', {'DTW_Distance', 'Embedding_Distance'});
    writetable(T, 'distance_comparison.csv');
    fprintf('  ✓ Gespeichert: distance_comparison.csv\n');
end

fprintf('\n✅ Analyse abgeschlossen!\n\n');
