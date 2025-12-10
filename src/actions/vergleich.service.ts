import type {
  AvailableDate,
  EmbeddingSimilarityParams,
  EmbeddingSimilarityResult,
  HierarchicalSimilarityResponse,
  MetadataCalculationRequest,
  MetadataCalculationResponse,
  MetadataStats,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
  TaskStatus,
} from '@/types/similarity.types';

const API_BASE_URL = '/api/vergleich';

// Generic fetch wrapper
const fetchAPI = async <T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> => {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return response.json();
};

export const TaskService = {
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return fetchAPI<TaskStatus>(`/task-status/${taskId}`);
  },
};

// Neue Metadata Services
export const MetadataService = {
  /**
   * Holt Metadata Statistiken
   */
  async getStats(): Promise<MetadataStats> {
    return fetchAPI<MetadataStats>('/metadata-stats');
  },

  /**
   * Holt verfügbare Tage
   */
  async getAvailableDates(): Promise<AvailableDate[]> {
    const result = await fetchAPI<{ available_dates: AvailableDate[] }>(
      '/available-dates',
    );
    return result.available_dates;
  },

  /**
   * Startet Metadata Berechnung
   */
  async calculate(
    request: MetadataCalculationRequest,
  ): Promise<MetadataCalculationResponse> {
    return fetchAPI<MetadataCalculationResponse>('/calculate-metadata', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  /**
   * Startet Metadata Berechnung und wartet bis Abschluss
   * @param request Berechnung Parameter
   * @param onStatusUpdate Optional callback für Status Updates
   */
  async calculateAndWait(
    request: MetadataCalculationRequest,
    onStatusUpdate?: (isRunning: boolean) => void,
  ): Promise<void> {
    const result = await this.calculate(request);

    if (!result.task_id) {
      // Kein Background Task, direkt fertig
      return Promise.resolve();
    }

    // Task läuft
    onStatusUpdate?.(true);

    // Polling bis Task fertig ist
    return new Promise<void>((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          const taskStatus = await TaskService.getTaskStatus(result.task_id!);

          if (taskStatus.status === 'completed') {
            clearInterval(pollInterval);
            onStatusUpdate?.(false);
            resolve();
          } else if (taskStatus.status === 'failed') {
            clearInterval(pollInterval);
            onStatusUpdate?.(false);
            reject(new Error(taskStatus.error || 'Task failed'));
          }
          // Status "running" - weiter pollen
        } catch (error) {
          clearInterval(pollInterval);
          onStatusUpdate?.(false);
          reject(error);
        }
      }, 500); // Alle Sekunde checken
    });
  },
};

// Similarity Service
export class SimilarityService {
  private static readonly BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  static async searchSimilarityEmbedding(
    targetId: string,
    params: EmbeddingSimilarityParams,
    callbacks: {
      onBahnenFound?: (
        results: SimilarityResult[],
        targetFeatures?: TargetFeatures,
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
          'acceleration_weight',
          params.weights.acceleration.toString(),
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

      const response = await fetch(
        `${this.BASE_URL}/api/search/similar/${targetId}?${queryParams.toString()}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: HierarchicalSimilarityResponse = await response.json();
      // ✅ 1. Target Bahn Features extrahieren
      let targetBahnFeatures: TargetFeatures | undefined;
      if (data.target_bahn_features) {
        targetBahnFeatures = {
          segment_id: data.target_bahn_features.segment_id,
          bahn_id: data.target_bahn_features.bahn_id,
          duration: data.target_bahn_features.duration,
          weight: data.target_bahn_features.weight,
          length: data.target_bahn_features.length,
          mean_twist_ist: data.target_bahn_features.mean_twist_ist,
          max_twist_ist: data.target_bahn_features.max_twist_ist,
          std_twist_ist: data.target_bahn_features.std_twist_ist,
          mean_acceleration_ist:
            data.target_bahn_features.mean_acceleration_ist,
          max_acceleration_ist: data.target_bahn_features.max_acceleration_ist,
          min_acceleration_ist: data.target_bahn_features.min_acceleration_ist,
          std_acceleration_ist: data.target_bahn_features.std_acceleration_ist,
          sidtw_average_distance:
            data.target_bahn_features.sidtw_average_distance,
          movement_type: data.target_bahn_features.movement_type,
          position_x: data.target_bahn_features.position_x,
          position_y: data.target_bahn_features.position_y,
          position_z: data.target_bahn_features.position_z,
        };
      }

      // ✅ 2. Bahnen-Ergebnisse mit Target Features
      if (data.bahn_similarity?.results) {
        const bahnResults = this.transformEmbeddingResults(
          data.bahn_similarity.results,
          'bahn',
        );
        callbacks.onBahnenFound?.(bahnResults, targetBahnFeatures);
      }

      // ✅ 3. Segment-Ergebnisse GRUPPIERT mit Target Features
      if (data.segment_similarity && data.segment_similarity.length > 0) {
        const segmentGroups: SegmentGroup[] = data.segment_similarity.map(
          (segmentGroup) => {
            let targetSegmentFeatures: TargetFeatures | undefined;

            if (segmentGroup.target_segment_features) {
              targetSegmentFeatures = {
                segment_id: segmentGroup.target_segment_features.segment_id,
                bahn_id: segmentGroup.target_segment_features.bahn_id,
                duration: segmentGroup.target_segment_features.duration,
                weight: segmentGroup.target_segment_features.weight,
                length: segmentGroup.target_segment_features.length,
                max_twist_ist:
                  segmentGroup.target_segment_features.max_twist_ist,
                mean_twist_ist:
                  segmentGroup.target_segment_features.mean_twist_ist,
                std_twist_ist:
                  segmentGroup.target_segment_features.std_twist_ist,
                mean_acceleration_ist:
                  segmentGroup.target_segment_features.mean_acceleration_ist,
                max_acceleration_ist:
                  segmentGroup.target_segment_features.max_acceleration_ist,
                min_acceleration_ist:
                  segmentGroup.target_segment_features.min_acceleration_ist,
                std_acceleration_ist:
                  segmentGroup.target_segment_features.std_acceleration_ist,
                sidtw_average_distance:
                  segmentGroup.target_segment_features.sidtw_average_distance,
                movement_type:
                  segmentGroup.target_segment_features.movement_type,
                position_x: segmentGroup.target_segment_features.position_x,
                position_y: segmentGroup.target_segment_features.position_y,
                position_z: segmentGroup.target_segment_features.position_z,
              };
            }

            return {
              target_segment: segmentGroup.target_segment,
              target_segment_features: targetSegmentFeatures,
              results: this.transformEmbeddingResults(
                segmentGroup.similar_segments.results,
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
    type: 'bahn' | 'segment',
  ): SimilarityResult[] {
    return results.map((result) => ({
      bahn_id: type === 'bahn' ? result.segment_id : result.bahn_id,
      segment_id: type === 'segment' ? result.segment_id : undefined,
      similarity_score: result.rrf_score || 0,
      duration: result.features?.duration || 0,
      weight: result.features?.weight || 0,
      length: result.features?.length || 0,
      movement_type: result.features?.movement_type || '',
      mean_twist_ist: result.features?.mean_twist_ist || 0,
      max_twist_ist: result.features?.max_twist_ist || 0,
      std_twist_ist: result.features?.std_twist_ist || 0,
      mean_acceleration_ist: result.features?.mean_acceleration_ist || 0,
      max_acceleration_ist: result.features?.max_acceleration_ist || 0,
      min_acceleration_ist: result.features?.min_acceleration_ist || 0,
      std_acceleration_ist: result.features?.std_acceleration_ist || 0,
      sidtw_average_distance: result.features?.sidtw_average_distance || 0,
      position_x: result.features?.position_x || 0,
      position_y: result.features?.position_y || 0,
      position_z: result.features?.position_z || 0,
    }));
  }
}
