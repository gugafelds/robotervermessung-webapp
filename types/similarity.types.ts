// types/similarity.types.ts

// ═══════════════════════════════════════════════════════════════════════════
// Metadata
// ═══════════════════════════════════════════════════════════════════════════

export interface MetadataStats {
  total_trajs: number;
  trajs_with_metadata: number;
  missing_metadata: number;
  coverage_percent: number;
}

export interface AvailableDate {
  date: string;
  count: number;
}

export interface MetadataCalculationRequest {
  mode: string;
  duplicate_handling?: string;
  batch_size?: number;
  traj_id?: string;
  start_time?: string;
  end_time?: string;
}

export interface MetadataCalculationResponse {
  task_id?: string;
  status?: string;
}

export interface TaskStatus {
  status: 'pending' | 'running' | 'completed' | 'failed';
  error?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// Search params
// ═══════════════════════════════════════════════════════════════════════════

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
  metric?: 'sidtw' | 'qdtw';
  prognosis_active?: boolean;
  // calibration_tag is derived from include_tags in similarity.service.ts
  coverage?: number;
  include_tags?: string[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Raw API response types (what the backend returns)
// ═══════════════════════════════════════════════════════════════════════════

export interface EmbeddingModeScore {
  rank: number;
  distance: number;
  rrf_contribution: number;
}

export interface EmbeddingSimilarityResult {
  seg_id: string;
  traj_id?: string;
  rrf_score: number;
  rank: number;
  rank_stage1?: number;
  rank_stage2?: number;
  dtw_distance?: number;
  similarity_score?: number;
  mode_scores: {
    joint?: EmbeddingModeScore;
    position?: EmbeddingModeScore;
    orientation?: EmbeddingModeScore;
    velocity?: EmbeddingModeScore;
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
    min_distance?: number;
    mean_distance?: number;
    max_distance?: number;
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
    weights: Record<string, number>;
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// Conformal interval
// ═══════════════════════════════════════════════════════════════════════════

export interface CalibrationMismatch {
  warning: string;
  requested_k?: number;
  used_k?: number;
  requested_modes?: string;
  used_modes?: string;
  requested_tag?: string;
  used_tag?: string;
}

export interface MatchQuality {
  expected_error_mm: number;
  tier: 'excellent' | 'good' | 'moderate' | 'poor';
  bucket: number;
  n_buckets: number;
  n_samples: number;
  calibration_tag_used: string;
}

export interface ConformalInterval {
  p_hat: number;
  low: number;
  high: number;
  sigma: number;
  coverage: number;
  n_segments?: number;
  strategy?: string;
  calibration_mismatch?: CalibrationMismatch | null;
  match_quality?: MatchQuality | null;
}

// ═══════════════════════════════════════════════════════════════════════════
// Prognosis
// ═══════════════════════════════════════════════════════════════════════════

export interface SegmentPrognosis {
  seg_id: string;
  p_hat: number | null;
  sigma: number | null;
  n_neighbors: number | null;
  d_min: number | null;
  d_max: number | null;
  d_normalized: number | null;
  query_path_length: number | null;
}

export interface TrajectoryPrognosis {
  p_hat: number;
  sigma: number;
  n_segments?: number; // decomposed only
  n_neighbors?: number; // direct / stage1 only
  d_min?: number | null;
  d_max?: number | null;
  d_normalized?: number | null;
}

export interface Prognosis {
  feature: string;
  stage: 'stage2_dtw' | 'stage1_rrf';
  decomposed: TrajectoryPrognosis | null;
  direct: TrajectoryPrognosis | null;
  decomposed_conformal_interval: ConformalInterval | null;
  direct_conformal_interval: ConformalInterval | null; // Stage 2 only
  stage1_conformal_interval: ConformalInterval | null; // Stage 1 only
  segments: SegmentPrognosis[];
}

// ═══════════════════════════════════════════════════════════════════════════
// Frontend display types
// ═══════════════════════════════════════════════════════════════════════════

export interface SimilarityResult {
  traj_id?: string;
  seg_id?: string;
  similarity_score: number;
  rank_stage1?: number;
  rank_stage2?: number;
  dtw_distance?: number;
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
  min_distance?: number;
  mean_distance?: number;
  max_distance?: number;
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
  min_distance?: number;
  mean_distance?: number;
  max_distance?: number;
  position_x?: number;
  position_y?: number;
  position_z?: number;
}

export interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  similar_segments: TrajSimilarityResponse;
  conformal_interval?: ConformalInterval | null;
}

export interface SearchTiming {
  stage1_ms?: number;
  stage2_ms?: number;
  total_ms?: number;
  data_loading_ms?: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// Full API response
// ═══════════════════════════════════════════════════════════════════════════

export interface HierarchicalSimilarityResponse {
  target_id: string;
  target_traj_id: string;
  target_traj_features?: TargetFeatures;
  modes: string[];
  weights: Record<string, number>;
  metric: 'sidtw' | 'qdtw';
  traj_similarity: TrajSimilarityResponse;
  segment_similarity: {
    target_segment: string;
    target_segment_features?: TargetFeatures;
    similar_segments: {
      target: string;
      results: EmbeddingSimilarityResult[];
      metadata: { modes: string[]; weights: Record<string, number> };
    };
  }[];
  metadata: {
    target_segments_count: number;
    segments_processed: number;
  };
  stage2_active: boolean;
  stage2_dtw_mode?: 'position' | 'joint';
  timing?: SearchTiming;
  prognosis?: Prognosis | null;
}
