// types/similarity.types.ts

export interface EmbeddingSimilarityParams {
  modes?: string[]; // ['joint', 'position', 'orientation']
  weights?: {
    joint: number;
    position: number;
    orientation: number;
  };
  limit: number; // Anzahl Ergebnisse (für Bahnen UND Segmente)
}

export interface EmbeddingModeScore {
  rank: number;
  distance: number;
  rrf_contribution: number;
}

export interface TaskStatus {
  task_id: string;
  status: string; // "running" | "completed" | "failed"
  progress_percent: number;
  error?: string;
}

export interface MetadataStats {
  total_bahns: number;
  bahns_with_metadata: number;
  missing_metadata: number;
  coverage_percent: number;
}

export interface AvailableDate {
  date: string;
}

export interface MetadataCalculationRequest {
  mode: 'all_missing' | 'single' | 'timerange';
  bahn_id?: string;
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
  segment_id: string;
  bahn_id?: string;
  rrf_score: number;
  rank: number;
  mode_scores: {
    joint?: EmbeddingModeScore;
    position?: EmbeddingModeScore;
    orientation?: EmbeddingModeScore;
  };
  features?: {
    segment_id: string;
    bahn_id: string;
    duration: number;
    length: number;
    median_twist_ist: number;
    median_acceleration_ist: number;
    movement_type: string;
  };
}

export interface BahnSimilarityResponse {
  target: string;
  results: EmbeddingSimilarityResult[];
  metadata: {
    modes: string[];
    weights: {
      joint: number;
      position: number;
      orientation: number;
    };
  };
}

export interface SimilarityResult {
  bahn_id?: string;
  segment_id?: string;
  similarity_score: number;
  duration?: number;
  weight?: number;
  length?: number;
  movement_type?: string;
  median_twist_ist?: number;
  median_acceleration_ist?: number;
  sidtw_average_distance?: number;
  meta_value?: number;
}

export interface TargetFeatures {
  segment_id: string;
  bahn_id: string;
  duration?: number;
  length?: number;
  median_twist_ist?: number;
  median_acceleration_ist?: number;
  movement_type?: string;
}

export interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  results: SimilarityResult[];
}

export interface HierarchicalSimilarityResponse {
  target_id: string;
  target_bahn_id: string;
  target_bahn_features?: {
    // ✅ NEU!
    segment_id: string;
    bahn_id: string;
    duration?: number;
    length?: number;
    median_twist_ist?: number;
    median_acceleration_ist?: number;
    movement_type?: string;
  };
  modes: string[];
  weights: {
    joint: number;
    position: number;
    orientation: number;
  };
  bahn_similarity: BahnSimilarityResponse;
  segment_similarity: {
    target_segment: string;
    target_segment_features?: {
      // ✅ NEU!
      segment_id: string;
      bahn_id: string;
      duration?: number;
      length?: number;
      median_twist_ist?: number;
      median_acceleration_ist?: number;
      movement_type?: string;
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
        };
      };
    };
  }[];
  metadata: {
    target_segments_count: number;
    segments_processed: number;
  };
}
