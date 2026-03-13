/* eslint-disable no-console */

'use server';

import {
  transformTrajAccelActResult,
  transformTrajAccelCmdResult,
  transformTrajSetpointsResult,
  transformTrajInfobyIDResult,
  transformTrajInfoResponse,
  transformTrajJointStatesResult,
  transformTrajOrientationCmdResult,
  transformTrajPoseActResult,
  transformTrajPoseTransResult,
  transformTrajPositionCmdResult,
  transformTrajVelActResult,
  transformTrajVelCmdResult,
} from '@/src/lib/transformer.motion';
import type {
  TrajAccelAct,
  TrajAccelCmd,
  TrajSetpoints,
  TrajInfo,
  TrajJointStates,
  TrajOrientationCmd,
  TrajPoseAct,
  TrajPoseTrans,
  TrajPositionCmd,
  TrajVelAct,
  TrajVelCmd,
} from '@/types/motion.types';
import type {
  TrajInfoResponse,
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
      chunks.push(<Uint8Array>value);
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

export const getTrajInfo = async (
  params: PaginationParams = { page: 1, pageSize: 20 },
): Promise<TrajInfoResponse> => {
  try {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.pageSize)
      queryParams.append('page_size', params.pageSize.toString());

    const result = await fetchFromAPI(
      `/traj/traj_info?${queryParams.toString()}`,
    );

    return transformTrajInfoResponse(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj info:', error);
    throw error;
  }
};

export interface SearchTrajParams extends PaginationParams {
  query?: string;
  calibration?: boolean;
  pointsEvents?: number;
  weight?: number;
  settedVelocity?: number;
  recordingDate?: string;
  sidtwDistance?: number;
}

export const searchTrajInfo = async (
  searchParams: SearchTrajParams = { page: 1, pageSize: 20 },
): Promise<TrajInfoResponse> => {
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
    if (searchParams.pointsEvents)
      queryParams.append('points_events', searchParams.pointsEvents.toString());
    if (searchParams.weight)
      queryParams.append('weight', searchParams.weight.toString());
    if (searchParams.settedVelocity)
      queryParams.append(
        'setted_velocity',
        searchParams.settedVelocity.toString(),
      );
    if (searchParams.sidtwDistance)
      queryParams.append(
        'sidtw_distance',
        searchParams.sidtwDistance.toString(),
      );
    if (searchParams.recordingDate)
      queryParams.append('recording_date', searchParams.recordingDate);
    if (searchParams.page)
      queryParams.append('page', searchParams.page.toString());
    if (searchParams.pageSize)
      queryParams.append('page_size', searchParams.pageSize.toString());

    const apiUrl = `/traj/traj_search?${queryParams.toString()}`;
    console.log('API-Anfrage:', apiUrl);

    // API-Anfrage mit Suchparametern
    const result = await fetchFromAPI(apiUrl);
    console.log('API-Ergebnis erhalten:', result.traj_info?.length, 'Einträge');

    // Transformiere die Antwort
    return transformTrajInfoResponse(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error searching Traj info:', error);
    throw error;
  }
};

export const getTrajInfoById = async (id: string): Promise<TrajInfo> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_info/${id}`);
    return transformTrajInfobyIDResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj info by ID:', error);
    throw error;
  }
};

export const getTrajPoseActById = async (
  id: string,
): Promise<TrajPoseAct[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_pose_act_raw/${id}`, true);
    return transformTrajPoseActResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj pose ist by ID:', error);
    throw error;
  }
};

export const getTrajPoseTransById = async (
  id: string,
): Promise<TrajPoseTrans[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_pose_act/${id}`, true);
    return transformTrajPoseTransResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching transformed pose data:', error);
    throw error;
  }
};

export const getTrajVelActById = async (
  id: string,
): Promise<TrajVelAct[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_vel_act/${id}`, true);
    return transformTrajVelActResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj twist ist by ID:', error);
    throw error;
  }
};

export const getTrajAccelActById = async (
  id: string,
): Promise<TrajAccelAct[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_accel_act/${id}`, true);
    return transformTrajAccelActResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj accel ist by ID:', error);
    throw error;
  }
};

export const getTrajAccelCmdById = async (
  id: string,
): Promise<TrajAccelCmd[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_accel_cmd/${id}`, true);
    return transformTrajAccelCmdResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj accel soll by ID:', error);
    throw error;
  }
};

export const getTrajPositionCmdById = async (
  id: string,
): Promise<TrajPositionCmd[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_position_cmd/${id}`, true);
    return transformTrajPositionCmdResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj position soll by ID:', error);
    throw error;
  }
};

export const getSegmentPositionCmdById = async (
  id: string,
): Promise<TrajPositionCmd[]> => {
  try {
    const result = await fetchFromAPI(
      `/traj/seg_position_cmd/${id}`,
      true,
    );
    return transformTrajPositionCmdResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj position soll by ID:', error);
    throw error;
  }
};

export const getTrajOrientationCmdById = async (
  id: string,
): Promise<TrajOrientationCmd[]> => {
  try {
    const result = await fetchFromAPI(
      `/traj/traj_orientation_cmd/${id}`,
      true,
    );
    return transformTrajOrientationCmdResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj orientation soll by ID:', error);
    throw error;
  }
};

export const getTrajVelCmdById = async (
  id: string,
): Promise<TrajVelCmd[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_vel_cmd/${id}`, true);
    return transformTrajVelCmdResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj twist soll by ID:', error);
    throw error;
  }
};

export const getTrajJointStatesById = async (
  id: string,
): Promise<TrajJointStates[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_joint_states/${id}`, true);
    return transformTrajJointStatesResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj joint states by ID:', error);
    throw error;
  }
};

export const getTrajSetpointsById = async (id: string): Promise<TrajSetpoints[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_setpoints/${id}`, true);
    return transformTrajSetpointsResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj events by ID:', error);
    throw error;
  }
};

export const getSegmentSetpointsById = async (
  id: string,
): Promise<TrajSetpoints[]> => {
  try {
    const result = await fetchFromAPI(`/traj/traj_setpoints/${id}`, true);
    return transformTrajSetpointsResult(result);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching Traj events by ID:', error);
    throw error;
  }
};

export const checkTransformedDataExists = async (
  id: string,
): Promise<boolean> => {
  try {
    const result = await fetchFromAPI(`/traj/check_transformed_data/${id}`);
    return result.exists;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error checking transformed data:', error);
    return false;
  }
};
