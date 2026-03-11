import type {
  BahnAccelIst,
  BahnAccelIstRaw,
  BahnAccelSoll,
  BahnAccelSollRaw,
  BahnEvents,
  BahnEventsRaw,
  BahnIMU,
  BahnIMURaw,
  BahnInfo,
  BahnInfoRaw,
  BahnJointStates,
  BahnJointStatesRaw,
  BahnOrientationSoll,
  BahnOrientationSollRaw,
  BahnPoseIst,
  BahnPoseIstRaw,
  BahnPoseTrans,
  BahnPoseTransRaw,
  BahnPositionSoll,
  BahnPositionSollRaw,
  BahnTwistIst,
  BahnTwistIstRaw,
  BahnTwistSoll,
  BahnTwistSollRaw,
} from "@/types/bewegungsdaten.types";
import type {
  BahnInfoResponse,
  BahnInfoResponseRaw,
  PaginationResult,
  PaginationResultRaw,
} from "@/types/pagination.types";

export const transformBahnInfoResult = (
  bahnenRaw: BahnInfoRaw[],
): BahnInfo[] => {
  return bahnenRaw.map(
    (bahn): BahnInfo => ({
      _id: bahn.id,
      bahnID: bahn.traj_id,
      robotModel: bahn.robot_model,
      bahnplanung: bahn.path_planning,
      recordingDate: bahn.recording_date,
      startTime: bahn.start_time,
      endTime: bahn.end_time,
      sourceDataIst: bahn.source_data_act,
      sourceDataSoll: bahn.source_data_cmd,
      recordFilename: bahn.record_filename,
      numberPointsEvents: bahn.number_setpoints,
      frequencyPoseIst: bahn.freq_pose_act,
      frequencyPositionSoll: bahn.freq_position_cmd,
      frequencyOrientationSoll: bahn.freq_orientation_cmd,
      frequencyTwistIst: bahn.freq_vel_act,
      frequencyTwistSoll: bahn.freq_vel_cmd,
      frequencyAccelIst: bahn.freq_accel_act,
      frequencyJointStates: bahn.freq_joint_states,
      calibrationRun: bahn.calibration_run,
      numberPointsPoseIst: bahn.number_pose_act,
      numberPointsTwistIst: bahn.number_vel_act,
      numberPointsAccelIst: bahn.number_accel_act,
      numberPointsPosSoll: bahn.number_position_cmd,
      numberPointsOrientSoll: bahn.number_orientation_cmd,
      numberPointsTwistSoll: bahn.number_vel_cmd,
      numberPointsJointStates: bahn.number_joint_states,
      weight: bahn.weight,
      handlingHeight: bahn.handling_height,
      velocityPicking: bahn.velocity_picking,
      velocityHandling: bahn.velocity_handling,
      frequencyIMU: bahn.freq_imu,
      pickAndPlaceRun: bahn.pick_and_place,
      numberPointsIMU: bahn.number_imu,
      numberPointsAccelSoll: bahn.number_accel_cmd,
      frequencyAccelSoll: bahn.freq_accel_cmd,
      settedVelocity: bahn.setted_velocity,
      stopPoint: bahn.stop_point,
      waitTime: bahn.wait_time,
    }),
  );
};

export const transformBahnInfobyIDResult = (
  bahnRaw: BahnInfoRaw,
): BahnInfo => ({
  _id: bahnRaw.id,
  bahnID: bahnRaw.traj_id,
  robotModel: bahnRaw.robot_model,
  bahnplanung: bahnRaw.path_planning,
  recordingDate: bahnRaw.recording_date,
  startTime: bahnRaw.start_time,
  endTime: bahnRaw.end_time,
  sourceDataIst: bahnRaw.source_data_act,
  sourceDataSoll: bahnRaw.source_data_cmd,
  recordFilename: bahnRaw.record_filename,
  numberPointsEvents: bahnRaw.number_setpoints,
  frequencyPoseIst: bahnRaw.freq_pose_act,
  frequencyPositionSoll: bahnRaw.freq_position_cmd,
  frequencyOrientationSoll: bahnRaw.freq_orientation_cmd,
  frequencyTwistIst: bahnRaw.freq_vel_act,
  frequencyTwistSoll: bahnRaw.freq_vel_cmd,
  frequencyAccelIst: bahnRaw.freq_accel_act,
  frequencyJointStates: bahnRaw.freq_joint_states,
  calibrationRun: bahnRaw.calibration_run,
  numberPointsPoseIst: bahnRaw.number_pose_act,
  numberPointsTwistIst: bahnRaw.number_vel_act,
  numberPointsAccelIst: bahnRaw.number_accel_act,
  numberPointsPosSoll: bahnRaw.number_position_cmd,
  numberPointsOrientSoll: bahnRaw.number_orientation_cmd,
  numberPointsTwistSoll: bahnRaw.number_vel_cmd,
  numberPointsJointStates: bahnRaw.number_joint_states,
  weight: bahnRaw.weight,
  handlingHeight: bahnRaw.handling_height,
  velocityPicking: bahnRaw.velocity_picking,
  velocityHandling: bahnRaw.velocity_handling,
  frequencyIMU: bahnRaw.freq_imu,
  pickAndPlaceRun: bahnRaw.pick_and_place,
  numberPointsIMU: bahnRaw.number_imu,
  numberPointsAccelSoll: bahnRaw.number_accel_cmd,
  frequencyAccelSoll: bahnRaw.freq_accel_cmd,
  settedVelocity: bahnRaw.setted_velocity,
  stopPoint: bahnRaw.stop_point,
  waitTime: bahnRaw.wait_time,
});

export const transformBahnPoseIstResult = (
  bahnenPoseIstRaw: BahnPoseIstRaw[],
): BahnPoseIst[] => {
  return bahnenPoseIstRaw.map(
    (bahn): BahnPoseIst => ({
      _id: bahn.id,
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      timestamp: bahn.timestamp,
      xIst: bahn.x_raw_act,
      yIst: bahn.y_raw_act,
      zIst: bahn.z_raw_act,
      qxIst: bahn.qx_raw_act,
      qyIst: bahn.qy_raw_act,
      qzIst: bahn.qz_raw_act,
      qwIst: bahn.qw_raw_act,
      sourceDataIst: bahn.source_data_raw_act,
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
export const transformBahnInfoResponse = (
  response: BahnInfoResponseRaw,
): BahnInfoResponse => {
  return {
    bahnInfo: transformBahnInfoResult(response.bahn_info),
    pagination: transformPaginationResult(response.pagination),
  };
};

export const transformBahnPoseTransResult = (
  bahnenPoseTransRaw: BahnPoseTransRaw[],
): BahnPoseTrans[] => {
  return bahnenPoseTransRaw.map(
    (bahn): BahnPoseTrans => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      timestamp: bahn.timestamp,
      xTrans: bahn.x_act,
      yTrans: bahn.y_act,
      zTrans: bahn.z_act,
      qxTrans: bahn.qx_act,
      qyTrans: bahn.qy_act,
      qzTrans: bahn.qz_act,
      qwTrans: bahn.qw_act,
      calibrationID: bahn.calibration_id,
    }),
  );
};

export const transformBahnTwistIstResult = (
  bahnenTwistIstRaw: BahnTwistIstRaw[],
): BahnTwistIst[] => {
  return bahnenTwistIstRaw.map(
    (bahn): BahnTwistIst => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpSpeedIst: bahn.tcp_vel_act,
    }),
  );
};

export const transformBahnAccelIstResult = (
  bahnenAccelIstRaw: BahnAccelIstRaw[],
): BahnAccelIst[] => {
  return bahnenAccelIstRaw.map(
    (bahn): BahnAccelIst => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpAccelIst: bahn.tcp_accel_act,
    }),
  );
};

export const transformBahnAccelSollResult = (
  bahnenAccelSollRaw: BahnAccelSollRaw[],
): BahnAccelSoll[] => {
  return bahnenAccelSollRaw.map(
    (bahn): BahnAccelSoll => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpAccelSoll: bahn.tcp_accel_cmd,
    }),
  );
};

export const transformBahnPositionSollResult = (
  bahnenPositionSollRaw: BahnPositionSollRaw[],
): BahnPositionSoll[] => {
  return bahnenPositionSollRaw.map(
    (bahn): BahnPositionSoll => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      xSoll: bahn.x_cmd,
      ySoll: bahn.y_cmd,
      zSoll: bahn.z_cmd,
      sourceDataSoll: bahn.source_data_cmd,
    }),
  );
};

export const transformBahnOrientationSollResult = (
  bahnenOrientationSollRaw: BahnOrientationSollRaw[],
): BahnOrientationSoll[] => {
  return bahnenOrientationSollRaw.map(
    (bahn): BahnOrientationSoll => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      qxSoll: bahn.qx_cmd,
      qySoll: bahn.qy_cmd,
      qzSoll: bahn.qz_cmd,
      qwSoll: bahn.qw_cmd,
      sourceDataSoll: bahn.source_data_cmd,
    }),
  );
};

export const transformBahnTwistSollResult = (
  bahnenTwistSollRaw: BahnTwistSollRaw[],
): BahnTwistSoll[] => {
  return bahnenTwistSollRaw.map(
    (bahn): BahnTwistSoll => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpSpeedSoll: bahn.tcp_vel_cmd,
      sourceDataSoll: bahn.source_data_cmd,
    }),
  );
};

export const transformBahnIMUResult = (
  bahnenIMURaw: BahnIMURaw[],
): BahnIMU[] => {
  return bahnenIMURaw.map(
    (bahn): BahnIMU => ({
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      tcpAccelPi: bahn.tcp_accel_pi,
      tcpAngularVelPi: bahn.tcp_angular_vel_pi,
      sourceDataIst: bahn.source_data_act,
    }),
  );
};

export const transformBahnJointStatesResult = (
  bahnJointStatesRaw: BahnJointStatesRaw[],
): BahnJointStates[] => {
  return bahnJointStatesRaw.map(
    (bahn): BahnJointStates => ({
      id: bahn.id,
      bahnId: bahn.traj_id,
      segmentId: bahn.seg_id,
      timestamp: bahn.timestamp,
      joint1: bahn.joint_1,
      joint2: bahn.joint_2,
      joint3: bahn.joint_3,
      joint4: bahn.joint_4,
      joint5: bahn.joint_5,
      joint6: bahn.joint_6,
      sourceDataSoll: bahn.source_data_cmd,
    }),
  );
};

export const transformBahnEventsResult = (
  bahnEventsRaw: BahnEventsRaw[],
): BahnEvents[] => {
  return bahnEventsRaw.map(
    (event): BahnEvents => ({
      id: event.id,
      bahnId: event.traj_id,
      segmentId: event.seg_id,
      timestamp: event.timestamp,
      xReached: event.x_reached,
      yReached: event.y_reached,
      zReached: event.z_reached,
      qxReached: event.qx_reached,
      qyReached: event.qy_reached,
      qzReached: event.qz_reached,
      qwReached: event.qw_reached,
      sourceDataSoll: event.source_data_cmd,
    }),
  );
};
