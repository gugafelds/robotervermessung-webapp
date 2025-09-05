/* eslint-disable no-console */

'use server';

import {
  transformBahnAccelIstResult,
  transformBahnAccelSollResult,
  transformBahnEventsResult,
  transformBahnIMUResult,
  transformBahnInfobyIDResult,
  transformBahnInfoResponse,
  transformBahnJointStatesResult,
  transformBahnOrientationSollResult,
  transformBahnPoseIstResult,
  transformBahnPoseTransResult,
  transformBahnPositionSollResult,
  transformBahnTwistIstResult,
  transformBahnTwistSollResult,
} from '@/src/lib/transformer.bewegungsdaten';
import type {
  BahnAccelIst,
  BahnAccelSoll,
  BahnEvents,
  BahnIMU,
  BahnInfo,
  BahnJointStates,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
  BahnTwistIst,
  BahnTwistSoll,
} from '@/types/bewegungsdaten.types';
import type {
  BahnInfoResponse,
  PaginationParams,
} from '@/types/pagination.types';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api';

/* eslint-disable no-await-in-loop */
async function streamFromAPI(endpoint: string) {
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

async function fetchFromAPI(endpoint: string, useStream = false) {
  if (useStream) {
    return streamFromAPI(endpoint);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    cache: 'no-cache',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
}

export const getBahnInfo = async (
  params: PaginationParams = { page: 1, pageSize: 20 },
): Promise<BahnInfoResponse> => {
  try {
    // URL-Parameter für die Paginierung erstellen
    // Konvertiere camelCase zu snake_case für die API-Anfrage
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.pageSize)
      queryParams.append('page_size', params.pageSize.toString());

    // API-Anfrage mit Paginierungsparametern
    const result = await fetchFromAPI(
      `/bahn/bahn_info?${queryParams.toString()}`,
    );

    // Transformiere die Antwort von snake_case zu camelCase
    return transformBahnInfoResponse(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn info:', error);
    throw error;
  }
};

export interface SearchBahnParams extends PaginationParams {
  query?: string;
  calibration?: boolean;
  pickPlace?: boolean;
  pointsEvents?: number;
  weight?: number;
  settedVelocity?: number;
  recordingDate?: string;
}

export const searchBahnInfo = async (
  searchParams: SearchBahnParams = { page: 1, pageSize: 20 },
): Promise<BahnInfoResponse> => {
  try {
    // URL-Parameter für die Suche erstellen
    const queryParams = new URLSearchParams();

    // Parameter hinzufügen und snake_case für API verwenden
    if (searchParams.query) {
      queryParams.append('query', searchParams.query);
      console.log('Suche mit Query:', searchParams.query);
    }
    if (searchParams.calibration !== undefined)
      queryParams.append('calibration', searchParams.calibration.toString());
    if (searchParams.pickPlace !== undefined)
      queryParams.append('pick_place', searchParams.pickPlace.toString());
    if (searchParams.pointsEvents)
      queryParams.append('points_events', searchParams.pointsEvents.toString());
    if (searchParams.weight)
      queryParams.append('weight', searchParams.weight.toString());
    if (searchParams.settedVelocity)
      queryParams.append(
        'setted_velocity',
        searchParams.settedVelocity.toString(),
      );
    if (searchParams.recordingDate)
      queryParams.append('recording_date', searchParams.recordingDate);
    if (searchParams.page)
      queryParams.append('page', searchParams.page.toString());
    if (searchParams.pageSize)
      queryParams.append('page_size', searchParams.pageSize.toString());

    const apiUrl = `/bahn/bahn_search?${queryParams.toString()}`;
    console.log('API-Anfrage:', apiUrl);

    // API-Anfrage mit Suchparametern
    const result = await fetchFromAPI(apiUrl);
    console.log('API-Ergebnis erhalten:', result.bahn_info?.length, 'Einträge');

    // Transformiere die Antwort
    return transformBahnInfoResponse(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error searching Bahn info:', error);
    throw error;
  }
};

export const getBahnInfoById = async (id: string): Promise<BahnInfo> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_info/${id}`);
    return transformBahnInfobyIDResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn info by ID:', error);
    throw error;
  }
};

export const getBahnPoseIstById = async (
  id: string,
): Promise<BahnPoseIst[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_pose_ist/${id}`, true);
    return transformBahnPoseIstResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn pose ist by ID:', error);
    throw error;
  }
};

export const getBahnPoseTransById = async (
  id: string,
): Promise<BahnPoseTrans[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_pose_trans/${id}`, true);
    return transformBahnPoseTransResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching transformed pose data:', error);
    throw error;
  }
};

export const getBahnTwistIstById = async (
  id: string,
): Promise<BahnTwistIst[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_twist_ist/${id}`, true);
    return transformBahnTwistIstResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn twist ist by ID:', error);
    throw error;
  }
};

export const getBahnAccelIstById = async (
  id: string,
): Promise<BahnAccelIst[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_accel_ist/${id}`, true);
    return transformBahnAccelIstResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn accel ist by ID:', error);
    throw error;
  }
};

export const getBahnAccelSollById = async (
  id: string,
): Promise<BahnAccelSoll[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_accel_soll/${id}`, true);
    return transformBahnAccelSollResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn accel soll by ID:', error);
    throw error;
  }
};

export const getBahnPositionSollById = async (
  id: string,
): Promise<BahnPositionSoll[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_position_soll/${id}`, true);
    return transformBahnPositionSollResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn position soll by ID:', error);
    throw error;
  }
};

export const getBahnOrientationSollById = async (
  id: string,
): Promise<BahnOrientationSoll[]> => {
  try {
    const result = await fetchFromAPI(
      `/bahn/bahn_orientation_soll/${id}`,
      true,
    );
    return transformBahnOrientationSollResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn orientation soll by ID:', error);
    throw error;
  }
};

export const getBahnTwistSollById = async (
  id: string,
): Promise<BahnTwistSoll[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_twist_soll/${id}`, true);
    return transformBahnTwistSollResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn twist soll by ID:', error);
    throw error;
  }
};

export const getBahnJointStatesById = async (
  id: string,
): Promise<BahnJointStates[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_joint_states/${id}`, true);
    return transformBahnJointStatesResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn joint states by ID:', error);
    throw error;
  }
};

export const getBahnEventsById = async (id: string): Promise<BahnEvents[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_events/${id}`, true);
    return transformBahnEventsResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn events by ID:', error);
    throw error;
  }
};

export const getBahnIMUById = async (id: string): Promise<BahnIMU[]> => {
  try {
    const result = await fetchFromAPI(`/bahn/bahn_imu/${id}`, true);
    return transformBahnIMUResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Bahn IMU by ID:', error);
    throw error;
  }
};

export const checkTransformedDataExists = async (
  id: string,
): Promise<boolean> => {
  try {
    const result = await fetchFromAPI(`/bahn/check_transformed_data/${id}`);
    return result.exists;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking transformed data:', error);
    return false;
  }
};
