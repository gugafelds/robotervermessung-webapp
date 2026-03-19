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
  SIDTWSollX: number;
  SIDTWSollY: number;
  SIDTWSollZ: number;
  SIDTWIstX: number;
  SIDTWIstY: number;
  SIDTWIstZ: number;
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
  DTWSollX: number;
  DTWSollY: number;
  DTWSollZ: number;
  DTWIstX: number;
  DTWIstY: number;
  DTWIstZ: number;
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
  QDTWSollX: number;
  QDTWSollY: number;
  QDTWSollZ: number;
  QDTWSollW: number;
  QDTWIstX: number;
  QDTWIstY: number;
  QDTWIstZ: number;
  QDTWIstW: number;
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
  GDSollX: number;
  GDSollY: number;
  GDSollZ: number;
  GDSollW: number;
  GDIstX: number;
  GDIstY: number;
  GDIstZ: number;
  GDIstW: number;
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
  EDSollX: number;
  EDSollY: number;
  EDSollZ: number;
  EDIstX: number;
  EDIstY: number;
  EDIstZ: number;
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
