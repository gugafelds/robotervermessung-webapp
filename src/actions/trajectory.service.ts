'use server';

import { revalidatePath } from 'next/cache';

import {
  transformBahnAccelIstResult,
  transformBahnEventsResult,
  transformBahnInfobyIDResult,
  transformBahnInfoResult,
  transformBahnJointStatesResult,
  transformBahnOrientationSollResult,
  transformBahnPoseIstResult,
  transformBahnPositionSollResult,
  transformBahnTwistIstResult,
  transformBahnTwistSollResult,
} from '@/src/lib/transformer-postgresql';
import type {
  BahnAccelIst,
  BahnAccelIstRaw,
  BahnEvents,
  BahnEventsRaw,
  BahnInfo,
  BahnInfoRaw,
  BahnJointStates,
  BahnJointStatesRaw,
  BahnOrientationSoll,
  BahnOrientationSollRaw,
  BahnPoseIst,
  BahnPoseIstRaw,
  BahnPositionSoll,
  BahnPositionSollRaw,
  BahnTwistIst,
  BahnTwistIstRaw,
  BahnTwistSoll,
  BahnTwistSollRaw,
} from '@/types/main';

import { queryPostgres } from '../lib/postgresql';

/* NEW VERSION */

export const getBahnInfo = async () => {
  const bahnInfoResult = await queryPostgres<BahnInfoRaw>(
    'SELECT * FROM bewegungsdaten.bahn_info ORDER BY recording_date DESC',
  );

  revalidatePath('/trajectories');
  return transformBahnInfoResult(bahnInfoResult);
};

export const getBahnInfoById = async (id: string): Promise<BahnInfo | null> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_info
    WHERE bahn_id = $1
  `;
  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnInfoResult: BahnInfoRaw | null;
  if (Array.isArray(result) && result.length > 0) {
    bahnInfoResult = result[0] as BahnInfoRaw;
  } else {
    bahnInfoResult = null;
  }

  if (!bahnInfoResult) {
    return null;
  }

  revalidatePath('/trajectories');
  return transformBahnInfobyIDResult(bahnInfoResult);
};

export const getBahnPoseIstById = async (
  id: string,
): Promise<BahnPoseIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_pose_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnPoseIstResult: BahnPoseIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnPoseIstResult = result[0] as BahnPoseIstRaw[];
  } else if (Array.isArray(result)) {
    bahnPoseIstResult = result as BahnPoseIstRaw[];
  } else {
    bahnPoseIstResult = [];
  }

  if (bahnPoseIstResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnPoseIstResult(bahnPoseIstResult);
};

export const getBahnTwistIstById = async (
  id: string,
): Promise<BahnTwistIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_twist_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnTwistIstResult: BahnTwistIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnTwistIstResult = result[0] as BahnTwistIstRaw[];
  } else if (Array.isArray(result)) {
    bahnTwistIstResult = result as BahnTwistIstRaw[];
  } else {
    bahnTwistIstResult = [];
  }

  if (bahnTwistIstResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnTwistIstResult(bahnTwistIstResult);
};

export const getBahnAccelIstById = async (
  id: string,
): Promise<BahnAccelIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_accel_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnAccelIstResult: BahnAccelIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnAccelIstResult = result[0] as BahnAccelIstRaw[];
  } else if (Array.isArray(result)) {
    bahnAccelIstResult = result as BahnAccelIstRaw[];
  } else {
    bahnAccelIstResult = [];
  }

  if (bahnAccelIstResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnAccelIstResult(bahnAccelIstResult);
};

export const getBahnPositionSollById = async (
  id: string,
): Promise<BahnPositionSoll[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_position_soll
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnPositionSollResult: BahnPositionSollRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnPositionSollResult = result[0] as BahnPositionSollRaw[];
  } else if (Array.isArray(result)) {
    bahnPositionSollResult = result as BahnPositionSollRaw[];
  } else {
    bahnPositionSollResult = [];
  }

  if (bahnPositionSollResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnPositionSollResult(bahnPositionSollResult);
};

export const getBahnOrientationSollById = async (
  id: string,
): Promise<BahnOrientationSoll[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_orientation_soll
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnOrientationSollResult: BahnOrientationSollRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnOrientationSollResult = result[0] as BahnOrientationSollRaw[];
  } else if (Array.isArray(result)) {
    bahnOrientationSollResult = result as BahnOrientationSollRaw[];
  } else {
    bahnOrientationSollResult = [];
  }

  if (bahnOrientationSollResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnOrientationSollResult(bahnOrientationSollResult);
};

export const getBahnTwistSollById = async (
  id: string,
): Promise<BahnTwistSoll[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_twist_soll
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnTwistSollResult: BahnTwistSollRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnTwistSollResult = result[0] as BahnTwistSollRaw[];
  } else if (Array.isArray(result)) {
    bahnTwistSollResult = result as BahnTwistSollRaw[];
  } else {
    bahnTwistSollResult = [];
  }

  if (bahnTwistSollResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnTwistSollResult(bahnTwistSollResult);
};

export const getBahnJointStatesById = async (
  id: string,
): Promise<BahnJointStates[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_joint_states
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnJointStatesResult: BahnJointStatesRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnJointStatesResult = result[0] as BahnJointStatesRaw[];
  } else if (Array.isArray(result)) {
    bahnJointStatesResult = result as BahnJointStatesRaw[];
  } else {
    bahnJointStatesResult = [];
  }

  if (bahnJointStatesResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnJointStatesResult(bahnJointStatesResult);
};

export const getBahnEventsById = async (id: string): Promise<BahnEvents[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_events
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnEventsResult: BahnEventsRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnEventsResult = result[0] as BahnEventsRaw[];
  } else if (Array.isArray(result)) {
    bahnEventsResult = result as BahnEventsRaw[];
  } else {
    bahnEventsResult = [];
  }

  if (bahnEventsResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnEventsResult(bahnEventsResult);
};
