import type {
  BahnAccelIst,
  BahnAccelIstRaw,
  BahnEvents,
  BahnEventsRaw,
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
} from '@/types/main';

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
      frequencyPoseIst: bahn.frequency_pose_ist,
      frequencyPositionSoll: bahn.frequency_position_soll,
      frequencyOrientationSoll: bahn.frequency_orientation_soll,
      frequencyTwistIst: bahn.frequency_twist_ist,
      frequencyTwistSoll: bahn.frequency_twist_soll,
      frequencyAccelIst: bahn.frequency_accel_ist,
      frequencyJointStates: bahn.frequency_joint_states,
      calibrationRun: bahn.calibration_run,
      numberPointsEvents: bahn.np_ereignisse,
      numberPointsPoseIst: bahn.np_pose_ist,
      numberPointsTwistIst: bahn.np_twist_ist,
      numberPointsAccelIst: bahn.np_accel_ist,
      numberPointsPosSoll: bahn.np_pos_soll,
      numberPointsOrientSoll: bahn.np_orient_soll,
      numberPointsTwistSoll: bahn.np_twist_soll,
      numberPointsJointStates: bahn.np_jointstates,
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
  frequencyPoseIst: bahnRaw.frequency_pose_ist,
  frequencyPositionSoll: bahnRaw.frequency_position_soll,
  frequencyOrientationSoll: bahnRaw.frequency_orientation_soll,
  frequencyTwistIst: bahnRaw.frequency_twist_ist,
  frequencyTwistSoll: bahnRaw.frequency_twist_soll,
  frequencyAccelIst: bahnRaw.frequency_accel_ist,
  frequencyJointStates: bahnRaw.frequency_joint_states,
  calibrationRun: bahnRaw.calibration_run,
  numberPointsEvents: bahnRaw.np_ereignisse,
  numberPointsPoseIst: bahnRaw.np_pose_ist,
  numberPointsTwistIst: bahnRaw.np_twist_ist,
  numberPointsAccelIst: bahnRaw.np_accel_ist,
  numberPointsPosSoll: bahnRaw.np_pos_soll,
  numberPointsOrientSoll: bahnRaw.np_orient_soll,
  numberPointsTwistSoll: bahnRaw.np_twist_soll,
  numberPointsJointStates: bahnRaw.np_jointstates,
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
      rollTrans: bahn.roll_trans,
      pitchTrans: bahn.pitch_trans,
      yawTrans: bahn.yaw_trans,
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
      tcpSpeedX: bahn.tcp_speed_x,
      tcpSpeedY: bahn.tcp_speed_y,
      tcpSpeedZ: bahn.tcp_speed_z,
      tcpSpeedIst: bahn.tcp_speed_ist,
      tcpAngularX: bahn.tcp_angular_x,
      tcpAngularY: bahn.tcp_angular_y,
      tcpAngularZ: bahn.tcp_angular_z,
      tcpAngularIst: bahn.tcp_angular_ist,
      sourceDataIst: bahn.source_data_ist,
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
      tcpAccelX: bahn.tcp_accel_x,
      tcpAccelY: bahn.tcp_accel_y,
      tcpAccelZ: bahn.tcp_accel_z,
      tcpAccelIst: bahn.tcp_accel_ist,
      tcpAngularAccelX: bahn.tcp_angular_accel_x,
      tcpAngularAccelY: bahn.tcp_angular_accel_y,
      tcpAngularAccelZ: bahn.tcp_angular_accel_z,
      tcpAngularAccelIst: bahn.tcp_angular_accel_ist,
      sourceDataIst: bahn.source_data_ist,
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
