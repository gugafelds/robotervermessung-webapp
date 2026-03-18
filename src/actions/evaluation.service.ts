/* eslint-disable no-console */

'use server';

// React Hook für Service

import {
  transformEDDeviationResult,
  transformEDInfoResult,
  transformGDDeviationResult,
  transformGDInfoResult,
  transformQDTWDeviationResult,
  transformQDTWInfoResult,
  transformSIDTWDeviationResult,
  transformSIDTWInfoResult,
} from '@/src/lib/transformer.evaluation';
import { transformTrajInfoResult } from '@/src/lib/transformer.motion';
import type {
  EDPosition,
  EDPositionRaw,
  GDOrientation,
  GDOrientationRaw,
  QDTWOrientation,
  QDTWOrientationRaw,
  SIDTWPosition,
  SIDTWPositionRaw,
} from '@/types/evaluation.types';
import type {
  EvaluationIDsResponse,
  PaginationParams,
} from '@/types/pagination.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// Erweiterte Parameter für die Suche/Pagination
export interface SearchEvaluationParams extends PaginationParams {
  query?: string;
  calibration?: boolean;
  pickPlace?: boolean;
  pointsEvents?: number;
  weight?: number;
  velocity?: number;
}

/* eslint-disable no-await-in-loop */
async function streamFromAPI<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(<Uint8Array>value);
    }
  } finally {
    reader.releaseLock();
  }

  return JSON.parse(new TextDecoder().decode(Buffer.concat(chunks)));
}
/* eslint-enable no-await-in-loop */

async function fetchFromAPI<T>(
  endpoint: string,
  useStream = false,
): Promise<T> {
  if (useStream) {
    return streamFromAPI<T>(endpoint);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    cache: 'no-cache',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
}

// Erweiterte Funktion, die nun auch Suchparameter akzeptiert und nur Trajen mit Evaluationsdaten zurückgibt
export const getEvaluationTrajIDs = async (
  params: SearchEvaluationParams = { page: 1, pageSize: 20 },
): Promise<EvaluationIDsResponse> => {
  try {
    // URL-Parameter für die Suche/Paginierung erstellen
    const queryParams = new URLSearchParams();

    // Suchparameter hinzufügen
    if (params.query) {
      queryParams.append('query', params.query);
      console.log('Evaluation-Suche mit Query:', params.query);
    }
    if (params.pointsEvents)
      queryParams.append('points_events', params.pointsEvents.toString());
    if (params.weight) queryParams.append('weight', params.weight.toString());
    if (params.velocity)
      queryParams.append('velocity', params.velocity.toString());

    // Pagination-Parameter
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.pageSize)
      queryParams.append('page_size', params.pageSize.toString());

    // API-Endpunkt mit Parametern - entweder Search oder Regular basierend auf Parametern
    // Wir verwenden jetzt immer den Such-Endpunkt, da dieser die Filterung nach Evaluationsdaten enthält
    const endpoint = `/evaluation/search?${queryParams.toString()}`;

    console.log('Evaluation API-Anfrage:', endpoint);

    const result = await fetchFromAPI<{
      traj_info: any[];
      pagination: {
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
        has_next: boolean;
        has_previous: boolean;
      };
    }>(endpoint);

    // Paginierung in camelCase transformieren
    return {
      evaluationTrajIDs: {
        traj_info: transformTrajInfoResult(result.traj_info || []),
      },
      pagination: {
        total: result.pagination.total,
        page: result.pagination.page,
        pageSize: result.pagination.page_size,
        totalPages: result.pagination.total_pages,
        hasNext: result.pagination.has_next,
        hasPrevious: result.pagination.has_previous,
      },
    };
  } catch (error) {
    console.error('Error fetching Evaluation Traj IDs:', error);
    throw error;
  }
};

export const getEvaluationInfoById = async (
  id: string,
): Promise<{
  SIDTWInfo: any[];
  EDInfo: any[];
  QDTWInfo: any[];
  GDInfo: any[];
}> => {
  try {
    const result = await fetchFromAPI<{
      [key: string]: any[];
    }>(`/evaluation/evaluation_info/${id}`);

    return {
      SIDTWInfo: transformSIDTWInfoResult(result.sidtw_info || []),
      EDInfo: transformEDInfoResult(result.ed_info || []),
      QDTWInfo: transformQDTWInfoResult(result.qdtw_info || []),
      GDInfo: transformGDInfoResult(result.gd_info || []),
    };
  } catch (error) {
    console.error(`Error fetching evaluation info for ${id}:`, error);
    return {
      SIDTWInfo: [],
      EDInfo: [],
      QDTWInfo: [],
      GDInfo: [],
    };
  }
};

export const getEDPositionById = async (id: string): Promise<EDPosition[]> => {
  try {
    const result = await fetchFromAPI<{
      position_euclidean: EDPositionRaw[];
    }>(`/evaluation/ed_evaluation/${id}`);
    return transformEDDeviationResult(result.position_euclidean);
  } catch (error) {
    console.error('Error fetching Euclidean deviation data:', error);
    throw error;
  }
};

export const getSIDTWPositionById = async (
  id: string,
): Promise<SIDTWPosition[]> => {
  try {
    const result = await fetchFromAPI<{ position_sidtw: SIDTWPositionRaw[] }>(
      `/evaluation/sidtw_evaluation/${id}`,
    );
    return transformSIDTWDeviationResult(result.position_sidtw);
  } catch (error) {
    console.error('Error fetching SIDTW deviation data:', error);
    throw error;
  }
};

/* export const getDTWPositionById = async (
  id: string,
): Promise<DTWPosition[]> => {
  try {
    const result = await fetchFromAPI<{ position_dtw: DTWPositionRaw[] }>(
      `/evaluation/position_dtw/${id}`,
    );
    return transformDTWDeviationResult(result.position_dtw);
  } catch (error) {
    console.error('Error fetching DTW deviation data:', error);
    throw error;
  }
}; */

export const checkPositionDataAvailability = async (
  id: string,
): Promise<boolean> => {
  try {
    const result = await fetchFromAPI<{ has_deviation_data: boolean }>(
      `/evaluation/has_deviation_data/${id}`,
    );
    return result.has_deviation_data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking deviation data availability:', error);
    return false;
  }
};

export const checkOrientationDataAvailability = async (
  id: string,
): Promise<boolean> => {
  try {
    const result = await fetchFromAPI<{ has_orientation_data: boolean }>(
      `/evaluation/has_orientation_data/${id}`,
    );
    return result.has_orientation_data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking orientation data availability:', error);
    return false;
  }
};

export const getQDTWOrientationById = async (
  id: string,
): Promise<QDTWOrientation[]> => {
  try {
    const result = await fetchFromAPI<{
      qdtw_evaluation: QDTWOrientationRaw[];
    }>(`/evaluation/qdtw_evaluation/${id}`);
    return transformQDTWDeviationResult(result.qdtw_evaluation);
  } catch (error) {
    console.error('Error fetching QDTW deviation data:', error);
    throw error;
  }
};

export const getGDOrientationById = async (
  id: string,
): Promise<GDOrientation[]> => {
  try {
    const result = await fetchFromAPI<{
      gd_evaluation: GDOrientationRaw[];
    }>(`/evaluation/gd_evaluation/${id}`);
    return transformGDDeviationResult(result.gd_evaluation);
  } catch (error) {
    console.error('Error fetching GD orientation data:', error);
    throw error;
  }
};
