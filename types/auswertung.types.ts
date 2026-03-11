import type { BahnInfo } from '@/types/bewegungsdaten.types';

export interface DFDInfoRaw {
  traj_id: string;
  seg_id: string;
  dfd_min_distance: number;
  dfd_max_distance: number;
  dfd_average_distance: number;
  dfd_standard_deviation: number;
  evaluation: string;
}

export interface DFDInfo {
  bahnID: string;
  segmentID: string;
  DFDMinDistance: number;
  DFDMaxDistance: number;
  DFDAvgDistance: number;
  DFDStdDeviation: number;
  evaluation: string;
}

export interface DFDPositionRaw {
  traj_id: string;
  seg_id: string;
  dfd_distances: number;
  dfd_cmd_x: number;
  dfd_cmd_y: number;
  dfd_cmd_z: number;
  dfd_act_x: number;
  dfd_act_y: number;
  dfd_act_z: number;
  points_order: number;
}

export interface DFDPosition {
  bahnID: string;
  segmentID: string;
  DFDDistances: number;
  DFDSollX: number;
  DFDSollY: number;
  DFDSollZ: number;
  DFDIstX: number;
  DFDIstY: number;
  DFDIstZ: number;
  pointsOrder: number;
}

export interface SIDTWInfoRaw {
  traj_id: string;
  seg_id: string;
  sidtw_min_distance: number;
  sidtw_max_distance: number;
  sidtw_average_distance: number;
  sidtw_standard_deviation: number;
}

export interface SIDTWInfo {
  bahnID: string;
  segmentID: string;
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
  bahnID: string;
  segmentID: string;
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
  bahnID: string;
  segmentID: string;
  QDTWMinDistance: number;
  QDTWMaxDistance: number;
  QDTWAvgDistance: number;
  QDTWStdDeviation: number;
}

export interface QADInfoRaw {
  traj_id: string;
  seg_id: string;
  gd_min_distance: number;
  gd_max_distance: number;
  gd_average_distance: number;
  gd_standard_deviation: number;
}

export interface QADInfo {
  bahnID: string;
  segmentID: string;
  QADMinDistance: number;
  QADMaxDistance: number;
  QADAvgDistance: number;
  QADStdDeviation: number;
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
  bahnID: string;
  segmentID: string;
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
  bahnID: string;
  segmentID: string;
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
  bahnID: string;
  segmentID: string;
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

export interface QADOrientationRaw {
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

export interface QADOrientation {
  bahnID: string;
  segmentID: string;
  QADDistances: number;
  QADSollX: number;
  QADSollY: number;
  QADSollZ: number;
  QADSollW: number;
  QADIstX: number;
  QADIstY: number;
  QADIstZ: number;
  QADIstW: number;
  pointsOrder: number;
}

export interface EAInfoRaw {
  traj_id: string;
  seg_id: string;
  euclidean_min_distance: number;
  euclidean_max_distance: number;
  euclidean_average_distance: number;
  euclidean_standard_deviation: number;
  evaluation: string;
}

export interface EAInfo {
  bahnID: string;
  segmentID: string;
  EAMinDistance: number;
  EAMaxDistance: number;
  EAAvgDistance: number;
  EAStdDeviation: number;
  evaluation: string;
}

export interface EAPositionRaw {
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

export interface EAPosition {
  bahnID: string;
  segmentID: string;
  EADistances: number;
  EASollX: number;
  EASollY: number;
  EASollZ: number;
  EAIstX: number;
  EAIstY: number;
  EAIstZ: number;
  pointsOrder: number;
}

export interface AuswertungBahnIDs {
  bahn_info: BahnInfo[];
}

export interface AuswertungInfo {
  traj_info: BahnInfo[];
  auswertung_info: {
    info_sidtw: SIDTWInfo[];
    info_euclidean: EAInfo[];
  };
}
