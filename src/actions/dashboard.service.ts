'use server';

import { revalidatePath } from 'next/cache';

import { queryPostgres } from '../lib/postgresql';

interface CountResult {
  count: number;
}

export const getBahnCount = async (): Promise<number> => {
  try {
    const result = await queryPostgres<CountResult>(
      'SELECT COUNT(*) as count FROM bewegungsdaten.bahn_info',
    );

    revalidatePath('/dashboard');

    if (result.length === 0) {
      throw new Error('No result returned from count query');
    }

    return result[0].count;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching bahn count:', error);
    throw error; // or handle it as appropriate for your application
  }
};
