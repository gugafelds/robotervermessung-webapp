import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryEuclideanMetrics,
  TrajectoryEuclideanMetricsRaw,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWJohnenMetricsRaw,
  TrajectoryHeader,
  TrajectoryHeaderRaw,
} from '@/types/main';

export const transformTrajectoryResult = (
  trajectoryRaw: TrajectoryDataRaw,
): TrajectoryData => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  timestampIst: trajectoryRaw.timestamp_ist,
  xIst: trajectoryRaw.x_ist,
  yIst: trajectoryRaw.y_ist,
  zIst: trajectoryRaw.z_ist,
  q1Ist: trajectoryRaw.q1_ist,
  q2Ist: trajectoryRaw.q2_ist,
  q3Ist: trajectoryRaw.q3_ist,
  q4Ist: trajectoryRaw.q4_ist,
  timestampSoll: trajectoryRaw.timestamp_soll,
  xSoll: trajectoryRaw.x_soll,
  ySoll: trajectoryRaw.y_soll,
  zSoll: trajectoryRaw.z_soll,
  q1Soll: trajectoryRaw.q1_soll,
  q2Soll: trajectoryRaw.q2_soll,
  q3Soll: trajectoryRaw.q3_soll,
  q4Soll: trajectoryRaw.q4_soll,
  jointStateIst: trajectoryRaw.joint_state_ist,
  jointStateSoll: trajectoryRaw.joint_state_soll,
});

export const transformMetricResult = (
  trajectoryRaw: TrajectoryEuclideanMetricsRaw,
): TrajectoryEuclideanMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  euclideanMaxDistance: trajectoryRaw.euclidean_max_distance,
  euclideanAverageDistance: trajectoryRaw.euclidean_average_distance,
  euclideanStandardDeviation: trajectoryRaw.euclidean_standard_deviation,
  euclideanIntersections: trajectoryRaw.euclidean_intersections,
  metricType: trajectoryRaw.metric_type,
});

export const transformDTWJohnenMetricResult = (
  trajectoryRaw: TrajectoryDTWJohnenMetricsRaw,
): TrajectoryDTWJohnenMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  dtwJohnenMaxDistance: trajectoryRaw.dtw_max_distance,
  dtwJohnenAverageDistance: trajectoryRaw.dtw_average_distance,
  dtwJohnenX: trajectoryRaw.dtw_X,
  dtwJohnenY: trajectoryRaw.dtw_Y,
  dtwAccDist: trajectoryRaw.dtw_accdist,
  dtwPath: trajectoryRaw.dtw_path,
  metricType: trajectoryRaw.metric_type
});

export const transformTrajectoriesDataResult = (
  trajectoriesDataRaw: TrajectoryDataRaw[],
): TrajectoryData[] => {
  return trajectoriesDataRaw.map(
    (trajectoryRaw): TrajectoryData => ({
      _id: trajectoryRaw._id,
      trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
      timestampIst: trajectoryRaw.timestamp_ist,
      xIst: trajectoryRaw.x_ist,
      yIst: trajectoryRaw.y_ist,
      zIst: trajectoryRaw.z_ist,
      q1Ist: trajectoryRaw.q1_ist,
      q2Ist: trajectoryRaw.q2_ist,
      q3Ist: trajectoryRaw.q3_ist,
      q4Ist: trajectoryRaw.q4_ist,
      timestampSoll: trajectoryRaw.timestamp_soll,
      xSoll: trajectoryRaw.x_soll,
      ySoll: trajectoryRaw.y_soll,
      zSoll: trajectoryRaw.z_soll,
      q1Soll: trajectoryRaw.q1_soll,
      q2Soll: trajectoryRaw.q2_soll,
      q3Soll: trajectoryRaw.q3_soll,
      q4Soll: trajectoryRaw.q4_soll,
      jointStateIst: trajectoryRaw.joint_state_ist,
      jointStateSoll: trajectoryRaw.joint_state_soll,
    }),
  );
};

export const transformTrajectoriesHeadersResult = (
  trajectoriesRaw: TrajectoryHeaderRaw[],
): TrajectoryHeader[] => {
  return trajectoriesRaw.map(
    (trajectory): TrajectoryHeader => ({
      _id: trajectory._id,
      dataId: trajectory.data_id,
      robotName: trajectory.robot_name,
      robotModel: trajectory.robot_model,
      trajectoryType: trajectory.trajectory_type,
      carthesian: trajectory.carthesian,
      pathSolver: trajectory.path_solver,
      recordingDate: trajectory.recording_date,
      realRobot: trajectory.real_robot,
      numberPointsIst: trajectory.number_of_points_ist,
      numberPointsSoll: trajectory.number_of_points_soll,
      SampleFrequencyIst: trajectory.sample_frequency_ist,
      SampleFrequencySoll: trajectory.sample_frequency_soll,
    }),
  );
};

export const transformTrajectoriesEuclideanMetricsResult = (
  trajectoriesEuclideanMetricsRaw: TrajectoryEuclideanMetricsRaw[],
): TrajectoryEuclideanMetrics[] => {
  return trajectoriesEuclideanMetricsRaw.map(
    (trajectory): TrajectoryEuclideanMetrics => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      euclideanMaxDistance: trajectory.euclidean_max_distance,
      euclideanAverageDistance: trajectory.euclidean_average_distance,
      euclideanStandardDeviation: trajectory.euclidean_standard_deviation,
      euclideanIntersections: trajectory.euclidean_intersections,
      metricType: trajectory.metric_type,
    }),
  );
};

export const transformTrajectoriesDTWJohnenMetricsResult = (
  trajectoriesDTWJohnenMetricsRaw: TrajectoryDTWJohnenMetricsRaw[],
): TrajectoryDTWJohnenMetrics[] => {
  return trajectoriesDTWJohnenMetricsRaw.map(
    (trajectory): TrajectoryDTWJohnenMetrics => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      dtwJohnenMaxDistance: trajectory.dtw_max_distance,
      dtwJohnenAverageDistance: trajectory.dtw_average_distance,
      dtwJohnenX: trajectory.dtw_X,
      dtwJohnenY: trajectory.dtw_Y,
      dtwAccDist: trajectory.dtw_accdist,
      dtwPath: trajectory.dtw_path,
      metricType: trajectory.metric_type
    }),
  );
};

