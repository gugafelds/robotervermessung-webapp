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
} from '@/types/bewegungsdaten.types';
import type {
  BahnInfoResponse,
  BahnInfoResponseRaw,
  PaginationResult,
  PaginationResultRaw,
} from '@/types/pagination.types';

export const transformBahnInfoResult = (
  bahnenRaw: BahnInfoRaw[],
): BahnInfo[] => {
  return bahnenRaw.map(
    (bahn): BahnInfo => ({
      _id: bahn.id,
      bahnID: bahn.bahn_id,
      robotModel: bahn.robot_model,
      bahnplanung: bahn.bahnplanung,
      recordingDate: bahn.recording_date,
      startTime: bahn.start_time,
      endTime: bahn.end_time,
      sourceDataIst: bahn.source_data_ist,
      sourceDataSoll: bahn.source_data_soll,
      recordFilename: bahn.record_filename,
      numberPointsEvents: bahn.np_ereignisse,
      frequencyPoseIst: bahn.frequency_pose_ist,
      frequencyPositionSoll: bahn.frequency_position_soll,
      frequencyOrientationSoll: bahn.frequency_orientation_soll,
      frequencyTwistIst: bahn.frequency_twist_ist,
      frequencyTwistSoll: bahn.frequency_twist_soll,
      frequencyAccelIst: bahn.frequency_accel_ist,
      frequencyJointStates: bahn.frequency_joint_states,
      calibrationRun: bahn.calibration_run,
      numberPointsPoseIst: bahn.np_pose_ist,
      numberPointsTwistIst: bahn.np_twist_ist,
      numberPointsAccelIst: bahn.np_accel_ist,
      numberPointsPosSoll: bahn.np_pos_soll,
      numberPointsOrientSoll: bahn.np_orient_soll,
      numberPointsTwistSoll: bahn.np_twist_soll,
      numberPointsJointStates: bahn.np_jointstates,
      weight: bahn.weight,
      handlingHeight: bahn.handling_height,
      velocityPicking: bahn.velocity_picking,
      velocityHandling: bahn.velocity_handling,
      frequencyIMU: bahn.frequency_imu,
      pickAndPlaceRun: bahn.pick_and_place,
      numberPointsIMU: bahn.np_imu,
      numberPointsAccelSoll: bahn.np_accel_soll,
      frequencyAccelSoll: bahn.frequency_accel_soll,
      stopPoint: bahn.stop_point,
      waitTime: bahn.wait_time,
    }),
  );
};

export const transformBahnInfobyIDResult = (
  bahnRaw: BahnInfoRaw,
): BahnInfo => ({
  _id: bahnRaw.id,
  bahnID: bahnRaw.bahn_id,
  robotModel: bahnRaw.robot_model,
  bahnplanung: bahnRaw.bahnplanung,
  recordingDate: bahnRaw.recording_date,
  startTime: bahnRaw.start_time,
  endTime: bahnRaw.end_time,
  sourceDataIst: bahnRaw.source_data_ist,
  sourceDataSoll: bahnRaw.source_data_soll,
  recordFilename: bahnRaw.record_filename,
  numberPointsEvents: bahnRaw.np_ereignisse,
  frequencyPoseIst: bahnRaw.frequency_pose_ist,
  frequencyPositionSoll: bahnRaw.frequency_position_soll,
  frequencyOrientationSoll: bahnRaw.frequency_orientation_soll,
  frequencyTwistIst: bahnRaw.frequency_twist_ist,
  frequencyTwistSoll: bahnRaw.frequency_twist_soll,
  frequencyAccelIst: bahnRaw.frequency_accel_ist,
  frequencyJointStates: bahnRaw.frequency_joint_states,
  calibrationRun: bahnRaw.calibration_run,
  numberPointsPoseIst: bahnRaw.np_pose_ist,
  numberPointsTwistIst: bahnRaw.np_twist_ist,
  numberPointsAccelIst: bahnRaw.np_accel_ist,
  numberPointsPosSoll: bahnRaw.np_pos_soll,
  numberPointsOrientSoll: bahnRaw.np_orient_soll,
  numberPointsTwistSoll: bahnRaw.np_twist_soll,
  numberPointsJointStates: bahnRaw.np_jointstates,
  weight: bahnRaw.weight,
  handlingHeight: bahnRaw.handling_height,
  velocityPicking: bahnRaw.velocity_picking,
  velocityHandling: bahnRaw.velocity_handling,
  frequencyIMU: bahnRaw.frequency_imu,
  pickAndPlaceRun: bahnRaw.pick_and_place,
  numberPointsIMU: bahnRaw.np_imu,
  numberPointsAccelSoll: bahnRaw.np_accel_soll,
  frequencyAccelSoll: bahnRaw.frequency_accel_soll,
  stopPoint: bahnRaw.stop_point,
  waitTime: bahnRaw.wait_time,
});

export const transformBahnPoseIstResult = (
  bahnenPoseIstRaw: BahnPoseIstRaw[],
): BahnPoseIst[] => {
  return bahnenPoseIstRaw.map(
    (bahn): BahnPoseIst => ({
      _id: bahn.id,
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      timestamp: bahn.timestamp,
      xIst: bahn.x_ist,
      yIst: bahn.y_ist,
      zIst: bahn.z_ist,
      qxIst: bahn.qx_ist,
      qyIst: bahn.qy_ist,
      qzIst: bahn.qz_ist,
      qwIst: bahn.qw_ist,
      sourceDataIst: bahn.source_data_ist,
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
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      timestamp: bahn.timestamp,
      xTrans: bahn.x_trans,
      yTrans: bahn.y_trans,
      zTrans: bahn.z_trans,
      qxTrans: bahn.qx_trans,
      qyTrans: bahn.qy_trans,
      qzTrans: bahn.qz_trans,
      qwTrans: bahn.qw_trans,
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
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      tcpSpeedIst: bahn.tcp_speed_ist,
    }),
  );
};

export const transformBahnAccelIstResult = (
  bahnenAccelIstRaw: BahnAccelIstRaw[],
): BahnAccelIst[] => {
  return bahnenAccelIstRaw.map(
    (bahn): BahnAccelIst => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      tcpAccelIst: bahn.tcp_accel_ist,
    }),
  );
};

export const transformBahnAccelSollResult = (
  bahnenAccelSollRaw: BahnAccelSollRaw[],
): BahnAccelSoll[] => {
  return bahnenAccelSollRaw.map(
    (bahn): BahnAccelSoll => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      tcpAccelSoll: bahn.tcp_accel_soll,
    }),
  );
};

export const transformBahnPositionSollResult = (
  bahnenPositionSollRaw: BahnPositionSollRaw[],
): BahnPositionSoll[] => {
  return bahnenPositionSollRaw.map(
    (bahn): BahnPositionSoll => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      xSoll: bahn.x_soll,
      ySoll: bahn.y_soll,
      zSoll: bahn.z_soll,
      sourceDataSoll: bahn.source_data_soll,
    }),
  );
};

export const transformBahnOrientationSollResult = (
  bahnenOrientationSollRaw: BahnOrientationSollRaw[],
): BahnOrientationSoll[] => {
  return bahnenOrientationSollRaw.map(
    (bahn): BahnOrientationSoll => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      qxSoll: bahn.qx_soll,
      qySoll: bahn.qy_soll,
      qzSoll: bahn.qz_soll,
      qwSoll: bahn.qw_soll,
      sourceDataSoll: bahn.source_data_soll,
    }),
  );
};

export const transformBahnTwistSollResult = (
  bahnenTwistSollRaw: BahnTwistSollRaw[],
): BahnTwistSoll[] => {
  return bahnenTwistSollRaw.map(
    (bahn): BahnTwistSoll => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      tcpSpeedSoll: bahn.tcp_speed_soll,
      sourceDataSoll: bahn.source_data_soll,
    }),
  );
};

export const transformBahnIMUResult = (
  bahnenIMURaw: BahnIMURaw[],
): BahnIMU[] => {
  return bahnenIMURaw.map(
    (bahn): BahnIMU => ({
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      tcpAccelPi: bahn.tcp_accel_pi,
      tcpAngularVelPi: bahn.tcp_angular_vel_pi,
      sourceDataIst: bahn.source_data_ist,
    }),
  );
};

export const transformBahnJointStatesResult = (
  bahnJointStatesRaw: BahnJointStatesRaw[],
): BahnJointStates[] => {
  return bahnJointStatesRaw.map(
    (bahn): BahnJointStates => ({
      id: bahn.id,
      bahnId: bahn.bahn_id,
      segmentId: bahn.segment_id,
      timestamp: bahn.timestamp,
      joint1: bahn.joint_1,
      joint2: bahn.joint_2,
      joint3: bahn.joint_3,
      joint4: bahn.joint_4,
      joint5: bahn.joint_5,
      joint6: bahn.joint_6,
      sourceDataSoll: bahn.source_data_soll,
    }),
  );
};

export const transformBahnEventsResult = (
  bahnEventsRaw: BahnEventsRaw[],
): BahnEvents[] => {
  return bahnEventsRaw.map(
    (event): BahnEvents => ({
      id: event.id,
      bahnId: event.bahn_id,
      segmentId: event.segment_id,
      timestamp: event.timestamp,
      xReached: event.x_reached,
      yReached: event.y_reached,
      zReached: event.z_reached,
      qxReached: event.qx_reached,
      qyReached: event.qy_reached,
      qzReached: event.qz_reached,
      qwReached: event.qw_reached,
      sourceDataSoll: event.source_data_soll,
    }),
  );
};
