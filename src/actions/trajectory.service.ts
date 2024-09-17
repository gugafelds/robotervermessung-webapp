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
  transformSegmentsHeadersResult,
} from '@/src/lib/transformer';
import {
  transformBahnAccelIstResult,
  transformBahnInfoResult,
  transformBahnPoseIstResult,
  transformBahnPositionSollResult,
  transformBahnTwistIstResult,
} from '@/src/lib/transformer-postgresql';
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
  SegmentHeaderRaw,
  BahnInfo,
  BahnInfoRaw,
  BahnPoseIst,
  BahnPoseIstRaw,
  BahnTwistIstRaw,
  BahnTwistIst,
  BahnAccelIstRaw,
  BahnAccelIst,
  BahnPositionSollRaw,
  BahnPositionSoll,
} from '@/types/main';

export const getTrajectoriesHeader = async () => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const trajectoriesHeaderResult = await mongo
    .collection('header')
    .find<TrajectoryHeaderRaw>({})
    .sort({ recording_date: -1 })
    .toArray();
=======
  const trajectoriesHeaderResult = await queryPostgres<TrajectoryHeaderRaw>(
    'SELECT * FROM trajectories.trajectories_header ORDER BY start_time DESC',
  );
>>>>>>> 99b4cb8 (segments included)

  revalidatePath('/trajectories');
  return transformTrajectoriesHeadersResult(trajectoriesHeaderResult);
};

export const getSegmentsHeader = async () => {
  const segmentsHeaderResult = await queryPostgres<SegmentHeaderRaw>(
    'SELECT * FROM trajectories.trajectories_header_segments ORDER BY end_time DESC',
  );

  revalidatePath('/trajectories');
  return transformSegmentsHeadersResult(segmentsHeaderResult);
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
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const trajectoryResult = await mongo
    .collection('data')
    .find<TrajectoryDataRaw>({ trajectory_header_id: id })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_data WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_data WHERE trajectory_header_id = $1';

  const [trajectoryResult] = await queryPostgres<TrajectoryDataRaw>(query, [id]);
>>>>>>> 99b4cb8 (segments included)

  if (!trajectoryResult) {
    return {} as TrajectoryData;
  }

  revalidatePath('/trajectories');
  return transformTrajectoryResult(trajectoryResult);
};

export const getEuclideanMetricsById = async (id: string) => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const euclideanMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryEuclideanMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'euclidean',
    })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_metrics_euclidean WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_metrics_euclidean WHERE trajectory_header_id = $1';
  
  const [euclideanMetricsResult] =
    await queryPostgres<TrajectoryEuclideanMetricsRaw>(
      query
      ,[id]);
>>>>>>> 99b4cb8 (segments included)

  if (!euclideanMetricsResult) {
    return {} as TrajectoryEuclideanMetrics;
  }

  revalidatePath('/trajectories');
  return transformEuclideanMetricResult(euclideanMetricsResult);
};

export const getDTWJohnenMetricsById = async (id: string) => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const dtwJohnenMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWJohnenMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'dtw_johnen',
    })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_metrics_dtw_johnen WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_metrics_dtw_johnen WHERE trajectory_header_id = $1';
  
  const [dtwJohnenMetricsResult] = await queryPostgres<TrajectoryDTWJohnenMetricsRaw>(
    query,
    [id],
  );
>>>>>>> 99b4cb8 (segments included)

  if (!dtwJohnenMetricsResult) {
    return {} as TrajectoryDTWJohnenMetrics;
  }

  revalidatePath('/trajectories');
  return transformDTWJohnenMetricResult(dtwJohnenMetricsResult);
};

export const getDTWMetricsById = async (id: string) => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const dtwMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDTWMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'dtw_standard',
    })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_metrics_dtw_standard WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_metrics_dtw_standard WHERE trajectory_header_id = $1';
  
  const [dtwMetricsResult] = await queryPostgres<TrajectoryDTWMetricsRaw>(
    query,
    [id],
  );
>>>>>>> 99b4cb8 (segments included)

  if (!dtwMetricsResult) {
    return {} as TrajectoryDTWMetrics;
  }

  revalidatePath('/trajectories');
  return transformDTWMetricResult(dtwMetricsResult);
};

export const getDFDMetricsById = async (id: string) => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const dfdMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryDFDMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'discrete_frechet',
    })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_metrics_discrete_frechet WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_metrics_discrete_frechet WHERE trajectory_header_id = $1';
  
  const [dfdMetricsResult] = await queryPostgres<TrajectoryDFDMetricsRaw>(
    query,
    [id],
  );
>>>>>>> 99b4cb8 (segments included)

  if (!dfdMetricsResult) {
    return {} as TrajectoryDFDMetrics;
  }

  revalidatePath('/trajectories');
  return transformDFDMetricResult(dfdMetricsResult);
};

export const getLCSSMetricsById = async (id: string) => {
<<<<<<< HEAD
  const mongo = await getMongoDb();

  const lcssMetricsResult = await mongo
    .collection('metrics')
    .find<TrajectoryLCSSMetricsRaw>({
      trajectory_header_id: id,
      metric_type: 'lcss',
    })
    .next();
=======
  const isSegment = id.includes('_');
  const query = isSegment
    ? 'SELECT * FROM trajectories.trajectories_metrics_lcss WHERE segment_id = $1'
    : 'SELECT * FROM trajectories.trajectories_metrics_lcss WHERE trajectory_header_id = $1';
  
  const [lcssMetricsResult] = await queryPostgres<TrajectoryLCSSMetricsRaw>(
    query,
    [id],
  );
>>>>>>> 99b4cb8 (segments included)

  if (!lcssMetricsResult) {
    return {} as TrajectoryLCSSMetrics;
  }

  revalidatePath('/trajectories');
  return transformLCSSMetricResult(lcssMetricsResult);
};


/* NEW VERSION */

export const getBahnInfo = async () => {
  const bahnInfoResult = await queryPostgres<BahnInfoRaw>(
    'SELECT * FROM bewegungsdaten.bahn_info ORDER BY recording_date DESC',
  );

  revalidatePath('/trajectories');
  return transformBahnInfoResult(bahnInfoResult);
};

export const getBahnPoseIstById = async (id: string): Promise<BahnPoseIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_pose_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;
  
  const result = await queryPostgres(query, [id]);
  
  // Explicit type checking and conversion
  let bahnPoseIstResult: BahnPoseIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnPoseIstResult = result[0] as BahnPoseIstRaw[];
  } else if (Array.isArray(result)) {
    bahnPoseIstResult = result as BahnPoseIstRaw[];
  } else {
    bahnPoseIstResult = [];
  }
  
  if (bahnPoseIstResult.length === 0) {
    return [];
  }
  
  revalidatePath('/trajectories');
  return transformBahnPoseIstResult(bahnPoseIstResult);
};

export const getBahnTwistIstById = async (id: string): Promise<BahnTwistIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_twist_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;
  
  const result = await queryPostgres(query, [id]);
  
  // Explicit type checking and conversion
  let bahnTwistIstResult: BahnTwistIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnTwistIstResult = result[0] as BahnTwistIstRaw[];
  } else if (Array.isArray(result)) {
    bahnTwistIstResult = result as BahnTwistIstRaw[];
  } else {
    bahnTwistIstResult = [];
  }
  
  if (bahnTwistIstResult.length === 0) {
    return [];
  }
  
  revalidatePath('/trajectories');
  return transformBahnTwistIstResult(bahnTwistIstResult);
};

export const getBahnAccelIstById = async (id: string): Promise<BahnAccelIst[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_accel_ist 
    WHERE bahn_id = $1 
    ORDER BY timestamp ASC
  `;
  
  const result = await queryPostgres(query, [id]);
  
  // Explicit type checking and conversion
  let bahnAccelIstResult: BahnAccelIstRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnAccelIstResult = result[0] as BahnAccelIstRaw[];
  } else if (Array.isArray(result)) {
    bahnAccelIstResult = result as BahnAccelIstRaw[];
  } else {
    bahnAccelIstResult = [];
  }
  
  if (bahnAccelIstResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnAccelIstResult(bahnAccelIstResult);
};

export const getBahnPositionSollById = async (id: string): Promise<BahnPositionSoll[]> => {
  const query = `
    SELECT * FROM bewegungsdaten.bahn_position_soll
    WHERE bahn_id = $1
    ORDER BY timestamp ASC
  `;

  const result = await queryPostgres(query, [id]);

  // Explicit type checking and conversion
  let bahnPositionSollResult: BahnPositionSollRaw[];
  if (Array.isArray(result) && result.length > 0 && Array.isArray(result[0])) {
    bahnPositionSollResult = result[0] as BahnPositionSollRaw[];
  } else if (Array.isArray(result)) {
    bahnPositionSollResult = result as BahnPositionSollRaw[];
  } else {
    bahnPositionSollResult = [];
  }

  if (bahnPositionSollResult.length === 0) {
    return [];
  }

  revalidatePath('/trajectories');
  return transformBahnPositionSollResult(bahnPositionSollResult);
};
