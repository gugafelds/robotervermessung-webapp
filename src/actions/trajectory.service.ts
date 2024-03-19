'use server';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformTrajectoriesResult,
  transformTrajectoryResult,
} from '@/src/lib/transformer';
import type { AxisData, AxisDataRaw, Trajectory } from '@/types/main';

export const getTrajectories = async () => {
  const mongo = await getMongoDb();

  const trajectoriesResult = await mongo
    .collection('header')
    .find<Trajectory>({})
    .sort({ recording_date: -1 })
    .toArray();

  return transformTrajectoriesResult(trajectoriesResult);
};

export const getTrajectoryById = async (id: string) => {
  const mongo = await getMongoDb();

  const trajectoryResult = await mongo
    .collection('data')
    .find<AxisDataRaw>({ trajectory_header_id: id })
    .next();

  if (!trajectoryResult) {
    return {} as AxisData;
  }

  return transformTrajectoryResult(trajectoryResult);
};
