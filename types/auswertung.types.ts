import type { BahnInfo } from '@/types/bewegungsdaten.types';

export interface DFDInfoRaw {
  bahn_id: string;
  segment_id: string;
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
  bahn_id: string;
  segment_id: string;
  dfd_distances: number;
  dfd_soll_x: number;
  dfd_soll_y: number;
  dfd_soll_z: number;
  dfd_ist_x: number;
  dfd_ist_y: number;
  dfd_ist_z: number;
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
  bahn_id: string;
  segment_id: string;
  sidtw_min_distance: number;
  sidtw_max_distance: number;
  sidtw_average_distance: number;
  sidtw_standard_deviation: number;
  evaluation: string;
}

export interface SIDTWInfo {
  bahnID: string;
  segmentID: string;
  SIDTWMinDistance: number;
  SIDTWMaxDistance: number;
  SIDTWAvgDistance: number;
  SIDTWStdDeviation: number;
  evaluation: string;
}

export interface DTWInfoRaw {
  bahn_id: string;
  segment_id: string;
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

export interface SIDTWPositionRaw {
  bahn_id: string;
  segment_id: string;
  sidtw_distances: number;
  sidtw_soll_x: number;
  sidtw_soll_y: number;
  sidtw_soll_z: number;
  sidtw_ist_x: number;
  sidtw_ist_y: number;
  sidtw_ist_z: number;
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
  bahn_id: string;
  segment_id: string;
  dtw_distances: number;
  dtw_soll_x: number;
  dtw_soll_y: number;
  dtw_soll_z: number;
  dtw_ist_x: number;
  dtw_ist_y: number;
  dtw_ist_z: number;
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

export interface EAInfoRaw {
  bahn_id: string;
  segment_id: string;
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
  bahn_id: string;
  segment_id: string;
  euclidean_distances: number;
  ea_soll_x: number;
  ea_soll_y: number;
  ea_soll_z: number;
  ea_ist_x: number;
  ea_ist_y: number;
  ea_ist_z: number;
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

export interface AuswertungInfo {
  bahn_info: BahnInfo[];
  auswertung_info: {
    info_dfd: DFDInfo[];
    info_sidtw: SIDTWInfo[];
    info_dtw: DTWInfo[];
    info_euclidean: EAInfo[];
  };
}
