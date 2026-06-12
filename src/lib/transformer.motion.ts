import type {
  TrajAccelAct,
  TrajAccelActRaw,
  TrajAccelCmd,
  TrajAccelCmdRaw,
  TrajInfo,
  TrajInfoRaw,
  TrajJointStates,
  TrajJointStatesRaw,
  TrajMetadata,
  TrajMetadataRaw,
  TrajOrientationCmd,
  TrajOrientationCmdRaw,
  TrajPoseAct,
  TrajPoseActRaw,
  TrajPositionCmd,
  TrajPositionCmdRaw,
  TrajSetpoints,
  TrajSetpointsRaw,
  TrajVelAct,
  TrajVelActRaw,
  TrajVelCmd,
  TrajVelCmdRaw,
} from '@/types/motion.types';
import type {
  PaginationResult,
  PaginationResultRaw,
  TrajInfoResponse,
  TrajInfoResponseRaw,
} from '@/types/pagination.types';

export const transformTrajInfoResult = (
  bahnenRaw: TrajInfoRaw[],
): TrajInfo[] => {
  return bahnenRaw.map(
    (bahn): TrajInfo => ({
      trajID: bahn.traj_id,
      robotModel: bahn.robot_model,
      pathPlanning: bahn.path_planning,
      recordingDate: bahn.recording_date,
      startTime: bahn.start_time,
      endTime: bahn.end_time,
      sourceDataAct: bahn.source_data_act,
      sourceDataCmd: bahn.source_data_cmd,
      recordFilename: bahn.record_filename,
      numberSetpoints: bahn.number_setpoints,
      frequencyPoseAct: bahn.freq_pose_act,
      frequencyPositionCmd: bahn.freq_position_cmd,
      frequencyOrientationCmd: bahn.freq_orientation_cmd,
      frequencyVelAct: bahn.freq_vel_act,
      frequencyVelCmd: bahn.freq_vel_cmd,
      frequencyAccelAct: bahn.freq_accel_act,
      frequencyJointStates: bahn.freq_joint_states,
      calibrationRun: bahn.calibration_run,
      numberPointsPoseAct: bahn.number_pose_act,
      numberPointsVelAct: bahn.number_vel_act,
      numberPointsAccelAct: bahn.number_accel_act,
      numberPointsPosCmd: bahn.number_position_cmd,
      numberPointsOrientCmd: bahn.number_orientation_cmd,
      numberPointsVelCmd: bahn.number_vel_cmd,
      numberPointsJointStates: bahn.number_joint_states,
      weight: bahn.weight,
      numberPointsAccelCmd: bahn.number_accel_cmd,
      frequencyAccelCmd: bahn.freq_accel_cmd,
      settedVelocity: bahn.setted_velocity,
      transfMatrix: bahn.transformation_matrix,
      stopPoint: bahn.stop_point,
      waitTime: bahn.wait_time,
    }),
  );
};

export const transformTrajInfobyIDResult = (
  bahnRaw: TrajInfoRaw,
): TrajInfo => ({
  trajID: bahnRaw.traj_id,
  robotModel: bahnRaw.robot_model,
  pathPlanning: bahnRaw.path_planning,
  recordingDate: bahnRaw.recording_date,
  startTime: bahnRaw.start_time,
  endTime: bahnRaw.end_time,
  sourceDataAct: bahnRaw.source_data_act,
  sourceDataCmd: bahnRaw.source_data_cmd,
  recordFilename: bahnRaw.record_filename,
  numberSetpoints: bahnRaw.number_setpoints,
  frequencyPoseAct: bahnRaw.freq_pose_act,
  frequencyPositionCmd: bahnRaw.freq_position_cmd,
  frequencyOrientationCmd: bahnRaw.freq_orientation_cmd,
  frequencyVelAct: bahnRaw.freq_vel_act,
  frequencyVelCmd: bahnRaw.freq_vel_cmd,
  frequencyAccelAct: bahnRaw.freq_accel_act,
  frequencyJointStates: bahnRaw.freq_joint_states,
  calibrationRun: bahnRaw.calibration_run,
  numberPointsPoseAct: bahnRaw.number_pose_act,
  numberPointsVelAct: bahnRaw.number_vel_act,
  numberPointsAccelAct: bahnRaw.number_accel_act,
  numberPointsPosCmd: bahnRaw.number_position_cmd,
  numberPointsOrientCmd: bahnRaw.number_orientation_cmd,
  numberPointsVelCmd: bahnRaw.number_vel_cmd,
  numberPointsJointStates: bahnRaw.number_joint_states,
  weight: bahnRaw.weight,
  numberPointsAccelCmd: bahnRaw.number_accel_cmd,
  frequencyAccelCmd: bahnRaw.freq_accel_cmd,
  settedVelocity: bahnRaw.setted_velocity,
  stopPoint: bahnRaw.stop_point,
  waitTime: bahnRaw.wait_time,
  transfMatrix: bahnRaw.transformation_matrix,
});

export const transformTrajPoseActResult = (
  bahnenPoseAct: TrajPoseActRaw[],
): TrajPoseAct[] => {
  return bahnenPoseAct.map(
    (bahn): TrajPoseAct => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      timestamp: bahn.timestamp,
      xAct: bahn.x_act,
      yAct: bahn.y_act,
      zAct: bahn.z_act,
      qxAct: bahn.qx_act,
      qyAct: bahn.qy_act,
      qzAct: bahn.qz_act,
      qwAct: bahn.qw_act,
    }),
  );
};

export const transformPaginationResult = (
  paginationRaw: PaginationResultRaw,
): PaginationResult => {
  return {
    total: paginationRaw.total,
    page: paginationRaw.page,
    pageSize: paginationRaw.page_size,
    totalPages: paginationRaw.total_pages,
    hasNext: paginationRaw.has_next,
    hasPrevious: paginationRaw.has_previous,
  };
};
// Transformiere die gesamte API-Antwort
export const transformTrajInfoResponse = (
  response: TrajInfoResponseRaw,
): TrajInfoResponse => {
  return {
    trajInfo: transformTrajInfoResult(response.traj_info),
    pagination: transformPaginationResult(response.pagination),
  };
};

export const transformTrajVelActResult = (
  bahnenVelActRaw: TrajVelActRaw[],
): TrajVelAct[] => {
  return bahnenVelActRaw.map(
    (bahn): TrajVelAct => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpSpeedAct: bahn.tcp_vel_act,
    }),
  );
};

export const transformTrajAccelActResult = (
  bahnenAccelActRaw: TrajAccelActRaw[],
): TrajAccelAct[] => {
  return bahnenAccelActRaw.map(
    (bahn): TrajAccelAct => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpAccelAct: bahn.tcp_accel_act,
    }),
  );
};

export const transformTrajAccelCmdResult = (
  bahnenAccelCmdRaw: TrajAccelCmdRaw[],
): TrajAccelCmd[] => {
  return bahnenAccelCmdRaw.map(
    (bahn): TrajAccelCmd => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpAccelCmd: bahn.tcp_accel_cmd,
    }),
  );
};

export const transformTrajPositionCmdResult = (
  bahnenPositionCmdRaw: TrajPositionCmdRaw[],
): TrajPositionCmd[] => {
  return bahnenPositionCmdRaw.map(
    (bahn): TrajPositionCmd => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      xCmd: bahn.x_cmd,
      yCmd: bahn.y_cmd,
      zCmd: bahn.z_cmd,
    }),
  );
};

export const transformTrajOrientationCmdResult = (
  bahnenOrientationCmdRaw: TrajOrientationCmdRaw[],
): TrajOrientationCmd[] => {
  return bahnenOrientationCmdRaw.map(
    (bahn): TrajOrientationCmd => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      qxCmd: bahn.qx_cmd,
      qyCmd: bahn.qy_cmd,
      qzCmd: bahn.qz_cmd,
      qwCmd: bahn.qw_cmd,
    }),
  );
};

export const transformTrajVelCmdResult = (
  bahnenVelCmdRaw: TrajVelCmdRaw[],
): TrajVelCmd[] => {
  return bahnenVelCmdRaw.map(
    (bahn): TrajVelCmd => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpSpeedCmd: bahn.tcp_vel_cmd,
    }),
  );
};

export const transformTrajJointStatesResult = (
  bahnJointStatesRaw: TrajJointStatesRaw[],
): TrajJointStates[] => {
  return bahnJointStatesRaw.map(
    (bahn): TrajJointStates => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      timestamp: bahn.timestamp,
      joint1: bahn.joint_1,
      joint2: bahn.joint_2,
      joint3: bahn.joint_3,
      joint4: bahn.joint_4,
      joint5: bahn.joint_5,
      joint6: bahn.joint_6,
    }),
  );
};

export const transformTrajSetpointsResult = (
  trajSetpointsRaw: TrajSetpointsRaw[],
): TrajSetpoints[] => {
  return trajSetpointsRaw.map(
    (event): TrajSetpoints => ({
      trajID: event.traj_id,
      segID: event.seg_id,
      timestamp: event.timestamp,
      xReached: event.x_reached,
      yReached: event.y_reached,
      zReached: event.z_reached,
      qxReached: event.qx_reached,
      qyReached: event.qy_reached,
      qzReached: event.qz_reached,
      qwReached: event.qw_reached,
      xSupport: event.x_support,
      ySupport: event.y_support,
      zSupport: event.z_support,
      qxSupport: event.qx_support,
      qySupport: event.qy_support,
      qzSupport: event.qz_support,
      qwSupport: event.qw_support,
      velocitySet: event.vel_set,
      stopPoint: event.stop_point,
      timestampSupport: event.timestamp_support,
    }),
  );
};

export const transformTrajMetadataResult = (
  trajMetadataRaw: TrajMetadataRaw[],
): TrajMetadata[] => {
  return trajMetadataRaw.map(
    (metadata): TrajMetadata => ({
      segID: metadata.seg_id,
      trajID: metadata.traj_id,
      movType: metadata.movement_type,
      duration: metadata.duration,
      weight: metadata.weight,
      length: metadata.length,
      minVel: metadata.min_vel,
      maxVel: metadata.max_vel,
      meanVel: metadata.mean_vel,
      medianVel: metadata.median_vel,
      stdVel: metadata.std_vel,
      minAccel: metadata.min_accel,
      maxAccel: metadata.max_accel,
      meanAccel: metadata.mean_accel,
      medianAccel: metadata.median_accel,
      stdAccel: metadata.std_accel,
      posX: metadata.position_x,
      posY: metadata.position_y,
      posZ: metadata.position_z,
    }),
  );
};
