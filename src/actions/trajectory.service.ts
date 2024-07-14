'use server';

import { revalidatePath } from 'next/cache';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformDFDMetricResult,
  transformDTWJohnenMetricResult,
  transformDTWMetricResult,
  transformEuclideanMetricResult,
  transformLCSSMetricResult,
  transformTrajectoriesDataResult,
  transformTrajectoriesHeadersResult,
  transformTrajectoryResult,
} from '@/src/lib/transformer';
import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryDFDMetrics,
  TrajectoryDFDMetricsRaw,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWJohnenMetricsRaw,
  TrajectoryDTWMetrics,
  TrajectoryDTWMetricsRaw,
  TrajectoryEuclideanMetrics,
  TrajectoryEuclideanMetricsRaw,
  TrajectoryHeaderRaw,
  TrajectoryLCSSMetrics,
  TrajectoryLCSSMetricsRaw,
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

export const getDTWMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const dtwMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'dtw_standard',
    })
    .next();

  if (!dtwMetricsResult) {
    return {} as TrajectoryDTWMetrics;
  }

  revalidatePath('/trajectories');
  return transformDTWMetricResult(dtwMetricsResult);
};

export const getDFDMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const dfdMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDFDMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'discrete_frechet',
    })
    .next();

  if (!dfdMetricsResult) {
    return {} as TrajectoryDFDMetrics;
  }

  revalidatePath('/trajectories');
  return transformDFDMetricResult(dfdMetricsResult);
};

export const getLCSSMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const lcssMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryLCSSMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'lcss',
    })
    .next();

  if (!lcssMetricsResult) {
    return {} as TrajectoryLCSSMetrics;
  }

  revalidatePath('/trajectories');
  return transformLCSSMetricResult(lcssMetricsResult);
};
