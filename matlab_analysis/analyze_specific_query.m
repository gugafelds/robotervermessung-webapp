function analyze_specific_query(query_id, data_path, results_path)
% ANALYZE_SPECIFIC_QUERY - Detaillierte Analyse einer spezifischen Query
%
% Zeigt für eine Query-Trajektorie:
%   - Top-K nach DTW
%   - Top-K nach Embeddings
%   - Visualisierung der ähnlichsten Trajektorien
%   - Warping-Pfad für beste Matches
%
% Syntax:
%   analyze_specific_query(5, 'trajectories.mat', 'dtw_baseline_results.mat')
%
% Inputs:
%   query_id     - Index der Query-Trajektorie (1-based)
%   data_path    - Pfad zur trajectories.mat
%   results_path - Pfad zur dtw_baseline_results.mat

%% Daten laden
fprintf('Lade Daten für Query #%d...\n', query_id);

data = load(data_path);
results = load(results_path);

n_traj = data.n_trajectories;
segment_ids = data.segment_ids;

if query_id < 1 || query_id > n_traj
    error('Invalid query_id! Must be between 1 and %d', n_traj);
end

query_segment_id = segment_ids{query_id};
query_traj = data.trajectories{query_id};

fprintf('  Query Segment: %s\n', query_segment_id);
fprintf('  Query Length: %d samples\n', size(query_traj, 1));
fprintf('\n');

%% Top-K nach DTW
k = 5;

dtw_distances = results.dtw_distance_matrix(query_id, :);
[dtw_sorted, dtw_idx] = sort(dtw_distances);
dtw_top_k = dtw_idx(2:k+1);  % Exclude self

fprintf('Top-%d nach DTW:\n', k);
for i = 1:k
    idx = dtw_top_k(i);
    fprintf('  %d. %s (DTW=%.4f)\n', i, segment_ids{idx}, dtw_sorted(i+1));
end
fprintf('\n');

%% Top-K nach Embeddings
emb_distances = results.joint_embedding_distances(query_id, :);
[emb_sorted, emb_idx] = sort(emb_distances);
emb_top_k = emb_idx(2:k+1);  % Exclude self

fprintf('Top-%d nach Joint Embeddings:\n', k);
for i = 1:k
    idx = emb_top_k(i);
    fprintf('  %d. %s (Cosine Dist=%.4f)\n', i, segment_ids{idx}, emb_sorted(i+1));
end
fprintf('\n');

%% Übereinstimmung
overlap = intersect(dtw_top_k, emb_top_k);
fprintf('Übereinstimmung: %d/%d Trajektorien in beiden Top-%d\n', ...
    length(overlap), k, k);
fprintf('\n');

%% Visualisierung
figure('Position', [100, 100, 1400, 900]);

% Plot 1: Query-Trajektorie
subplot(2, 3, 1);
plot_joint_trajectory(query_traj, sprintf('Query: %s', query_segment_id));

% Plot 2-4: Top-3 nach DTW
for i = 1:3
    subplot(2, 3, i+1);
    idx = dtw_top_k(i);
    match_traj = data.trajectories{idx};
    plot_joint_trajectory(match_traj, ...
        sprintf('DTW #%d: %s (d=%.3f)', i, segment_ids{idx}, dtw_sorted(i+1)));
end

% Plot 5-6: Top-2 nach Embeddings (die NICHT in DTW Top-3 sind)
unique_emb = setdiff(emb_top_k(1:3), dtw_top_k(1:3));
for i = 1:min(2, length(unique_emb))
    subplot(2, 3, 4+i);
    idx = unique_emb(i);
    match_traj = data.trajectories{idx};

    % Finde Position in emb_top_k
    pos = find(emb_top_k == idx);

    plot_joint_trajectory(match_traj, ...
        sprintf('Emb #%d: %s (d=%.3f)', pos, segment_ids{idx}, ...
        results.joint_embedding_distances(query_id, idx)));
end

sgtitle(sprintf('Query #%d: %s - DTW vs Embedding Matches', query_id, query_segment_id), ...
    'FontWeight', 'bold', 'FontSize', 14);

%% Warping Path Visualization
figure('Position', [120, 120, 1200, 400]);

for i = 1:3
    subplot(1, 3, i);

    idx = dtw_top_k(i);
    match_traj = data.trajectories{idx};

    % Berechne DTW mit Warping Path
    [dist, warping_path] = dtw_with_path(query_traj, match_traj);

    % Plot Warping Path
    plot(warping_path(:, 1), warping_path(:, 2), 'b-', 'LineWidth', 1);
    xlabel('Query Index');
    ylabel('Match Index');
    title(sprintf('DTW #%d: %s\nWarping Path (d=%.3f)', ...
        i, segment_ids{idx}, dist));
    grid on;
    axis equal tight;
end

sgtitle('DTW Warping Paths', 'FontWeight', 'bold', 'FontSize', 14);

fprintf('✅ Visualisierung erstellt\n');

end


%% Helper Functions
function plot_joint_trajectory(traj, title_str)
    % Plot alle 6 Joints in einem Plot

    n = size(traj, 1);
    t = 1:n;

    hold on;
    colors = lines(6);
    for j = 1:6
        plot(t, traj(:, j), 'Color', colors(j, :), 'LineWidth', 1.5);
    end

    xlabel('Sample');
    ylabel('Joint Angle');
    title(title_str, 'Interpreter', 'none', 'FontSize', 10);
    legend({'J1', 'J2', 'J3', 'J4', 'J5', 'J6'}, 'Location', 'best', 'FontSize', 8);
    grid on;
end


function [distance, path] = dtw_with_path(traj_A, traj_B)
    % Simplified DTW mit Path Extraction

    n = size(traj_A, 1);
    m = size(traj_B, 1);

    % Distance matrix
    D = zeros(n, m);
    for i = 1:n
        for j = 1:m
            D(i, j) = norm(traj_A(i, :) - traj_B(j, :));
        end
    end

    % DTW
    DTW = inf(n+1, m+1);
    DTW(1, 1) = 0;

    for i = 1:n
        for j = 1:m
            cost = D(i, j);
            DTW(i+1, j+1) = cost + min([DTW(i, j+1), DTW(i+1, j), DTW(i, j)]);
        end
    end

    distance = DTW(n+1, m+1);

    % Backtrack path
    path = zeros(n+m, 2);
    i = n; j = m;
    idx = 1;

    while i > 0 && j > 0
        path(idx, :) = [i, j];
        idx = idx + 1;

        [~, direction] = min([DTW(i, j+1), DTW(i+1, j), DTW(i, j)]);

        if direction == 1
            i = i - 1;
        elseif direction == 2
            j = j - 1;
        else
            i = i - 1;
            j = j - 1;
        end
    end

    path = path(1:idx-1, :);
    path = flipud(path);
end
