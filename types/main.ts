import type { ObjectId } from 'mongodb';

export interface AxisDataRaw {
  _id: ObjectId | string;
  trajectory_header_id: string;
  timestamp_ist: number[];
  x_ist: number[];
  y_ist: number[];
  z_ist: number[];
  q1_ist: number[];
  q2_ist: number[];
  q3_ist: number[];
  q4_ist: number[];
  timestamp_soll: number[];
  x_soll: number[];
  y_soll: number[];
  z_soll: number[];
  q1_soll: number[];
  q2_soll: number[];
  q3_soll: number[];
  q4_soll: number[];
  joint_states_ist: number[][];
  joint_states_soll: number[][];
}

export interface AxisData {
  _id: ObjectId | string;
  trajectoryHeaderId: string;
  timestampIst: number[];
  xIst: number[];
  yIst: number[];
  zIst: number[];
  q1Ist: number[];
  q2Ist: number[];
  q3Ist: number[];
  q4Ist: number[];
  timestampSoll: number[];
  xSoll: number[];
  ySoll: number[];
  zSoll: number[];
  q1Soll: number[];
  q2Soll: number[];
  q3Soll: number[];
  q4Soll: number[];
  jointStatesIst: number[][];
  jointStatesSoll: number[][];
}

export interface TrajectoryRaw {
  _id: ObjectId | string;
  data_id: string;
  robot_name: string;
  trajectory_type: string;
  carthesian: boolean;
  path_solver: string;
  recording_date: string;
  real_robot: boolean;
  number_of_points_ist: number;
  number_of_points_soll: number;
  sample_frequency_ist: number;
  sample_frequency_soll: number;
}


export interface Trajectory {
  _id: ObjectId | string;
  dataId: string;
  robotName: string;
  trajectoryType: string;
  carthesian: boolean;
  pathSolver: string;
  recordingDate: string;
  realRobot: boolean;
  numberPointsIst: number;
  numberPointsSoll: number;
  SampleFrequencyIst: number;
  SampleFrequencySoll: number;
}
