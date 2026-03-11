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
  settedVelocity: number;
  stopPoint: number;
  waitTime: number;
}

export interface BahnInfoRaw {
  id: number;
  traj_id: string;
  robot_model: string;
  path_planning: string;
  recording_date: string;
  start_time: string;
  end_time: string;
  source_data_act: string;
  source_data_cmd: string;
  record_filename: string;
  number_setpoints: number;
  freq_pose_act: number;
  freq_position_cmd: number;
  freq_orientation_cmd: number;
  freq_vel_act: number;
  freq_vel_cmd: number;
  freq_accel_act: number;
  freq_joint_states: number;
  calibration_run: boolean;
  number_pose_act: number;
  number_vel_act: number;
  number_accel_act: number;
  number_accel_cmd: number;
  number_position_cmd: number;
  number_orientation_cmd: number;
  number_vel_cmd: number;
  number_joint_states: number;
  weight: number;
  handling_height: string;
  velocity_picking: string;
  velocity_handling: string;
  freq_imu: number;
  pick_and_place: boolean;
  number_imu: number;
  freq_accel_cmd: number;
  setted_velocity: number;
  stop_point: number;
  wait_time: number;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  x_raw_act: number;
  y_raw_act: number;
  z_raw_act: number;
  qx_raw_act: number;
  qy_raw_act: number;
  qz_raw_act: number;
  qw_raw_act: number;
  source_data_raw_act: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_vel_act: number;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_accel_act: number;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_accel_cmd: number;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_accel_pi: number;
  tcp_angular_vel_pi: number;
  source_data_act: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  x_cmd: number;
  y_cmd: number;
  z_cmd: number;
  source_data_cmd: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  qx_cmd: number;
  qy_cmd: number;
  qz_cmd: number;
  qw_cmd: number;
  source_data_cmd: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_vel_cmd: number;
  source_data_cmd: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  joint_1: number;
  joint_2: number;
  joint_3: number;
  joint_4: number;
  joint_5: number;
  joint_6: number;
  source_data_cmd: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  x_reached: number;
  y_reached: number;
  z_reached: number;
  qx_reached: number;
  qy_reached: number;
  qz_reached: number;
  qw_reached: number;
  source_data_cmd: string;
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
  traj_id: string;
  seg_id: string;
  timestamp: string;
  x_act: number;
  y_act: number;
  z_act: number;
  qx_act: number;
  qy_act: number;
  qz_act: number;
  qw_act: number;
  calibration_id: string;
}
