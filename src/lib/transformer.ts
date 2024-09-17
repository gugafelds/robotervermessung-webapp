import type {
  SegmentHeader,
  SegmentHeaderRaw,
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
  TrajectoryHeader,
  TrajectoryHeaderRaw,
  TrajectoryLCSSMetrics,
  TrajectoryLCSSMetricsRaw,
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
  tcpVelocityIst: trajectoryRaw.tcp_velocity_ist,
  tcpAcceleration: trajectoryRaw.tcp_acceleration,
  jointStateIst: trajectoryRaw.joint_state_ist,
  timestampSoll: trajectoryRaw.timestamp_soll,
  xSoll: trajectoryRaw.x_soll,
  ySoll: trajectoryRaw.y_soll,
  zSoll: trajectoryRaw.z_soll,
  q1Soll: trajectoryRaw.q1_soll,
  q2Soll: trajectoryRaw.q2_soll,
  q3Soll: trajectoryRaw.q3_soll,
  q4Soll: trajectoryRaw.q4_soll,
  tcpVelocitySoll: trajectoryRaw.tcp_velocity_soll,
  jointStateSoll: trajectoryRaw.joint_state_soll,
  segmentId: trajectoryRaw.segment_id,
});

export const transformEuclideanMetricResult = (
  trajectoryRaw: TrajectoryEuclideanMetricsRaw,
): TrajectoryEuclideanMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  euclideanDistances: trajectoryRaw.euclidean_distances,
  euclideanMaxDistance: trajectoryRaw.euclidean_max_distance,
  euclideanAverageDistance: trajectoryRaw.euclidean_average_distance,
  euclideanStandardDeviation: trajectoryRaw.euclidean_standard_deviation,
  euclideanIntersections: trajectoryRaw.euclidean_intersections,
  metricType: trajectoryRaw.metric_type,
});

export const transformDTWMetricResult = (
  trajectoryRaw: TrajectoryDTWMetricsRaw,
): TrajectoryDTWMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  dtwMaxDistance: trajectoryRaw.dtw_max_distance,
  dtwAverageDistance: trajectoryRaw.dtw_average_distance,
  dtwDistances: trajectoryRaw.dtw_distances,
  dtwX: trajectoryRaw.dtw_X,
  dtwY: trajectoryRaw.dtw_Y,
  dtwAccDist: trajectoryRaw.dtw_accdist,
  dtwPath: trajectoryRaw.dtw_path,
  metricType: trajectoryRaw.metric_type,
});

export const transformDTWJohnenMetricResult = (
  trajectoryRaw: TrajectoryDTWJohnenMetricsRaw,
): TrajectoryDTWJohnenMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  dtwJohnenMaxDistance: trajectoryRaw.dtw_max_distance,
  dtwJohnenAverageDistance: trajectoryRaw.dtw_average_distance,
  dtwJohnenDistances: trajectoryRaw.dtw_distances,
  dtwJohnenX: trajectoryRaw.dtw_x,
  dtwJohnenY: trajectoryRaw.dtw_y,
  dtwAccDist: trajectoryRaw.dtw_accdist,
  dtwPath: trajectoryRaw.dtw_path,
  metricType: trajectoryRaw.metric_type,
});

export const transformDFDMetricResult = (
  trajectoryRaw: TrajectoryDFDMetricsRaw,
): TrajectoryDFDMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  dfdMaxDistance: trajectoryRaw.frechet_max_distance,
  dfdAverageDistance: trajectoryRaw.frechet_average_distance,
  dfdDistances: trajectoryRaw.frechet_distances,
  dfdAccDist: trajectoryRaw.frechet_accdist,
  dfdPath: trajectoryRaw.frechet_path,
  metricType: trajectoryRaw.metric_type,
});

export const transformLCSSMetricResult = (
  trajectoryRaw: TrajectoryLCSSMetricsRaw,
): TrajectoryLCSSMetrics => ({
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  lcssMaxDistance: trajectoryRaw.lcss_max_distance,
  lcssAverageDistance: trajectoryRaw.lcss_average_distance,
  lcssDistances: trajectoryRaw.lcss_distances,
  lcssAccDist: trajectoryRaw.lcss_accdist,
  lcssPath: trajectoryRaw.lcss_path,
  lcssX: trajectoryRaw.lcss_X,
  lcssY: trajectoryRaw.lcss_Y,
  lcssScore: trajectoryRaw.lcss_score,
  lcssThreshold: trajectoryRaw.lcss_threshold,
  metricType: trajectoryRaw.metric_type,
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
      tcpVelocityIst: trajectoryRaw.tcp_velocity_ist,
      tcpAcceleration: trajectoryRaw.tcp_acceleration,
      jointStateIst: trajectoryRaw.joint_state_ist,
      timestampSoll: trajectoryRaw.timestamp_soll,
      xSoll: trajectoryRaw.x_soll,
      ySoll: trajectoryRaw.y_soll,
      zSoll: trajectoryRaw.z_soll,
      q1Soll: trajectoryRaw.q1_soll,
      q2Soll: trajectoryRaw.q2_soll,
      q3Soll: trajectoryRaw.q3_soll,
      q4Soll: trajectoryRaw.q4_soll,
      tcpVelocitySoll: trajectoryRaw.tcp_velocity_soll,
      jointStateSoll: trajectoryRaw.joint_state_soll,
      segmentId: trajectoryRaw.segment_id,
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
      SourceDataIst: trajectory.source_data_ist,
      SourceDataSoll: trajectory.source_data_soll,
      startTime: trajectory.start_time,
      endTime: trajectory.end_time,
    }),
  );
};

export const transformSegmentsHeadersResult = (
  trajectoriesRaw: SegmentHeaderRaw[],
): SegmentHeader[] => {
  return trajectoriesRaw.map(
    (trajectory): SegmentHeader => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      segmentId: trajectory.segment_id,
      startTime: trajectory.start_time,
      endTime: trajectory.end_time,
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
      euclideanDistances: trajectory.euclidean_distances,
      euclideanMaxDistance: trajectory.euclidean_max_distance,
      euclideanAverageDistance: trajectory.euclidean_average_distance,
      euclideanStandardDeviation: trajectory.euclidean_standard_deviation,
      euclideanIntersections: trajectory.euclidean_intersections,
      metricType: trajectory.metric_type,
    }),
  );
};

export const transformTrajectoriesDTWMetricsResult = (
  trajectoriesDTWMetricsRaw: TrajectoryDTWMetricsRaw[],
): TrajectoryDTWMetrics[] => {
  return trajectoriesDTWMetricsRaw.map(
    (trajectory): TrajectoryDTWMetrics => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      dtwMaxDistance: trajectory.dtw_max_distance,
      dtwAverageDistance: trajectory.dtw_average_distance,
      dtwDistances: trajectory.dtw_distances,
      dtwX: trajectory.dtw_X,
      dtwY: trajectory.dtw_Y,
      dtwAccDist: trajectory.dtw_accdist,
      dtwPath: trajectory.dtw_path,
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
      dtwJohnenDistances: trajectory.dtw_distances,
      dtwJohnenX: trajectory.dtw_x,
      dtwJohnenY: trajectory.dtw_y,
      dtwAccDist: trajectory.dtw_accdist,
      dtwPath: trajectory.dtw_path,
      metricType: trajectory.metric_type,
    }),
  );
};

export const transformTrajectoriesDFDMetricsResult = (
  trajectoriesDFDMetricsRaw: TrajectoryDFDMetricsRaw[],
): TrajectoryDFDMetrics[] => {
  return trajectoriesDFDMetricsRaw.map(
    (trajectory): TrajectoryDFDMetrics => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      dfdMaxDistance: trajectory.frechet_max_distance,
      dfdAverageDistance: trajectory.frechet_average_distance,
      dfdDistances: trajectory.frechet_distances,
      dfdAccDist: trajectory.frechet_accdist,
      dfdPath: trajectory.frechet_path,
      metricType: trajectory.metric_type,
    }),
  );
};

export const transformTrajectoriesLCSSMetricsResult = (
  trajectoriesLCSSMetricsRaw: TrajectoryLCSSMetricsRaw[],
): TrajectoryLCSSMetrics[] => {
  return trajectoriesLCSSMetricsRaw.map(
    (trajectory): TrajectoryLCSSMetrics => ({
      _id: trajectory._id,
      trajectoryHeaderId: trajectory.trajectory_header_id,
      lcssMaxDistance: trajectory.lcss_max_distance,
      lcssAverageDistance: trajectory.lcss_average_distance,
      lcssDistances: trajectory.lcss_distances,
      lcssAccDist: trajectory.lcss_accdist,
      lcssPath: trajectory.lcss_path,
      lcssX: trajectory.lcss_X,
      lcssY: trajectory.lcss_Y,
      lcssScore: trajectory.lcss_score,
      lcssThreshold: trajectory.lcss_threshold,
      metricType: trajectory.metric_type,
    }),
  );
};
