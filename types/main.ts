import type { ObjectId } from 'mongodb';

export enum TrajectoryType {
  CIRCLE = 'circle',
  SQUARE = 'square',
}

export interface AxisDataRaw {
  x_ist: number[];
  y_ist: number[];
  z_ist: number[];
  x_soll: number[];
  y_soll: number[];
  z_soll: number[];
  x_vicon: number[];
  y_vicon: number[];
  z_vicon: number[];
}

export interface AxisData {
  xIst: number[];
  yIst: number[];
  zIst: number[];
  xSoll: number[];
  ySoll: number[];
  zSoll: number[];
  xVicon: number[];
  yVicon: number[];
  zVicon: number[];
}

export interface TrajectoryRaw {
  _id: ObjectId | string;
  robot_name: string;
  trajectory_type: TrajectoryType;
  carthesian: true;
  path_solver: string;
  recording_date: string;
  data: AxisDataRaw;
}

export interface Trajectory {
  _id: ObjectId | string;
  robotName: string;
  trajectoryType: TrajectoryType;
  carthesian: true;
  pathSolver: string;
  recordingDate: string;
  data: AxisData;
}
