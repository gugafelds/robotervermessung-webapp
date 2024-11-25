'use server';

import {
  transformBahnAccelIstResult,
  transformBahnEventsResult,
  transformBahnInfobyIDResult,
  transformBahnInfoResult,
  transformBahnJointStatesResult,
  transformBahnOrientationSollResult,
  transformBahnPoseIstResult,
  transformBahnPoseTransResult,
  transformBahnPositionSollResult,
  transformBahnTwistIstResult,
  transformBahnTwistSollResult,
} from '@/src/lib/transformer';
import type {
  BahnAccelIst,
  BahnEvents,
  BahnInfo,
  BahnJointStates,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
  BahnTwistIst,
  BahnTwistSoll,
} from '@/types/main';

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
    cache: 'force-cache',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
}

export const getAllBahnInfo = async (): Promise<BahnInfo[]> => {
  try {
    const result = await fetchFromAPI('/bahn/bahn_info');
    return transformBahnInfoResult(result.bahn_info);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching all Bahn info:', error);
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
