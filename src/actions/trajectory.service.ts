'use server';

import { revalidatePath } from 'next/cache';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformDTWJohnenMetricResult,
  transformEuclideanMetricResult,
  transformTrajectoriesDataResult,
  transformTrajectoriesHeadersResult,
  transformTrajectoryResult,
} from '@/src/lib/transformer';
import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWJohnenMetricsRaw,
  TrajectoryEuclideanMetrics,
  TrajectoryEuclideanMetricsRaw,
  TrajectoryHeaderRaw,
} from '@/types/main';

export const getTrajectoriesHeader = async () => {
  const mongo = await getMongoDb();

  const trajectoriesHeaderResult = await mongo
    .collection('header')
    .find<TrajectoryHeaderRaw>({})
    .sort({ recording_date: -1 })
    .toArray();

  revalidatePath('/trajectories');
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

  revalidatePath('/trajectories');
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

  revalidatePath('/trajectories');
  return transformTrajectoryResult(trajectoryResult);
};

export const getEuclideanMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const euclideanMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryEuclideanMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'euclidean',
    })
    .next();

  if (!euclideanMetricsResult) {
    return {} as TrajectoryEuclideanMetrics;
  }

  revalidatePath('/trajectories');
  return transformEuclideanMetricResult(euclideanMetricsResult);
};

export const getDTWJohnenMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const dtwJohnenMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWJohnenMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'dtw_johnen',
    })
    .next();

  if (!dtwJohnenMetricsResult) {
    return {} as TrajectoryDTWJohnenMetrics;
  }

  revalidatePath('/trajectories');
  return transformDTWJohnenMetricResult(dtwJohnenMetricsResult);
};
