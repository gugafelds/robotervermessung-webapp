'use server';

import { getMongoDb } from '@/src/lib/mongodb';
import {
  transformMetricResult,
  transformTrajectoriesDataResult,
  transformTrajectoriesEuclideanMetricsResult,
  transformTrajectoriesDTWJohnenMetricsResult,
  transformTrajectoriesHeadersResult,
  transformTrajectoryResult,
  transformDTWJohnenMetricResult,
} from '@/src/lib/transformer';
import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryEuclideanMetrics,
  TrajectoryEuclideanMetricsRaw,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWJohnenMetricsRaw,
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

export const getTrajectoriesEuclideanMetrics = async () => {
  const mongo = await getMongoDb();

  const trajectoriesEuclideanMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryEuclideanMetricsRaw>({ metric_type: "euclidean"})
    .sort({ recording_date: -1 })
    .toArray();

  return transformTrajectoriesEuclideanMetricsResult(
    trajectoriesEuclideanMetricsResult,
  );
};



export const getTrajectoriesDTWJohnenMetrics = async () => {
  const mongo = await getMongoDb();

  const trajectoriesDTWJohnenMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWJohnenMetricsRaw>({})
    .sort({ recording_date: -1 })
    .toArray();

  return transformTrajectoriesDTWJohnenMetricsResult(
    trajectoriesDTWJohnenMetricsResult,
  );
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

export const getEuclideanMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const euclideanMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryEuclideanMetricsRaw>({ trajectory_header_id: id })
    .next();

  if (!euclideanMetricsResult) {
    return {} as TrajectoryEuclideanMetrics;
  }

  return transformMetricResult(euclideanMetricsResult);
};

export const getDTWJohnenMetricsById = async (id: string) => {
  const mongo = await getMongoDb();

  const dtwJohnenMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWJohnenMetricsRaw>({ trajectory_header_id: id })
    .next();

  if (!dtwJohnenMetricsResult) {
    return {} as TrajectoryDTWJohnenMetrics;
  }

  return transformDTWJohnenMetricResult(dtwJohnenMetricsResult);
};
