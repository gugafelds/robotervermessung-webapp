'use server';

import { ObjectId } from 'mongodb';

import { getMongoDb } from '@/src/lib/mongodb';

export const getTrajectories = async () => {
  const mongo = await getMongoDb();

  return mongo
    .collection('trajectories')
    .find<any>({}, { projection: { data: 0 } })
    .sort({ recording_date: -1 })
    .toArray();
};

export const getTrajectoryById = async (id: string) => {
  const mongo = await getMongoDb();

  return mongo
    .collection('trajectories')
    .find<any>({ _id: new ObjectId(id) })
    .next();
};
