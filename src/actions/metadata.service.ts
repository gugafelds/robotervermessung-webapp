import type {
  AvailableDate,
  EmbeddingSimilarityParams,
  EmbeddingSimilarityResult,
  HierarchicalSimilarityResponse,
  MetadataCalculationRequest,
  MetadataCalculationResponse,
  MetadataStats,
  SearchTiming,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
  TaskStatus,
} from '@/types/similarity.types';

const API_BASE_URL = '/api/metadata';

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

export const MetadataService = {
  async getStats(): Promise<MetadataStats> {
    return fetchAPI<MetadataStats>('/metadata-stats');
  },

  async getAvailableDates(): Promise<AvailableDate[]> {
    const result = await fetchAPI<{ available_dates: AvailableDate[] }>(
      '/available-dates',
    );
    return result.available_dates;
  },

  async calculate(
    request: MetadataCalculationRequest,
  ): Promise<MetadataCalculationResponse> {
    return fetchAPI<MetadataCalculationResponse>('/calculate-metadata', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async calculateAndWait(
    request: MetadataCalculationRequest,
    onStatusUpdate?: (isRunning: boolean) => void,
  ): Promise<void> {
    const result = await this.calculate(request);

    if (!result.task_id) {
      return Promise.resolve();
    }

    onStatusUpdate?.(true);

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
        } catch (error) {
          clearInterval(pollInterval);
          onStatusUpdate?.(false);
          reject(error);
        }
      }, 500);
    });
  },
};