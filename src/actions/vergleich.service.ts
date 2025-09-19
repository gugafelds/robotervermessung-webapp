// Bestehende Interfaces
export interface MetaValuesStatus {
  total_rows: number;
  meta_values_count: number;
  completion_rate: number;
  avg_meta_value: number | null;
  min_meta_value: number | null;
  max_meta_value: number | null;
  has_meta_values: boolean;
}

export interface MetaValuesCalculationResponse {
  status: string;
  message: string;
  task_id?: string;
  processed_rows?: number;
  parameters_used?: string[];
  stats?: {
    min_meta_value: number;
    max_meta_value: number;
    avg_meta_value: number;
  };
}

export interface TaskStatus {
  task_id: string;
  status: string; // "running" | "completed" | "failed"
  progress_percent: number;
  error?: string;
}

// Neue Interfaces für Metadata
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

export interface SimilaritySearchParams {
  bahnLimit: number;
  segmentLimit: number;
  weights: {
    duration: number;
    weight: number;
    length: number;
    movement_type: number;
    direction_x: number;
    direction_y: number;
    direction_z: number;
  };
}

export interface SimilarityResult {
  bahn_id?: string;
  segment_id?: string;
  similarity_score: number;
  meta_value?: number;
  duration?: number;
  weight?: number;
  length?: number;
  movement_type?: string;
  sidtw_average_distance?: number;
}

export interface BahnSimilarityResponse {
  target_bahn_id: string;
  original_input: string;
  input_type: string;
  bahn_similarity: {
    target: SimilarityResult;
    similar_bahnen: SimilarityResult[];
    auto_threshold: number;
    total_found: number;
  };
  calculation_method: string;
}

export interface SegmentTaskResponse {
  task_id: string;
  status: string;
  message: string;
  target_bahn_id: string;
  original_input: string;
  input_type: string;
  total_segments: number;
  estimated_duration_minutes: number;
}

export interface SegmentTaskStatus extends TaskStatus {
  total_bahns?: number;
  processed_bahns?: number;
  total_segments?: number;
  processed_segments?: number;
  current_segment?: string;
  results?: Array<{
    target_segment: string;
    similarity_data: {
      target: SimilarityResult;
      similar_segmente: SimilarityResult[];
      auto_threshold: number;
      total_found: number;
    };
  }>;
}

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

export const MetaValuesService = {
  /**
   * Holt den aktuellen Status der Meta-Values
   */
  async getStatus(): Promise<MetaValuesStatus> {
    return fetchAPI<MetaValuesStatus>('/meta-values-status');
  },

  /**
   * Startet die Meta-Values Berechnung
   */
  async calculate(): Promise<MetaValuesCalculationResponse> {
    return fetchAPI<MetaValuesCalculationResponse>('/calculate-meta-values', {
      method: 'POST',
    });
  },

  /**
   * Holt Task Status
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return fetchAPI<TaskStatus>(`/task-status/${taskId}`);
  },

  /**
   * Startet Meta-Values Berechnung und wartet bis Abschluss
   * @param onStatusUpdate Optional callback für Status Updates
   */
  async calculateAndWait(
    onStatusUpdate?: (isRunning: boolean) => void,
  ): Promise<void> {
    const result = await this.calculate();

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
          const taskStatus = await this.getTaskStatus(result.task_id!);

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
      }, 500); // Alle halbe Sekunde checken
    });
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
          const taskStatus = await MetaValuesService.getTaskStatus(
            result.task_id!,
          );

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
export const SimilarityService = {
  /**
   * Sucht ähnliche Bahnen (sofortige Antwort)
   */
  async searchBahnen(
    targetId: string,
    params: SimilaritySearchParams,
  ): Promise<BahnSimilarityResponse> {
    const searchParams = new URLSearchParams({
      limit: params.bahnLimit.toString(),
      weight_duration: params.weights.duration.toString(),
      weight_weight: params.weights.weight.toString(),
      weight_length: params.weights.length.toString(),
      weight_movement_type: params.weights.movement_type.toString(),
      weight_direction_x: params.weights.direction_x.toString(),
      weight_direction_y: params.weights.direction_y.toString(),
      weight_direction_z: params.weights.direction_z.toString(),
    });

    return fetchAPI<BahnSimilarityResponse>(
      `/similarity/bahnen/${targetId}?${searchParams.toString()}`,
    );
  },

  /**
   * Startet Segment-Task (Background Job)
   */
  async startSegmentTask(
    targetId: string,
    params: SimilaritySearchParams,
  ): Promise<SegmentTaskResponse> {
    return fetchAPI<SegmentTaskResponse>(
      `/similarity/segments/start-task/${targetId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          segment_limit: params.segmentLimit,
          weight_duration: params.weights.duration,
          weight_weight: params.weights.weight,
          weight_length: params.weights.length,
          weight_movement_type: params.weights.movement_type,
          weight_direction_x: params.weights.direction_x,
          weight_direction_y: params.weights.direction_y,
          weight_direction_z: params.weights.direction_z,
        }),
      },
    );
  },

  /**
   * Holt Segment Task Status (erweitert von MetaValuesService)
   */
  async getSegmentTaskStatus(taskId: string): Promise<SegmentTaskStatus> {
    return fetchAPI<SegmentTaskStatus>(`/task-status/${taskId}`);
  },

  /**
   * Führt komplette Similarity Search durch mit Progress Callbacks
   */
  async searchSimilarity(
    targetId: string,
    params: SimilaritySearchParams,
    callbacks?: {
      onBahnenFound?: (results: SimilarityResult[]) => void;
      onSegmentProgress?: (progress: string) => void;
      onSegmentsFound?: (results: SimilarityResult[]) => void;
      onError?: (error: string) => void;
    },
  ): Promise<{
    bahnResults: SimilarityResult[];
    segmentResults: SimilarityResult[];
  }> {
    try {
      // Phase 1: Bahnen sofort laden
      const bahnResponse = await this.searchBahnen(targetId, params);

      const bahnResults: SimilarityResult[] = [];
      if (bahnResponse.bahn_similarity?.target) {
        bahnResults.push(bahnResponse.bahn_similarity.target);
      }
      if (bahnResponse.bahn_similarity?.similar_bahnen) {
        bahnResults.push(...bahnResponse.bahn_similarity.similar_bahnen);
      }

      // Bahnen sofort zurückgeben
      callbacks?.onBahnenFound?.(bahnResults);

      // Phase 2: Segment-Task starten
      const taskResponse = await this.startSegmentTask(targetId, params);

      if (callbacks?.onSegmentProgress) {
        callbacks.onSegmentProgress(
          `${taskResponse.total_segments} Segmente werden berechnet...`,
        );
      }

      // Phase 3: Polling für Segmente
      const segmentResults = await this.pollSegmentTask(
        taskResponse.task_id,
        callbacks?.onSegmentProgress,
      );

      callbacks?.onSegmentsFound?.(segmentResults);

      return {
        bahnResults,
        segmentResults,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      callbacks?.onError?.(errorMessage);
      throw error;
    }
  },

  /**
   * Polling für Segment Task Results
   */
  async pollSegmentTask(
    taskId: string,
    onProgress?: (progress: string) => void,
  ): Promise<SimilarityResult[]> {
    return new Promise((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          const taskStatus = await this.getSegmentTaskStatus(taskId);

          if (taskStatus.status === 'completed') {
            clearInterval(pollInterval);

            // Extrahiere Segment-Ergebnisse
            const segmentResults: SimilarityResult[] = [];

            if (taskStatus.results && Array.isArray(taskStatus.results)) {
              taskStatus.results.forEach((segmentGroup) => {
                if (segmentGroup.similarity_data?.target) {
                  segmentResults.push(segmentGroup.similarity_data.target);
                }
                if (segmentGroup.similarity_data?.similar_segmente) {
                  segmentResults.push(
                    ...segmentGroup.similarity_data.similar_segmente,
                  );
                }
              });
            }

            resolve(segmentResults);
          } else if (taskStatus.status === 'failed') {
            clearInterval(pollInterval);
            reject(new Error(taskStatus.error || 'Segment task failed'));
          } else if (taskStatus.status === 'running') {
            // Progress Update
            const processed =
              taskStatus.processed_bahns || taskStatus.processed_segments || 0;
            const total =
              taskStatus.total_bahns || taskStatus.total_segments || 0;

            if (onProgress) {
              onProgress(`${processed}/${total} Segmente berechnet`);
            }
          }
        } catch (error) {
          clearInterval(pollInterval);
          reject(error);
        }
      }, 500); // Alle 2 Sekunden pollen
    });
  },
};
