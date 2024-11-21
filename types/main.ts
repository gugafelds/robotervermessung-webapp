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
  frequencyPoseIst: number;
  frequencyPositionSoll: number;
  frequencyOrientationSoll: number;
  frequencyTwistIst: number;
  frequencyTwistSoll: number;
  frequencyAccelIst: number;
  frequencyJointStates: number;
  calibrationRun: boolean;
  numberPointsEvents: number;
  numberPointsPoseIst: number;
  numberPointsTwistIst: number;
  numberPointsAccelIst: number;
  numberPointsPosSoll: number;
  numberPointsOrientSoll: number;
  numberPointsTwistSoll: number;
  numberPointsJointStates: number;
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
  frequency_pose_ist: number;
  frequency_position_soll: number;
  frequency_orientation_soll: number;
  frequency_twist_ist: number;
  frequency_twist_soll: number;
  frequency_accel_ist: number;
  frequency_joint_states: number;
  calibration_run: boolean;
  np_ereignisse: number;
  np_pose_ist: number;
  np_twist_ist: number;
  np_accel_ist: number;
  np_pos_soll: number;
  np_orient_soll: number;
  np_twist_soll: number;
  np_jointstates: number;
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
  rollTrans: number;
  pitchTrans: number;
  yawTrans: number;
  calibrationID: string;
}

export interface BahnPoseTransRaw {
  bahn_id: string;
  segment_id: string;
  timestamp: string;
  x_trans: string;
  y_trans: string;
  z_trans: string;
  roll_trans: number;
  pitch_trans: number;
  yaw_trans: number;
  calibration_id: string;
}
