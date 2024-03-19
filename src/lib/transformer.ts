import type {
  TrajectoryData,
  TrajectoryDataRaw,
  TrajectoryHeader,
  TrajectoryHeaderRaw,
} from '@/types/main';

export const transformTrajectoryResult = (
  trajectoryRaw: TrajectoryDataRaw,
): TrajectoryData => ({
  ...trajectoryRaw,
  _id: trajectoryRaw._id,
  trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
  timestampIst: trajectoryRaw.timestamp_ist,
  xIst: trajectoryRaw.x_ist,
  yIst: trajectoryRaw.y_ist,
  zIst: trajectoryRaw.z_ist,
  q1Ist: trajectoryRaw.q1_ist,
  q2Ist: trajectoryRaw.q2_ist,
  q3Ist: trajectoryRaw.q3_ist,
  q4Ist: trajectoryRaw.q4_ist,
  timestampSoll: trajectoryRaw.timestamp_soll,
  xSoll: trajectoryRaw.x_soll,
  ySoll: trajectoryRaw.y_soll,
  zSoll: trajectoryRaw.z_soll,
  q1Soll: trajectoryRaw.q1_soll,
  q2Soll: trajectoryRaw.q2_soll,
  q3Soll: trajectoryRaw.q3_soll,
  q4Soll: trajectoryRaw.q4_soll,
  jointStatesIst: trajectoryRaw.joint_states_ist,
  jointStatesSoll: trajectoryRaw.joint_states_soll,
});

export const transformTrajectoriesDataResult = (
  trajectoriesDataRaw: TrajectoryDataRaw[],
): TrajectoryData[] => {
  return trajectoriesDataRaw.map(
    (trajectoryRaw): TrajectoryData => ({
      ...trajectoryRaw,
      _id: trajectoryRaw._id,
      trajectoryHeaderId: trajectoryRaw.trajectory_header_id,
      timestampIst: trajectoryRaw.timestamp_ist,
      xIst: trajectoryRaw.x_ist,
      yIst: trajectoryRaw.y_ist,
      zIst: trajectoryRaw.z_ist,
      q1Ist: trajectoryRaw.q1_ist,
      q2Ist: trajectoryRaw.q2_ist,
      q3Ist: trajectoryRaw.q3_ist,
      q4Ist: trajectoryRaw.q4_ist,
      timestampSoll: trajectoryRaw.timestamp_soll,
      xSoll: trajectoryRaw.x_soll,
      ySoll: trajectoryRaw.y_soll,
      zSoll: trajectoryRaw.z_soll,
      q1Soll: trajectoryRaw.q1_soll,
      q2Soll: trajectoryRaw.q2_soll,
      q3Soll: trajectoryRaw.q3_soll,
      q4Soll: trajectoryRaw.q4_soll,
      jointStatesIst: trajectoryRaw.joint_states_ist,
      jointStatesSoll: trajectoryRaw.joint_states_soll,
    }),
  );
};

export const transformTrajectoriesHeadersResult = (
  trajectoriesRaw: TrajectoryHeaderRaw[],
): TrajectoryHeader[] => {
  return trajectoriesRaw.map(
    (trajectory): TrajectoryHeader => ({
      ...trajectory,
      _id: trajectory._id,
      dataId: trajectory.data_id,
      robotName: trajectory.robot_name,
      trajectoryType: trajectory.trajectory_type,
      carthesian: trajectory.carthesian,
      pathSolver: trajectory.path_solver,
      recordingDate: trajectory.recording_date,
      realRobot: trajectory.real_robot,
      numberPointsIst: trajectory.number_of_points_ist,
      numberPointsSoll: trajectory.number_of_points_soll,
      SampleFrequencyIst: trajectory.sample_frequency_ist,
      SampleFrequencySoll: trajectory.sample_frequency_soll,
    }),
  );
};
