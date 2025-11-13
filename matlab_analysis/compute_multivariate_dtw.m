function distance = compute_multivariate_dtw(traj_A, traj_B, options)
% COMPUTE_MULTIVARIATE_DTW - Berechnet DTW für 6D Joint-Trajektorien
%
% Syntax:
%   distance = compute_multivariate_dtw(traj_A, traj_B, options)
%
% Inputs:
%   traj_A  - (n x 6) Matrix: Joint-Trajektorie A
%   traj_B  - (m x 6) Matrix: Joint-Trajektorie B
%   options - Struct mit Optionen:
%             .normalize (bool): Z-Score Normalisierung
%             .use_constrained_dtw (bool): Sakoe-Chiba Band
%             .window_size (double): Band-Breite als Anteil (0-1)
%             .joint_weights (vector): Gewichte für Joints [1x6]
%
% Outputs:
%   distance - DTW-Distanz (skalarer Wert)
%
% Algorithmus:
%   1. Optional: Normalisierung (Z-Score pro Joint)
%   2. Berechne Distanz-Matrix zwischen allen Punkten
%   3. DTW Dynamic Programming mit optionalem Sakoe-Chiba Band
%   4. Rückgabe: Minimale Warping-Distanz

%% Parameter extrahieren
normalize = options.normalize;
use_constrained = options.use_constrained_dtw;
window_size = options.window_size;
joint_weights = options.joint_weights(:)';  % Row vector

n = size(traj_A, 1);
m = size(traj_B, 1);

%% 1. Normalisierung (optional)
if normalize
    % Z-Score Normalisierung für jedes Joint separat
    traj_A = (traj_A - mean(traj_A, 1)) ./ (std(traj_A, 0, 1) + 1e-8);
    traj_B = (traj_B - mean(traj_B, 1)) ./ (std(traj_B, 0, 1) + 1e-8);
end

%% 2. Distanz-Matrix berechnen
% D(i,j) = gewichtete euklidische Distanz zwischen traj_A(i,:) und traj_B(j,:)

% Sakoe-Chiba Band definieren
if use_constrained
    band_width = max(round(max(n, m) * window_size), 1);
else
    band_width = max(n, m);  % Kein Constraint
end

%% 3. DTW Dynamic Programming
% Initialisierung
DTW = inf(n+1, m+1);
DTW(1, 1) = 0;

% DP mit Sakoe-Chiba Constraint
for i = 1:n
    for j = max(1, i - band_width):min(m, i + band_width)

        % Gewichtete euklidische Distanz für dieses Punkt-Paar
        diff = traj_A(i, :) - traj_B(j, :);
        weighted_diff = sqrt(joint_weights) .* diff;  % Element-wise weights
        point_distance = norm(weighted_diff);  % L2 norm

        % DTW-Rekursion
        cost = point_distance;
        DTW(i+1, j+1) = cost + min([...
            DTW(i, j+1), ...    % Insertion
            DTW(i+1, j), ...    % Deletion
            DTW(i, j) ...       % Match
        ]);
    end
end

% Finale DTW-Distanz
distance = DTW(n+1, m+1);

% Normalisierung auf Pfadlänge (optional)
% distance = distance / (n + m);  % Uncomment für path-normalized distance

end
