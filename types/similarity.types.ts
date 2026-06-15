// types/similarity.types.ts

export interface EmbeddingSimilarityParams {
  modes?: string[];
  weights?: {
    joint: number;
    position: number;
    orientation: number;
    velocity: number;
    metadata: number;
  };
  limit: number;
  prefilter_features?: string[];
  stage2_active?: boolean;
  dtw_mode?: 'position' | 'joint';
  metric?: 'sidtw' | 'qdtw'; // NEU
}

export interface EmbeddingModeScore {
  rank: number;
  distance: number;
  rrf_contribution: number;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  progress_percent: number;
  error?: string;
}

export interface MetadataStats {
  total_trajs: number;
  trajs_with_metadata: number;
  missing_metadata: number;
  coverage_percent: number;
}

export interface AvailableDate {
  date: string;
}

export interface MetadataCalculationRequest {
  mode: 'all_missing' | 'single' | 'timerange';
  traj_id?: string;
  start_time?: string;
  end_time?: string;
  duplicate_handling?: string;
  batch_size?: number;
}

export interface MetadataCalculationResponse {
  task_id: string;
  status: string;
  message: string;
  estimated_duration_minutes?: number;
}

export interface EmbeddingSimilarityResult {
  seg_id: string;
  traj_id?: string;
  rrf_score: number;
  rank: number;
  // Stage 2 fields (optional — only present when stage2_active=true)
  rank_stage1?: number;
  rank_stage2?: number;
  dtw_distance?: number;
  mode_scores: {
    joint?: EmbeddingModeScore;
    position?: EmbeddingModeScore;
    orientation?: EmbeddingModeScore;
    velocity?: EmbeddingModeScore;
    acceleration?: EmbeddingModeScore;
    metadata?: EmbeddingModeScore;
  };
  features?: {
    seg_id: string;
    traj_id: string;
    duration: number;
    weight?: number;
    length: number;
    movement_type?: string;
    mean_vel?: number;
    max_vel?: number;
    std_vel?: number;
    mean_accel?: number;
    max_accel?: number;
    min_accel?: number;
    std_accel?: number;
    min_distance?: number; // NEU
    mean_distance?: number; // NEU
    max_distance?: number; // NEU
    position_x?: number;
    position_y?: number;
    position_z?: number;
  };
}

export interface TrajSimilarityResponse {
  target: string;
  results: EmbeddingSimilarityResult[];
  metadata: {
    modes: string[];
    weights: {
      joint: number;
      position: number;
      orientation: number;
      velocity: number;
      acceleration: number;
      metadata: number;
    };
  };
}

export interface SimilarityResult {
  traj_id?: string;
  seg_id?: string;
  similarity_score: number;
  // Stage 2 fields
  rank_stage1?: number;
  rank_stage2?: number;
  dtw_distance?: number;
  // Features
  duration?: number;
  weight?: number;
  length?: number;
  movement_type?: string;
  mean_vel?: number;
  max_vel?: number;
  std_vel?: number;
  mean_accel?: number;
  max_accel?: number;
  min_accel?: number;
  std_accel?: number;
  min_distance?: number; // NEU
  mean_distance?: number; // NEU
  max_distance?: number; // NEU
  position_x?: number;
  position_y?: number;
  position_z?: number;
}

export interface TargetFeatures {
  seg_id: string;
  traj_id: string;
  duration?: number;
  weight?: number;
  length?: number;
  movement_type?: string;
  mean_vel?: number;
  max_vel?: number;
  std_vel?: number;
  mean_accel?: number;
  max_accel?: number;
  min_accel?: number;
  std_accel?: number;
  min_distance?: number; // NEU
  mean_distance?: number; // NEU
  max_distance?: number; // NEU
  position_x?: number;
  position_y?: number;
  position_z?: number;
}

export interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  results: SimilarityResult[];
  conformal_interval?: ConformalInterval | null;
}

export interface SearchTiming {
  stage1_ms: number;
  data_loading_ms?: number;
  stage2_ms?: number;
  total_ms: number;
}

export interface HierarchicalSimilarityResponse {
  target_id: string;
  target_traj_id: string;
  target_traj_features?: TargetFeatures;
  modes: string[];
  weights: {
    joint: number;
    position: number;
    orientation: number;
    velocity: number;
    acceleration: number;
    metadata: number;
  };
  metric: 'sidtw' | 'qdtw';
  traj_similarity: TrajSimilarityResponse;
  segment_similarity: {
    target_segment: string;
    target_segment_features?: TargetFeatures;
    similar_segments: {
      target: string;
      results: EmbeddingSimilarityResult[];
      metadata: {
        modes: string[];
        weights: {
          joint: number;
          position: number;
          orientation: number;
          velocity: number;
          acceleration: number;
          metadata: number;
        };
      };
    };
    conformal_interval?: ConformalInterval | null; // NEU
  }[];
  metadata: {
    target_segments_count: number;
    segments_processed: number;
  };
  // Stage 2
  stage2_active: boolean;
  stage2_dtw_mode?: 'position' | 'joint';
  timing?: SearchTiming;
  conformal_interval?: ConformalInterval | null; // NEU — Trajektorie-Ebene
}

export interface PrognosisValues {
  simple: number | null;
  weighted: number | null;
}

export interface PrognosisFields {
  min: PrognosisValues;
  mean: PrognosisValues;
  max: PrognosisValues;
}

export interface PrognosisResult {
  direct: PrognosisFields;
  decomposed: PrognosisFields;
  groundTruth: {
    min: number | null;
    mean: number | null;
    max: number | null;
  };
  // Alte confidence bleibt vorerst für Stage 1 (ohne Stage 2)
  confidence: {
    direct: number | null;
    decomposed: {
      weightedMean: number | null;
      minimum: number | null;
      harmonicMean: number | null;
    };
  };
  // NEU — nur befüllt wenn stage2Active === true
  conformalInterval?: ConformalInterval | null;
}

export interface ConformalInterval {
  p_hat: number; // inverse-DTW gewichtete Prognose [mm]
  low: number; // untere Intervallgrenze [mm]
  high: number; // obere Intervallgrenze [mm]
  coverage: number; // Ziel-Coverage z.B. 0.90
  n_segments?: number; // Anzahl Segmente (nur auf Trajektorie-Ebene)
  n?: number; // Anzahl Nachbarn (nur auf Segment-Ebene)
  sigma?: number; // lokaler Spread d_min × std(perf) — optional für Debug
}
