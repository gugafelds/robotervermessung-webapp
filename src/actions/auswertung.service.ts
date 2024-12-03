/* eslint-disable no-console */

'use server';

import {
  transformDFDDeviationResult,
  transformDFDInfoResult,
  transformEADeviationResult,
  transformEAInfoResult,
  transformSIDTWDeviationResult,
  transformSIDTWInfoResult,
} from '@/src/lib/transformer.auswertung';
import { transformBahnInfoResult } from '@/src/lib/transformer.bewegungsdaten';
import type {
  AuswertungInfo,
  DFDDeviation,
  DFDDeviationRaw,
  EADeviation,
  EADeviationRaw,
  SIDTWDeviation,
  SIDTWDeviationRaw,
} from '@/types/auswertung.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

// API Response Types
interface ApiResponse {
  bahn_info: any[]; // oder spezifischer Type
  auswertung_info: {
    dfd_info: any[]; // oder spezifischer Type
    sidtw_info: any[]; // oder spezifischer Type
    euclidean_info: any[]; // oder spezifischer Type
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

export const getAllAuswertungInfo = async (): Promise<AuswertungInfo> => {
  try {
    const result = await fetchFromAPI<ApiResponse>(
      '/auswertung/auswertung_info',
    );

    return {
      bahn_info: transformBahnInfoResult(result.bahn_info),
      auswertung_info: {
        dfd_info: transformDFDInfoResult(result.auswertung_info.dfd_info),
        sidtw_info: transformSIDTWInfoResult(result.auswertung_info.sidtw_info),
        euclidean_info: transformEAInfoResult(
          result.auswertung_info.euclidean_info,
        ),
      },
    };
  } catch (error) {
    console.error('Error fetching all Auswertung info:', error);
    throw error;
  }
};

export const getEADeviationById = async (
  id: string,
): Promise<EADeviation[]> => {
  try {
    const result = await fetchFromAPI<{
      euclidean_deviation: EADeviationRaw[];
    }>(`/auswertung/euclidean_deviation/${id}`);
    return transformEADeviationResult(result.euclidean_deviation);
  } catch (error) {
    console.error('Error fetching Euclidean deviation data:', error);
    throw error;
  }
};

export const getDFDDeviationById = async (
  id: string,
): Promise<DFDDeviation[]> => {
  try {
    const result = await fetchFromAPI<{ dfd_deviation: DFDDeviationRaw[] }>(
      `/auswertung/dfd_deviation/${id}`,
    );
    return transformDFDDeviationResult(result.dfd_deviation);
  } catch (error) {
    console.error('Error fetching DFD deviation data:', error);
    throw error;
  }
};

export const getSIDTWDeviationById = async (
  id: string,
): Promise<SIDTWDeviation[]> => {
  try {
    const result = await fetchFromAPI<{ sidtw_deviation: SIDTWDeviationRaw[] }>(
      `/auswertung/sidtw_deviation/${id}`,
    );
    return transformSIDTWDeviationResult(result.sidtw_deviation);
  } catch (error) {
    console.error('Error fetching SIDTW deviation data:', error);
    throw error;
  }
};

export const checkDeviationDataAvailability = async (
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
