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

export interface DFDDeviationRaw {
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
  evaluation: string;
}

export interface DFDDeviation {
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
  evaluation: string;
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

export interface SIDTWDeviationRaw {
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
  evaluation: string;
}

export interface SIDTWDeviation {
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
  evaluation: string;
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

export interface EADeviationRaw {
  bahn_id: string;
  segment_id: string;
  euclidean_distances: number;
  points_order: number;
  evaluation: string;
}

export interface EADeviation {
  bahnID: string;
  segmentID: string;
  EADistances: number;
  pointsOrder: number;
  evaluation: string;
}

export interface AuswertungInfo {
  bahn_info: BahnInfo[];
  auswertung_info: {
    dfd_info: DFDInfo[];
    sidtw_info: SIDTWInfo[];
    euclidean_info: EAInfo[];
  };
}
