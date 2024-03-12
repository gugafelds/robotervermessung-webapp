'use server';

import { ObjectId } from 'mongodb';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformTrajectoriesResult,
  transformTrajectoryResult,
} from '@/src/lib/transformer';
import type { Trajectory, TrajectoryRaw } from '@/types/main';

export const getTrajectories = async () => {
  const mongo = await getMongoDb();

  const trajectoriesResult = await mongo
    .collection('trajectories')
    .find<TrajectoryRaw>({}, { projection: { data: 0 } })
    .sort({ recording_date: -1 })
    .toArray();

  return transformTrajectoriesResult(trajectoriesResult);
};

export const getTrajectoryById = async (id: string) => {
  const mongo = await getMongoDb();

  const trajectoryResult = await mongo
    .collection('trajectories')
    .find<TrajectoryRaw>({ _id: new ObjectId(id) })
    .next();

  if (!trajectoryResult) {
    return {} as Trajectory;
  }

  return transformTrajectoryResult(trajectoryResult);
};
