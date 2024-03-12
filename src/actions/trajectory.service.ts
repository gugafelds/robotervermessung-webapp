'use server';

import { getMongoDb } from '@/src/lib/mongodb';

export const getTrajectories = async () => {
  const mongo = await getMongoDb();

  return mongo
    .collection('trajectories')
    .find<any>({}, { projection: { data: 0 } })
    .sort({ recording_date: -1 })
    .toArray();
};
