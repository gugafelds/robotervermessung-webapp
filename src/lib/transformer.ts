import type { Trajectory, TrajectoryRaw } from '@/types/main';

export const transformTrajectoriesResult = (
  trajectoriesRaw: TrajectoryRaw[],
): Trajectory[] => {
  return trajectoriesRaw.map(
    (trajectory): Trajectory => ({
      ...trajectory,
      _id: trajectory._id,
      robotName: trajectory.robot_name,
      trajectoryType: trajectory.trajectory_type,
      pathSolver: trajectory.path_solver,
      recordingDate: trajectory.recording_date,
      data: {
        xIst: trajectory.data?.x_ist,
        yIst: trajectory.data?.y_ist,
        zIst: trajectory.data?.z_ist,
        xSoll: trajectory.data?.x_soll,
        ySoll: trajectory.data?.y_soll,
        zSoll: trajectory.data?.z_soll,
        xVicon: trajectory.data?.x_vicon,
        yVicon: trajectory.data?.y_vicon,
        zVicon: trajectory.data?.z_vicon,
      },
    }),
  );
};

export const transformTrajectoryResult = (
  trajectoriesRaw: TrajectoryRaw,
): Trajectory => ({
  ...trajectoriesRaw,
  _id: trajectoriesRaw._id,
  robotName: trajectoriesRaw.robot_name,
  trajectoryType: trajectoriesRaw.trajectory_type,
  pathSolver: trajectoriesRaw.path_solver,
  recordingDate: trajectoriesRaw.recording_date,
  data: {
    xIst: trajectoriesRaw.data.x_ist,
    yIst: trajectoriesRaw.data.y_ist,
    zIst: trajectoriesRaw.data.z_ist,
    xSoll: trajectoriesRaw.data.x_soll,
    ySoll: trajectoriesRaw.data.y_soll,
    zSoll: trajectoriesRaw.data.z_soll,
    xVicon: trajectoriesRaw.data.x_vicon,
    yVicon: trajectoriesRaw.data.y_vicon,
    zVicon: trajectoriesRaw.data.z_vicon,
  },
});
