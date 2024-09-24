'use server';

import { revalidatePath } from 'next/cache';

import { queryPostgres } from '../lib/postgresql';

interface CountResult {
  count: number;
}

interface ComponentCountResult {
  component: string;
  count: number;
}

interface FrequencyDataResult {
  exact_frequency: number;
  ids: string[];
}

export const getBahnCount = async (): Promise<number> => {
  try {
    const result = await queryPostgres<CountResult>(
      'SELECT COUNT(DISTINCT record_filename) as count FROM bewegungsdaten.bahn_info',
    );

    revalidatePath('/dashboard');

    if (result.length === 0) {
      throw new Error('No result returned from count query');
    }

    return result[0].count;
  } catch (error) {
    console.error('Error fetching bahn count:', error);
    throw error;
  }
};

export const getComponentPointCounts = async (): Promise<
  Record<string, number>
> => {
  try {
    const result = await queryPostgres<ComponentCountResult>(`

      SELECT 'bahnTwistIst' as component, COUNT(*) as count FROM bewegungsdaten.bahn_twist_ist
      UNION ALL
            SELECT 'bahnAccelIst' as component, COUNT(*) as count FROM bewegungsdaten.bahn_accel_ist
      UNION ALL
      SELECT 'bahnPositionSoll' as component, COUNT(*) as count FROM bewegungsdaten.bahn_position_soll
      UNION ALL
      SELECT 'bahnOrientationSoll' as component, COUNT(*) as count FROM bewegungsdaten.bahn_orientation_soll
      UNION ALL
      SELECT 'bahnJointStates' as component, COUNT(*) as count FROM bewegungsdaten.bahn_joint_states
      UNION ALL
      SELECT 'bahnEvents' as component, COUNT(*) as count FROM bewegungsdaten.bahn_events
      UNION ALL
      SELECT 'bahnPoseIst' as component, COUNT(*) as count FROM bewegungsdaten.bahn_pose_ist
      
      
    `);

    revalidatePath('/dashboard');

    return result.reduce(
      (acc, { component, count }) => {
        acc[component] = count;
        return acc;
      },
      {} as Record<string, number>,
    );
  } catch (error) {
    console.error('Error fetching component point counts:', error);
    throw error;
  }
};

export const getFrequencyData = async (): Promise<Record<string, string[]>> => {
  // eslint-disable-next-line no-useless-catch
  try {
    const result = await queryPostgres<FrequencyDataResult>(`
      SELECT 
        CASE 
          WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
          WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
          WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
          ELSE 0
        END as exact_frequency,
        ARRAY_AGG(bahn_id) as ids
      FROM bewegungsdaten.bahn_info
      GROUP BY 
        CASE 
          WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
          WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
          WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
          ELSE 0
        END
      HAVING 
        CASE 
          WHEN frequency_pose_ist > 0 THEN frequency_pose_ist
          WHEN frequency_twist_ist > 0 THEN frequency_twist_ist
          WHEN frequency_accel_ist > 0 THEN frequency_accel_ist
          ELSE 0
        END > 0
      ORDER BY exact_frequency DESC
    `);

    revalidatePath('/dashboard');

    // Group frequencies to nearest 100 Hz
    return result.reduce(
      (acc, { exact_frequency, ids }) => {
        const roundedFrequency = Math.round(exact_frequency / 100) * 100;
        const key = roundedFrequency.toString();
        if (!acc[key]) {
          acc[key] = [];
        }
        acc[key].push(...ids);
        return acc;
      },
      {} as Record<string, string[]>,
    );
  } catch (error) {
    throw error;
  }
};
