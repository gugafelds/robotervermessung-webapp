import type { ObjectId, Timestamp } from 'mongodb';

export interface TrajectoryDataRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  timestamp_ist: number[];
  x_ist: number[];
  y_ist: number[];
  z_ist: number[];
  q1_ist: number[];
  q2_ist: number[];
  q3_ist: number[];
  q4_ist: number[];
  tcp_velocity_ist: number[];
  tcp_acceleration: number[];
  joint_state_ist: number[];
  timestamp_soll: number[];
  x_soll: number[];
  y_soll: number[];
  z_soll: number[];
  q1_soll: number[];
  q2_soll: number[];
  q3_soll: number[];
  q4_soll: number[];
  tcp_velocity_soll: number[];
  joint_state_soll: number[];
  cpu_temperature: number[];
  segment_id: string;
}

export interface TrajectoryData {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  timestampIst: number[];
  xIst: number[];
  yIst: number[];
  zIst: number[];
  q1Ist: number[];
  q2Ist: number[];
  q3Ist: number[];
  q4Ist: number[];
  tcpVelocityIst: number[];
  tcpAcceleration: number[];
  jointStateIst: number[];
  timestampSoll: number[];
  xSoll: number[];
  ySoll: number[];
  zSoll: number[];
  q1Soll: number[];
  q2Soll: number[];
  q3Soll: number[];
  q4Soll: number[];
  tcpVelocitySoll: number[];
  jointStateSoll: number[];
  segmentId: string;
}

export interface TrajectoryHeaderRaw {
  _id: ObjectId | string;
  data_id: string;
  robot_name: string;
  robot_model: string;
  trajectory_type: string;
  carthesian: boolean;
  path_solver: string;
  recording_date: string;
  real_robot: boolean;
  number_of_points_ist: number;
  number_of_points_soll: number;
  sample_frequency_ist: number;
  sample_frequency_soll: number;
  source_data_ist: string;
  source_data_soll: string;
  start_time: string;
  end_time: string;
}

export interface TrajectoryHeader {
  _id: ObjectId | string;
  dataId: string;
  robotName: string;
  robotModel: string;
  trajectoryType: string;
  carthesian: boolean;
  pathSolver: string;
  recordingDate: string;
  realRobot: boolean;
  numberPointsIst: number;
  numberPointsSoll: number;
  SampleFrequencyIst: number;
  SampleFrequencySoll: number;
  SourceDataIst: string;
  SourceDataSoll: string;
  startTime: string;
  endTime: string;
}

export interface SegmentHeaderRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  segment_id: string;
  start_time: string;
  end_time: string;
  number_of_points_ist: number;
  number_of_points_soll: number;
  sample_frequency_ist: number;
  sample_frequency_soll: number;
}

export interface SegmentHeader {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  segmentId: string;
  startTime: string;
  endTime: string;
  numberPointsIst: number;
  numberPointsSoll: number;
  SampleFrequencyIst: number;
  SampleFrequencySoll: number;
}

export interface TrajectoryEuclideanMetricsRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  euclidean_distances: number[];
  euclidean_max_distance: number;
  euclidean_average_distance: number;
  euclidean_standard_deviation: number;
  euclidean_intersections: Array<number>;
  metric_type: string;
}

export interface TrajectoryEuclideanMetrics {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  euclideanDistances: number[];
  euclideanMaxDistance: number;
  euclideanAverageDistance: number;
  euclideanStandardDeviation: number;
  euclideanIntersections: Array<number>;
  metricType: string;
}

export interface TrajectoryDTWJohnenMetricsRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  dtw_max_distance: number;
  dtw_average_distance: number;
  dtw_distances: Array<number>;
  dtw_x: Array<number>;
  dtw_y: Array<number>;
  dtw_accdist: number[];
  dtw_path: Array<number>;
  metric_type: string;
}

export interface TrajectoryDTWJohnenMetrics {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  dtwJohnenMaxDistance: number;
  dtwJohnenAverageDistance: number;
  dtwJohnenDistances: Array<number>;
  dtwJohnenX: Array<number>;
  dtwJohnenY: Array<number>;
  dtwAccDist: number[];
  dtwPath: Array<number>;
  metricType: string;
}

export interface TrajectoryDTWMetricsRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  dtw_max_distance: number;
  dtw_average_distance: number;
  dtw_distances: number[];
  dtw_X: number[][];
  dtw_Y: number[][];
  dtw_accdist: number[];
  dtw_path: number[];
  metric_type: string;
}

export interface TrajectoryDTWMetrics {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  dtwMaxDistance: number;
  dtwAverageDistance: number;
  dtwDistances: number[];
  dtwX: number[][];
  dtwY: number[][];
  dtwAccDist: number[];
  dtwPath: number[];
  metricType: string;
}

export interface TrajectoryDFDMetricsRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  frechet_max_distance: number;
  frechet_average_distance: number;
  frechet_distances: number[];
  frechet_accdist: number[];
  frechet_path: number[];
  metric_type: string;
}

export interface TrajectoryDFDMetrics {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  dfdMaxDistance: number;
  dfdAverageDistance: number;
  dfdDistances: number[];
  dfdAccDist: number[];
  dfdPath: number[];
  metricType: string;
}

export interface TrajectoryLCSSMetricsRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  lcss_max_distance: number;
  lcss_average_distance: number;
  lcss_distances: number[];
  lcss_X: number[];
  lcss_Y: number[];
  lcss_accdist: number[];
  lcss_path: number[];
  lcss_score: number;
  lcss_threshold: number;
  metric_type: string;
}

export interface TrajectoryLCSSMetrics {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  lcssMaxDistance: number;
  lcssAverageDistance: number;
  lcssDistances: number[];
  lcssX: number[];
  lcssY: number[];
  lcssAccDist: number[];
  lcssPath: number[];
  lcssScore: number;
  lcssThreshold: number;
  metricType: string;
}

/* NEW VERSION */

export interface BahnInfo {
  _id: number;
  bahnID: string;
  robotModel: string;
  bahnplanung: string;
  recordingDate: string;
  startTime: string;
  endTime: string;
  sourceDataIst: string;
  sourceDataSoll: string;
  recordFilename: string;
  numberPoints: number;
  frequencyPoseIst: number;
  frequencyPositionSoll: number;
  frequencyOrientationSoll: number;
  frequencyTwistIst: number;
  frequencyTwistSoll: number;
  frequencyAccelIst: number;
  frequencyJointStates: number;
  calibrationRun: boolean;
}

export interface BahnInfoRaw {
  id: number;
  bahn_id: string;
  robot_model: string;
  bahnplanung: string;
  recording_date: string;
  start_time: string;
  end_time: string;
  source_data_ist: string;
  source_data_soll: string;
  record_filename: string;
  number_of_points: number;
  frequency_pose_ist: number;
  frequency_position_soll: number;
  frequency_orientation_soll: number;
  frequency_twist_ist: number;
  frequency_twist_soll: number;
  frequency_accel_ist: number;
  frequency_joint_states: number;
  calibration_run: boolean;
}

export interface BahnPoseIst {
  _id: number;
  bahnID: string;
  segmentID: string;
  timestamp: string;
  xIst: string;
  yIst: string;
  zIst: string;
  qxIst: number;
  qyIst: number;
  qzIst: number;
  qwIst: number;
  sourceDataIst: string;
}

export interface BahnPoseIstRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  x_ist: string;
  y_ist: string;
  z_ist: string;
  qx_ist: number;
  qy_ist: number;
  qz_ist: number;
  qw_ist: number;
  source_data_ist: string;
}

export interface BahnTwistIst {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpSpeedX: number;
  tcpSpeedY: number;
  tcpSpeedZ: number;
  tcpSpeedIst: number;
  tcpAngularX: number;
  tcpAngularY: number;
  tcpAngularZ: number;
  tcpAngularIst: number;
  sourceDataIst: string;
}

export interface BahnTwistIstRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_speed_x: number;
  tcp_speed_y: number;
  tcp_speed_z: number;
  tcp_speed_ist: number;
  tcp_angular_x: number;
  tcp_angular_y: number;
  tcp_angular_z: number;
  tcp_angular_ist: number;
  source_data_ist: string;
}

export interface BahnAccelIst {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpAccelX: number;
  tcpAccelY: number;
  tcpAccelZ: number;
  tcpAccelIst: number;
  tcpAngularAccelX: number;
  tcpAngularAccelY: number;
  tcpAngularAccelZ: number;
  tcpAngularAccelIst: number;
  sourceDataIst: string;
}

export interface BahnAccelIstRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_accel_x: number;
  tcp_accel_y: number;
  tcp_accel_z: number;
  tcp_accel_ist: number;
  tcp_angular_accel_x: number;
  tcp_angular_accel_y: number;
  tcp_angular_accel_z: number;
  tcp_angular_accel_ist: number;
  source_data_ist: string;
}

export interface BahnPositionSoll {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  xSoll: number;
  ySoll: number;
  zSoll: number;
  sourceDataSoll: string;
}

export interface BahnPositionSollRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  x_soll: number;
  y_soll: number;
  z_soll: number;
  source_data_soll: string;
}

// Interfaces
export interface BahnOrientationSoll {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  qxSoll: number;
  qySoll: number;
  qzSoll: number;
  qwSoll: number;
  sourceDataSoll: string;
}

export interface BahnOrientationSollRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  qx_soll: number;
  qy_soll: number;
  qz_soll: number;
  qw_soll: number;
  source_data_soll: string;
}