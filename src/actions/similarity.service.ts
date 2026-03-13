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

      // Stage 2 Parameter
      if (params.stage2_active !== undefined) {
        queryParams.append('stage2_active', params.stage2_active.toString());
      }
      if (params.dtw_mode) {
        queryParams.append('dtw_mode', params.dtw_mode);
      }

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

      // 1. Target Bahn Features
      let targetTrajFeatures: TargetFeatures | undefined;
      if (data.target_traj_features) {
        targetTrajFeatures = {
          seg_id: data.target_traj_features.seg_id,
          traj_id: data.target_traj_features.traj_id,
          duration: data.target_traj_features.duration,
          weight: data.target_traj_features.weight,
          length: data.target_traj_features.length,
          mean_vel_act: data.target_traj_features.mean_vel_act,
          max_vel_act: data.target_traj_features.max_vel_act,
          std_vel_act: data.target_traj_features.std_vel_act,
          mean_accel_act:
            data.target_traj_features.mean_accel_act,
          max_accel_act: data.target_traj_features.max_accel_act,
          min_accel_act: data.target_traj_features.min_accel_act,
          std_accel_act: data.target_traj_features.std_accel_act,
          sidtw_average_distance:
            data.target_traj_features.sidtw_average_distance,
          movement_type: data.target_traj_features.movement_type,
          position_x: data.target_traj_features.position_x,
          position_y: data.target_traj_features.position_y,
          position_z: data.target_traj_features.position_z,
        };
      }

      // 2. Trajen-Ergebnisse
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
          (seg) => {
            let targetSegFeatures: TargetFeatures | undefined;
            if (seg.target_segment_features) {
              targetSegFeatures = {
                seg_id: seg.target_segment_features.seg_id,
                traj_id: seg.target_segment_features.traj_id,
                duration: seg.target_segment_features.duration,
                weight: seg.target_segment_features.weight,
                length: seg.target_segment_features.length,
                mean_vel_act: seg.target_segment_features.mean_vel_act,
                max_vel_act: seg.target_segment_features.max_vel_act,
                std_vel_act: seg.target_segment_features.std_vel_act,
                mean_accel_act:
                  seg.target_segment_features.mean_accel_act,
                max_accel_act:
                  seg.target_segment_features.max_accel_act,
                min_accel_act:
                  seg.target_segment_features.min_accel_act,
                std_accel_act:
                  seg.target_segment_features.std_accel_act,
                sidtw_average_distance:
                  seg.target_segment_features.sidtw_average_distance,
                movement_type: seg.target_segment_features.movement_type,
                position_x: seg.target_segment_features.position_x,
                position_y: seg.target_segment_features.position_y,
                position_z: seg.target_segment_features.position_z,
              };
            }

            return {
              target_segment: seg.target_segment,
              target_segment_features: targetSegFeatures,
              results: this.transformEmbeddingResults(
                seg.similar_segments?.results ?? [],
                'segment',
              ),
            };
          },
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
      // Stage 2 Felder — nur vorhanden wenn stage2_active=true
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
      sidtw_average_distance: result.features?.sidtw_average_distance ?? 0,
      position_x: result.features?.position_x ?? 0,
      position_y: result.features?.position_y ?? 0,
      position_z: result.features?.position_z ?? 0,
    }));
  }
}