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
    mean_vel_act?: number;
    max_vel_act?: number;
    std_vel_act?: number;
    mean_accel_act?: number;
    max_accel_act?: number;
    min_accel_act?: number;
    std_accel_act?: number;
    sidtw_average_distance?: number;
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
  mean_vel_act?: number;
  max_vel_act?: number;
  std_vel_act?: number;
  mean_accel_act?: number;
  max_accel_act?: number;
  min_accel_act?: number;
  std_accel_act?: number;
  sidtw_average_distance?: number;
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
  mean_vel_act?: number;
  max_vel_act?: number;
  std_vel_act?: number;
  mean_accel_act?: number;
  max_accel_act?: number;
  min_accel_act?: number;
  std_accel_act?: number;
  sidtw_average_distance?: number;
  position_x?: number;
  position_y?: number;
  position_z?: number;
}

export interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  results: SimilarityResult[];
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
  target_traj_features?: {
    seg_id: string;
    traj_id: string;
    duration?: number;
    weight?: number;
    length?: number;
    movement_type?: string;
    mean_vel_act?: number;
    max_vel_act?: number;
    std_vel_act?: number;
    mean_accel_act?: number;
    max_accel_act?: number;
    min_accel_act?: number;
    std_accel_act?: number;
    sidtw_average_distance?: number;
    position_x?: number;
    position_y?: number;
    position_z?: number;
  };
  modes: string[];
  weights: {
    joint: number;
    position: number;
    orientation: number;
    velocity: number;
    acceleration: number;
    metadata: number;
  };
  traj_similarity: TrajSimilarityResponse;
  segment_similarity: {
    target_segment: string;
    target_segment_features?: {
      seg_id: string;
      traj_id: string;
      duration?: number;
      weight?: number;
      length?: number;
      movement_type?: string;
      mean_vel_act?: number;
      max_vel_act?: number;
      std_vel_act?: number;
      mean_accel_act?: number;
      max_accel_act?: number;
      min_accel_act?: number;
      std_accel_act?: number;
      sidtw_average_distance?: number;
      position_x?: number;
      position_y?: number;
      position_z?: number;
    };
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
  }[];
  metadata: {
    target_segments_count: number;
    segments_processed: number;
  };
  // Stage 2 response fields
  stage2_active: boolean;
  stage2_dtw_mode?: 'position' | 'joint';
  timing?: SearchTiming;
}
