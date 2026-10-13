import type { TrajInfo } from '@/types/motion.types';

export interface SIDTWInfoRaw {
  traj_id: string;
  seg_id: string;
  sidtw_min_distance: number;
  sidtw_max_distance: number;
  sidtw_average_distance: number;
  sidtw_standard_deviation: number;
}

export interface SIDTWInfo {
  trajID: string;
  segID: string;
  SIDTWMinDistance: number;
  SIDTWMaxDistance: number;
  SIDTWAvgDistance: number;
  SIDTWStdDeviation: number;
}

export interface DTWInfoRaw {
  traj_id: string;
  seg_id: string;
  dtw_min_distance: number;
  dtw_max_distance: number;
  dtw_average_distance: number;
  dtw_standard_deviation: number;
  evaluation: string;
}

export interface DTWInfo {
  trajID: string;
  segID: string;
  DTWMinDistance: number;
  DTWMaxDistance: number;
  DTWAvgDistance: number;
  DTWStdDeviation: number;
  evaluation: string;
}

export interface QDTWInfoRaw {
  traj_id: string;
  seg_id: string;
  qdtw_min_distance: number;
  qdtw_max_distance: number;
  qdtw_average_distance: number;
  qdtw_standard_deviation: number;
}

export interface QDTWInfo {
  trajID: string;
  segID: string;
  QDTWMinDistance: number;
  QDTWMaxDistance: number;
  QDTWAvgDistance: number;
  QDTWStdDeviation: number;
}

export interface GDInfoRaw {
  traj_id: string;
  seg_id: string;
  gd_min_distance: number;
  gd_max_distance: number;
  gd_average_distance: number;
  gd_standard_deviation: number;
}

export interface GDInfo {
  trajID: string;
  segID: string;
  GDMinDistance: number;
  GDMaxDistance: number;
  GDAvgDistance: number;
  GDStdDeviation: number;
}

export interface SIDTWPositionRaw {
  traj_id: string;
  seg_id: string;
  sidtw_deviation: number;
  sidtw_cmd_x: number;
  sidtw_cmd_y: number;
  sidtw_cmd_z: number;
  sidtw_act_x: number;
  sidtw_act_y: number;
  sidtw_act_z: number;
  points_order: number;
}

export interface SIDTWPosition {
  trajID: string;
  segID: string;
  SIDTWDistances: number;
  SIDTWCmdX: number;
  SIDTWCmdY: number;
  SIDTWCmdZ: number;
  SIDTWActX: number;
  SIDTWActY: number;
  SIDTWActZ: number;
  pointsOrder: number;
}

export interface DTWPositionRaw {
  traj_id: string;
  seg_id: string;
  dtw_distances: number;
  dtw_cmd_x: number;
  dtw_cmd_y: number;
  dtw_cmd_z: number;
  dtw_act_x: number;
  dtw_act_y: number;
  dtw_act_z: number;
  points_order: number;
}

export interface DTWPosition {
  trajID: string;
  segID: string;
  DTWDistances: number;
  DTWCmdX: number;
  DTWCmdY: number;
  DTWCmdZ: number;
  DTWActX: number;
  DTWActY: number;
  DTWActZ: number;
  pointsOrder: number;
}

export interface QDTWOrientationRaw {
  traj_id: string;
  seg_id: string;
  qdtw_deviation: number;
  qdtw_cmd_x: number;
  qdtw_cmd_y: number;
  qdtw_cmd_z: number;
  qdtw_cmd_w: number;
  qdtw_act_x: number;
  qdtw_act_y: number;
  qdtw_act_z: number;
  qdtw_act_w: number;
  points_order: number;
}

export interface QDTWOrientation {
  trajID: string;
  segID: string;
  QDTWDistances: number;
  QDTWCmdX: number;
  QDTWCmdY: number;
  QDTWCmdZ: number;
  QDTWCmdW: number;
  QDTWActX: number;
  QDTWActY: number;
  QDTWActZ: number;
  QDTWActW: number;
  pointsOrder: number;
}

export interface GDOrientationRaw {
  traj_id: string;
  seg_id: string;
  gd_deviation: number;
  gd_cmd_x: number;
  gd_cmd_y: number;
  gd_cmd_z: number;
  gd_cmd_w: number;
  gd_act_x: number;
  gd_act_y: number;
  gd_act_z: number;
  gd_act_w: number;
  points_order: number;
}

export interface GDOrientation {
  trajID: string;
  segID: string;
  GDDistances: number;
  GDCmdX: number;
  GDCmdY: number;
  GDCmdZ: number;
  GDCmdW: number;
  GDActX: number;
  GDActY: number;
  GDActZ: number;
  GDActW: number;
  pointsOrder: number;
}

export interface EDInfoRaw {
  traj_id: string;
  seg_id: string;
  ed_min_distance: number;
  ed_max_distance: number;
  ed_average_distance: number;
  ed_standard_deviation: number;
}

export interface EDInfo {
  trajID: string;
  segID: string;
  EDMinDistance: number;
  EDMaxDistance: number;
  EDAvgDistance: number;
  EDStdDeviation: number;
}

export interface EDPositionRaw {
  traj_id: string;
  seg_id: string;
  ed_deviation: number;
  ed_cmd_x: number;
  ed_cmd_y: number;
  ed_cmd_z: number;
  ed_act_x: number;
  ed_act_y: number;
  ed_act_z: number;
  points_order: number;
}

export interface EDPosition {
  trajID: string;
  segID: string;
  EDDistances: number;
  EDCmdX: number;
  EDCmdY: number;
  EDCmdZ: number;
  EDActX: number;
  EDActY: number;
  EDActZ: number;
  pointsOrder: number;
}

export interface EvaluationTrajIDs {
  traj_info: TrajInfo[];
}

export interface EvaluationInfo {
  traj_info: TrajInfo[];
  evaluation_info: {
    info_sidtw: SIDTWInfo[];
    info_euclidean: EDInfo[];
  };
}

// Positioning accuracy per segment (evaluation.acc_position): measured - target in mm
export interface AccPositionRaw {
  segment_id: string;
  traj_id: string;
  stop_point: number | null;
  pos_mode: 'rest' | 'nearest' | 'all'; // 'all' = whole trajectory (segment_id = traj_id)
  dx: number | null;
  dy: number | null;
  dz: number | null;
  p: number;
  q_deg: number | null;
  n_rest: number | null;
  t_rest_ms: number | null;
  v_min_mm_s: number | null;
  p1_sidtw: number | null;
}

export interface AccPosition {
  segmentID: string;
  trajID: string;
  stopPoint: number | null;
  posMode: 'rest' | 'nearest' | 'all';
  dx: number | null;
  dy: number | null;
  dz: number | null;
  p: number;
  qDeg: number | null;
  nRest: number | null;
  tRestMs: number | null;
  vMinMmS: number | null;
  p1SIDTW: number | null;
}

// Approach to the target per segment (+-0.2 s around the segment end): time [s], distance [mm], speed [mm/s]
export interface AccApproach {
  segmentID: string;
  t: number[];
  distance: number[];
  along: number[]; // signed along the approach direction: < 0 short of the target, > 0 overshoot [mm]
  across: number[]; // across the approach direction [mm]
  alongDp: number; // the same split at the table's Δp point
  acrossDp: number;
  sidtwT: number | null; // time of the measured point of the segment's last SIDTW pair [s]
  sidtwDistance: number | null; // its distance to the target [mm]
  sidtwDeviation: number | null; // SIDTW deviation of that pair (= 'SIDTW at end') [mm]
  speed: (number | null)[];
}
