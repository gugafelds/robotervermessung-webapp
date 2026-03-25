import type {
  EmbeddingSimilarityParams,
  EmbeddingSimilarityResult,
  HierarchicalSimilarityResponse,
  SearchTiming,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

export class SimilarityService {
  private static readonly BASE_URL = '';

  static async searchSimilarityEmbedding(
    targetId: string,
    params: EmbeddingSimilarityParams,
    callbacks: {
      onTrajsFound?: (
        results: SimilarityResult[],
        targetFeatures?: TargetFeatures,
        timing?: SearchTiming,
        stage2Active?: boolean,
        dtwMode?: 'position' | 'joint',
      ) => void;
      onSegmentsFound?: (groups: SegmentGroup[]) => void;
      onError?: (error: string) => void;
    },
  ): Promise<void> {
    try {
      const queryParams = new URLSearchParams();

      if (params.modes && params.modes.length > 0) {
        queryParams.append('modes', params.modes.join(','));
      }

      if (params.weights) {
        queryParams.append('joint_weight', params.weights.joint.toString());
        queryParams.append(
          'position_weight',
          params.weights.position.toString(),
        );
        queryParams.append(
          'orientation_weight',
          params.weights.orientation.toString(),
        );
        queryParams.append(
          'velocity_weight',
          params.weights.velocity.toString(),
        );
        queryParams.append(
          'metadata_weight',
          params.weights.metadata.toString(),
        );
      }

      queryParams.append('limit', params.limit.toString());

      if (params.prefilter_features && params.prefilter_features.length > 0) {
        queryParams.append(
          'prefilter_features',
          params.prefilter_features.join(','),
        );
      }

      if (params.stage2_active !== undefined) {
        queryParams.append('stage2_active', params.stage2_active.toString());
      }
      if (params.dtw_mode) {
        queryParams.append('dtw_mode', params.dtw_mode);
      }

      // Metric Parameter                                                  // NEU
      if (params.metric) {
        // NEU
        queryParams.append('metric', params.metric); // NEU
      } // NEU

      const response = await fetch(
        `${this.BASE_URL}/api/similarity/search/${targetId}?${queryParams.toString()}`,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: HierarchicalSimilarityResponse = await response.json();

      // 1. Target Bahn Features — direkt spreaden, kein manuelles Mapping
      const targetTrajFeatures: TargetFeatures | undefined =
        data.target_traj_features ?? undefined;

      // 2. Traj-Ergebnisse
      if (data.traj_similarity?.results) {
        const trajResults = this.transformEmbeddingResults(
          data.traj_similarity.results,
          'traj',
        );
        callbacks.onTrajsFound?.(
          trajResults,
          targetTrajFeatures,
          data.timing,
          data.stage2_active,
          data.stage2_dtw_mode,
        );
      }

      // 3. Segment-Ergebnisse
      if (data.segment_similarity && data.segment_similarity.length > 0) {
        const segmentGroups: SegmentGroup[] = data.segment_similarity.map(
          (seg) => ({
            target_segment: seg.target_segment,
            target_segment_features: seg.target_segment_features ?? undefined, // direkt
            results: this.transformEmbeddingResults(
              seg.similar_segments?.results ?? [],
              'segment',
            ),
          }),
        );

        callbacks.onSegmentsFound?.(segmentGroups);
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      callbacks.onError?.(errorMessage);
    }
  }

  private static transformEmbeddingResults(
    results: EmbeddingSimilarityResult[],
    type: 'traj' | 'segment',
  ): SimilarityResult[] {
    return results.map((result) => ({
      traj_id: type === 'traj' ? result.seg_id : result.traj_id,
      seg_id: type === 'segment' ? result.seg_id : undefined,
      similarity_score: result.rrf_score ?? 0,
      // Stage 2
      rank_stage1: result.rank_stage1,
      rank_stage2: result.rank_stage2,
      dtw_distance: result.dtw_distance,
      // Features
      duration: result.features?.duration ?? 0,
      weight: result.features?.weight ?? 0,
      length: result.features?.length ?? 0,
      movement_type: result.features?.movement_type ?? '',
      mean_vel_act: result.features?.mean_vel_act ?? 0,
      max_vel_act: result.features?.max_vel_act ?? 0,
      std_vel_act: result.features?.std_vel_act ?? 0,
      mean_accel_act: result.features?.mean_accel_act ?? 0,
      max_accel_act: result.features?.max_accel_act ?? 0,
      min_accel_act: result.features?.min_accel_act ?? 0,
      std_accel_act: result.features?.std_accel_act ?? 0,
      min_distance: result.features?.min_distance, // NEU
      mean_distance: result.features?.mean_distance, // NEU
      max_distance: result.features?.max_distance, // NEU
      position_x: result.features?.position_x ?? 0,
      position_y: result.features?.position_y ?? 0,
      position_z: result.features?.position_z ?? 0,
    }));
  }
}
