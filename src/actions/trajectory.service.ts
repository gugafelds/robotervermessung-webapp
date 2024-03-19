'use server';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformTrajectoriesDataResult,
  transformTrajectoriesHeadersResult,
  transformTrajectoryResult,
} from '@/src/lib/transformer';
import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryHeaderRaw,
} from '@/types/main';

export const getTrajectoriesHeader = async () => {
  const mongo = await getMongoDb();

  const trajectoriesHeaderResult = await mongo
    .collection('header')
    .find<TrajectoryHeaderRaw>({})
    .sort({ recording_date: -1 })
    .toArray();

  return transformTrajectoriesHeadersResult(trajectoriesHeaderResult);
};

export const getTrajectoriesData = async () => {
  const mongo = await getMongoDb();

  const trajectoriesDataResult = await mongo
    .collection('data')
    .find<TrajectoryDataRaw>({})
    .sort({ recording_date: -1 })
    .toArray();

  if (!trajectoriesDataResult) {
    return {} as TrajectoryData[];
  }

  return transformTrajectoriesDataResult(trajectoriesDataResult);
};

export const getTrajectoryById = async (id: string) => {
  const mongo = await getMongoDb();

  const trajectoryResult = await mongo
    .collection('data')
    .find<TrajectoryDataRaw>({ trajectory_header_id: id })
    .next();

  if (!trajectoryResult) {
    return {} as TrajectoryData;
  }

  return transformTrajectoryResult(trajectoryResult);
};
