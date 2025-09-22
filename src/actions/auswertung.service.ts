/* eslint-disable no-console */

'use server';

import {
  transformDFDDeviationResult,
  transformDFDInfoResult,
  transformDTWDeviationResult,
  transformDTWInfoResult,
  transformEADeviationResult,
  transformEAInfoResult,
  transformSIDTWDeviationResult,
  transformSIDTWInfoResult,
} from '@/src/lib/transformer.auswertung';
import { transformBahnInfoResult } from '@/src/lib/transformer.bewegungsdaten';
import type {
  DFDPosition,
  DFDPositionRaw,
  DTWPosition,
  DTWPositionRaw,
  EAPosition,
  EAPositionRaw,
  SIDTWPosition,
  SIDTWPositionRaw,
} from '@/types/auswertung.types';
import type {
  AuswertungIDsResponse,
  PaginationParams,
} from '@/types/pagination.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// Erweiterte Parameter für die Suche/Pagination
export interface SearchAuswertungParams extends PaginationParams {
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
      chunks.push(value);
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

// Erweiterte Funktion, die nun auch Suchparameter akzeptiert und nur Bahnen mit Auswertungsdaten zurückgibt
export const getAuswertungBahnIDs = async (
  params: SearchAuswertungParams = { page: 1, pageSize: 20 },
): Promise<AuswertungIDsResponse> => {
  try {
    // URL-Parameter für die Suche/Paginierung erstellen
    const queryParams = new URLSearchParams();

    // Suchparameter hinzufügen
    if (params.query) {
      queryParams.append('query', params.query);
      console.log('Auswertung-Suche mit Query:', params.query);
    }
    if (params.calibration !== undefined)
      queryParams.append('calibration', params.calibration.toString());
    if (params.pickPlace !== undefined)
      queryParams.append('pick_place', params.pickPlace.toString());
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
    // Wir verwenden jetzt immer den Such-Endpunkt, da dieser die Filterung nach Auswertungsdaten enthält
    const endpoint = `/auswertung/search?${queryParams.toString()}`;

    console.log('Auswertung API-Anfrage:', endpoint);

    const result = await fetchFromAPI<{
      bahn_info: any[];
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
      auswertungBahnIDs: {
        bahn_info: transformBahnInfoResult(result.bahn_info || []),
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
    console.error('Error fetching Auswertung Bahn IDs:', error);
    throw error;
  }
};

export const getAuswertungInfoById = async (
  id: string,
): Promise<{
  info_dfd: any[];
  info_sidtw: any[];
  info_dtw: any[];
  info_euclidean: any[];
}> => {
  try {
    const result = await fetchFromAPI<{
      [key: string]: any[];
    }>(`/auswertung/auswertung_info/${id}`);

    return {
      info_dfd: transformDFDInfoResult(result.info_dfd || []),
      info_sidtw: transformSIDTWInfoResult(result.info_sidtw || []),
      info_dtw: transformDTWInfoResult(result.info_dtw || []),
      info_euclidean: transformEAInfoResult(result.info_euclidean || []),
    };
  } catch (error) {
    console.error(`Error fetching Auswertung info for ${id}:`, error);
    return {
      info_dfd: [],
      info_sidtw: [],
      info_dtw: [],
      info_euclidean: [],
    };
  }
};

export const getEAPositionById = async (id: string): Promise<EAPosition[]> => {
  try {
    const result = await fetchFromAPI<{
      position_euclidean: EAPositionRaw[];
    }>(`/auswertung/position_euclidean/${id}`);
    return transformEADeviationResult(result.position_euclidean);
  } catch (error) {
    console.error('Error fetching Euclidean deviation data:', error);
    throw error;
  }
};

export const getDFDPositionById = async (
  id: string,
): Promise<DFDPosition[]> => {
  try {
    const result = await fetchFromAPI<{ position_dfd: DFDPositionRaw[] }>(
      `/auswertung/position_dfd/${id}`,
    );
    return transformDFDDeviationResult(result.position_dfd);
  } catch (error) {
    console.error('Error fetching DFD deviation data:', error);
    throw error;
  }
};

export const getSIDTWPositionById = async (
  id: string,
): Promise<SIDTWPosition[]> => {
  try {
    const result = await fetchFromAPI<{ position_sidtw: SIDTWPositionRaw[] }>(
      `/auswertung/position_sidtw/${id}`,
    );
    return transformSIDTWDeviationResult(result.position_sidtw);
  } catch (error) {
    console.error('Error fetching SIDTW deviation data:', error);
    throw error;
  }
};

export const getDTWPositionById = async (
  id: string,
): Promise<DTWPosition[]> => {
  try {
    const result = await fetchFromAPI<{ position_dtw: DTWPositionRaw[] }>(
      `/auswertung/position_dtw/${id}`,
    );
    return transformDTWDeviationResult(result.position_dtw);
  } catch (error) {
    console.error('Error fetching DTW deviation data:', error);
    throw error;
  }
};

export const checkPositionDataAvailability = async (
  id: string,
): Promise<boolean> => {
  try {
    const result = await fetchFromAPI<{ has_deviation_data: boolean }>(
      `/auswertung/has_deviation_data/${id}`,
    );
    return result.has_deviation_data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking deviation data availability:', error);
    return false;
  }
};
