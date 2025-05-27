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
  numberPointsEvents: number;
  frequencyPoseIst: number;
  frequencyPositionSoll: number;
  frequencyOrientationSoll: number;
  frequencyTwistIst: number;
  frequencyTwistSoll: number;
  frequencyAccelIst: number;
  frequencyAccelSoll: number;
  frequencyJointStates: number;
  calibrationRun: boolean;
  numberPointsPoseIst: number;
  numberPointsTwistIst: number;
  numberPointsAccelIst: number;
  numberPointsAccelSoll: number;
  numberPointsPosSoll: number;
  numberPointsOrientSoll: number;
  numberPointsTwistSoll: number;
  numberPointsJointStates: number;
  weight: number;
  handlingHeight: string;
  velocityPicking: string;
  velocityHandling: string;
  frequencyIMU: number;
  pickAndPlaceRun: boolean;
  numberPointsIMU: number;
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
  np_ereignisse: number;
  frequency_pose_ist: number;
  frequency_position_soll: number;
  frequency_orientation_soll: number;
  frequency_twist_ist: number;
  frequency_twist_soll: number;
  frequency_accel_ist: number;
  frequency_joint_states: number;
  calibration_run: boolean;
  np_pose_ist: number;
  np_twist_ist: number;
  np_accel_ist: number;
  np_accel_soll: number;
  np_pos_soll: number;
  np_orient_soll: number;
  np_twist_soll: number;
  np_jointstates: number;
  weight: number;
  handling_height: string;
  velocity_picking: string;
  velocity_handling: string;
  frequency_imu: number;
  pick_and_place: boolean;
  np_imu: number;
  frequency_accel_soll: number;
}

export interface BahnPoseIst {
  _id: number;
  bahnID: string;
  segmentID: string;
  timestamp: string;
  xIst: number;
  yIst: number;
  zIst: number;
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
  x_ist: number;
  y_ist: number;
  z_ist: number;
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
  tcpSpeedIst: number;
}

export interface BahnTwistIstRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_speed_ist: number;
}

export interface BahnAccelIst {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpAccelIst: number;
}

export interface BahnAccelIstRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_accel_ist: number;
}

export interface BahnAccelSoll {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpAccelSoll: number;
}

export interface BahnAccelSollRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_accel_soll: number;
}

export interface BahnIMU {
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpAccelPi: number;
  tcpAngularVelPi: number;
  sourceDataIst: string;
}

export interface BahnIMURaw {
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_accel_pi: number;
  tcp_angular_vel_pi: number;
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

export interface BahnTwistSoll {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  tcpSpeedSoll: number;
  sourceDataSoll: string;
}

export interface BahnTwistSollRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  tcp_speed_soll: number;
  source_data_soll: string;
}

export interface BahnJointStates {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  joint1: number;
  joint2: number;
  joint3: number;
  joint4: number;
  joint5: number;
  joint6: number;
  sourceDataSoll: string;
}

export interface BahnJointStatesRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  joint_1: number;
  joint_2: number;
  joint_3: number;
  joint_4: number;
  joint_5: number;
  joint_6: number;
  source_data_soll: string;
}

export interface BahnEvents {
  id: number;
  bahnId: string;
  segmentId: string;
  timestamp: string;
  xReached: number;
  yReached: number;
  zReached: number;
  qxReached: number;
  qyReached: number;
  qzReached: number;
  qwReached: number;
  sourceDataSoll: string;
}

export interface BahnEventsRaw {
  id: number;
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  x_reached: number;
  y_reached: number;
  z_reached: number;
  qx_reached: number;
  qy_reached: number;
  qz_reached: number;
  qw_reached: number;
  source_data_soll: string;
}

export interface BahnPoseTrans {
  bahnID: string;
  segmentID: string;
  timestamp: string;
  xTrans: number;
  yTrans: number;
  zTrans: number;
  qxTrans: number;
  qyTrans: number;
  qzTrans: number;
  qwTrans: number;
  calibrationID: string;
}

export interface BahnPoseTransRaw {
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  x_trans: number;
  y_trans: number;
  z_trans: number;
  qx_trans: number;
  qy_trans: number;
  qz_trans: number;
  qw_trans: number;
  calibration_id: string;
}
