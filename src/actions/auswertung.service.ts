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
  AuswertungInfo,
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
  AuswertungInfoResponse,
  PaginationParams,
} from '@/types/pagination.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// API Response Types
interface ApiResponse {
  bahn_info: any[]; // oder spezifischer Type
  auswertung_info: {
    info_dfd: any[]; // oder spezifischer Type
    info_sidtw: any[];
    info_dtw: any[]; // oder spezifischer Type
    info_euclidean: any[]; // oder spezifischer Type
  };
  pagination: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
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

export const getAuswertungBahnIDs = async (
  params: PaginationParams = { page: 1, pageSize: 20 },
): Promise<AuswertungIDsResponse> => {
  try {
    // URL-Parameter für die Paginierung erstellen
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.pageSize)
      queryParams.append('page_size', params.pageSize.toString());

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
    }>(`/auswertung/auswertung_info_overview?${queryParams.toString()}`);

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

// Angepasste Funktion zur Unterstützung von Paginierung
export const getAllAuswertungInfo = async (
  params: PaginationParams = { page: 1, pageSize: 20 },
): Promise<AuswertungInfoResponse> => {
  try {
    // URL-Parameter für die Paginierung erstellen
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.pageSize)
      queryParams.append('page_size', params.pageSize.toString());

    const result = await fetchFromAPI<ApiResponse>(
      `/auswertung/auswertung_info?${queryParams.toString()}`,
    );

    // Daten transformieren
    const transformedData: AuswertungInfo = {
      bahn_info: transformBahnInfoResult(result.bahn_info || []),
      auswertung_info: {
        info_dfd: transformDFDInfoResult(
          result.auswertung_info?.info_dfd || [],
        ),
        info_sidtw: transformSIDTWInfoResult(
          result.auswertung_info?.info_sidtw || [],
        ),
        info_dtw: transformDTWInfoResult(
          result.auswertung_info?.info_dtw || [],
        ),
        info_euclidean: transformEAInfoResult(
          result.auswertung_info?.info_euclidean || [],
        ),
      },
    };

    // Paginierung in camelCase transformieren
    return {
      auswertungInfo: transformedData,
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
    console.error('Error fetching all Auswertung info:', error);
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
