import type {
  BahnAccelIst,
  BahnAccelIstRaw,
  BahnInfo,
  BahnInfoRaw,
  BahnPoseIst,
  BahnPoseIstRaw,
  BahnPositionSoll,
  BahnPositionSollRaw,
  BahnTwistIst,
  BahnTwistIstRaw,
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
    numberPoints: bahn.number_of_points,
    frequencyPoseIst: bahn.frequency_pose_ist,
    frequencyPositionSoll: bahn.frequency_position_soll,
    frequencyOrientationSoll: bahn.frequency_orientation_soll,
    frequencyTwistIst: bahn.frequency_twist_ist,
    frequencyTwistSoll: bahn.frequency_twist_soll,
    frequencyAccelIst: bahn.frequency_accel_ist,
    frequencyJointStates: bahn.frequency_joint_states,
    calibrationRun: bahn.calibration_run
    }),
  );
};

export const transformBahnPoseIstResult = (bahnenPoseIstRaw: BahnPoseIstRaw[]): BahnPoseIst[] => {
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
    })
  );
};

export const transformBahnTwistIstResult = (bahnenTwistIstRaw: BahnTwistIstRaw[]): BahnTwistIst[] => {
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
    })
  );
};

export const transformBahnAccelIstResult = (bahnenAccelIstRaw: BahnAccelIstRaw[]): BahnAccelIst[] => {
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
    })
  );
};

export const transformBahnPositionSollResult = (bahnenPositionSollRaw: BahnPositionSollRaw[]): BahnPositionSoll[] => {
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
    })
  );
};
