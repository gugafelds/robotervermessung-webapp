import { getMongoDb } from '@/src/lib/mongodb';

export const getTrajectoriesCount = async () => {
  const mongo = await getMongoDb();

  return mongo.collection('header').countDocuments();
};
