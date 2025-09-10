// services/vergleich.service.ts

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
      }, 1000); // Alle Sekunde checken
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
      }, 1000); // Alle Sekunde checken
    });
  },
};
