export interface TrajInfo {
  trajID: string;
  robotModel: string;
  pathPlanning: string;
  recordingDate: string;
  startTime: string;
  endTime: string;
  sourceDataAct: string;
  sourceDataCmd: string;
  recordFilename: string;
  numberSetpoints: number;
  frequencyPoseAct: number;
  frequencyPositionCmd: number;
  frequencyOrientationCmd: number;
  frequencyVelAct: number;
  frequencyVelCmd: number;
  frequencyAccelAct: number;
  frequencyAccelCmd: number;
  frequencyJointStates: number;
  calibrationRun: boolean;
  numberPointsPoseAct: number;
  numberPointsVelAct: number;
  numberPointsAccelAct: number;
  numberPointsAccelCmd: number;
  numberPointsPosCmd: number;
  numberPointsOrientCmd: number;
  numberPointsVelCmd: number;
  numberPointsJointStates: number;
  weight: number;
  transfMatrix: string;
  settedVelocity: number;
  stopPoint: number;
  waitTime: number;
}

export interface TrajInfoRaw {
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
  freq_accel_cmd: number;
  setted_velocity: number;
  transformation_matrix: string;
  stop_point: number;
  wait_time: number;
}

export interface TrajPoseAct {
  bahnID: string;
  segmentID: string;
  timestamp: string;
  xAct: number;
  yAct: number;
  zAct: number;
  qxAct: number;
  qyAct: number;
  qzAct: number;
  qwAct: number;
}

export interface TrajPoseActRaw {
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
}

export interface TrajVelAct {
  trajID: string;
  segID: string;
  timestamp: string;
  tcpSpeedAct: number;
}

export interface TrajVelActRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_vel_act: number;
}

export interface TrajAccelAct {
  trajID: string;
  segID: string;
  timestamp: string;
  tcpAccelAct: number;
}

export interface TrajAccelActRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_accel_act: number;
}

export interface TrajAccelCmd {
  trajID: string;
  segID: string;
  timestamp: string;
  tcpAccelCmd: number;
}

export interface TrajAccelCmdRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_accel_cmd: number;
}

export interface TrajPositionCmd {
  trajID: string;
  segID: string;
  timestamp: string;
  xCmd: number;
  yCmd: number;
  zCmd: number;
}

export interface TrajPositionCmdRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  x_cmd: number;
  y_cmd: number;
  z_cmd: number;
}

export interface TrajOrientationCmd {
  trajID: string;
  segID: string;
  timestamp: string;
  qxCmd: number;
  qyCmd: number;
  qzCmd: number;
  qwCmd: number;
}

export interface TrajOrientationCmdRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  qx_cmd: number;
  qy_cmd: number;
  qz_cmd: number;
  qw_cmd: number;
}

export interface TrajVelCmd {
  trajID: string;
  segID: string;
  timestamp: string;
  tcpSpeedCmd: number;
}

export interface TrajVelCmdRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  tcp_vel_cmd: number;
}

export interface TrajJointStates {
  trajID: string;
  segID: string;
  timestamp: string;
  joint1: number;
  joint2: number;
  joint3: number;
  joint4: number;
  joint5: number;
  joint6: number;
}

export interface TrajJointStatesRaw {
  traj_id: string;
  seg_id: string;
  timestamp: string;
  joint_1: number;
  joint_2: number;
  joint_3: number;
  joint_4: number;
  joint_5: number;
  joint_6: number;
}

export interface TrajSetpoints {
  trajID: string;
  segID: string;
  timestamp: string;
  xReached: number;
  yReached: number;
  zReached: number;
  qxReached: number;
  qyReached: number;
  qzReached: number;
  qwReached: number;
}

export interface TrajSetpointsRaw {
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
}
