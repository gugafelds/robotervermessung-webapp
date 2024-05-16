import { revalidatePath } from 'next/cache';

import { getMongoDb } from '@/src/lib/mongodb';

export const getTrajectoriesCount = async () => {
  const mongo = await getMongoDb();

  revalidatePath('/dashboard');
  return mongo.collection('header').countDocuments();
};
