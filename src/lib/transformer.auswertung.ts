import type {
  DFDInfo,
  DFDInfoRaw,
  DFDPosition,
  DFDPositionRaw,
  EAInfo,
  EAInfoRaw,
  EAPosition,
  EAPositionRaw,
  SIDTWInfo,
  SIDTWInfoRaw,
  SIDTWPosition,
  SIDTWPositionRaw,
} from '@/types/auswertung.types';

export const transformEAInfoResult = (bahnenRaw: EAInfoRaw[]): EAInfo[] => {
  return bahnenRaw.map(
    (bahn): EAInfo => ({
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      EAMinDistance: bahn.euclidean_min_distance,
      EAMaxDistance: bahn.euclidean_max_distance,
      EAAvgDistance: bahn.euclidean_average_distance,
      EAStdDeviation: bahn.euclidean_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};

export const transformDFDInfoResult = (bahnenRaw: DFDInfoRaw[]): DFDInfo[] => {
  return bahnenRaw.map(
    (bahn): DFDInfo => ({
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      DFDMinDistance: bahn.dfd_min_distance,
      DFDMaxDistance: bahn.dfd_max_distance,
      DFDAvgDistance: bahn.dfd_average_distance,
      DFDStdDeviation: bahn.dfd_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};

export const transformSIDTWInfoResult = (
  bahnenRaw: SIDTWInfoRaw[],
): SIDTWInfo[] => {
  return bahnenRaw.map(
    (bahn): SIDTWInfo => ({
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      SIDTWMinDistance: bahn.sidtw_min_distance,
      SIDTWMaxDistance: bahn.sidtw_max_distance,
      SIDTWAvgDistance: bahn.sidtw_average_distance,
      SIDTWStdDeviation: bahn.sidtw_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};

export const transformEADeviationResult = (
  data: EAPositionRaw[],
): EAPosition[] => {
  return data.map((item) => ({
    bahnID: item.bahn_id,
    segmentID: item.segment_id,
    EADistances: item.euclidean_distances,
    pointsOrder: item.points_order,
  }));
};

export const transformDFDDeviationResult = (
  data: DFDPositionRaw[],
): DFDPosition[] => {
  return data.map((item) => ({
    bahnID: item.bahn_id,
    segmentID: item.segment_id,
    DFDDistances: item.dfd_distances,
    DFDSollX: item.dfd_soll_x,
    DFDSollY: item.dfd_soll_y,
    DFDSollZ: item.dfd_soll_z,
    DFDIstX: item.dfd_ist_x,
    DFDIstY: item.dfd_ist_y,
    DFDIstZ: item.dfd_ist_z,
    pointsOrder: item.points_order,
  }));
};

export const transformSIDTWDeviationResult = (
  data: SIDTWPositionRaw[],
): SIDTWPosition[] => {
  return data.map((item) => ({
    bahnID: item.bahn_id,
    segmentID: item.segment_id,
    SIDTWDistances: item.sidtw_distances,
    SIDTWSollX: item.sidtw_soll_x,
    SIDTWSollY: item.sidtw_soll_y,
    SIDTWSollZ: item.sidtw_soll_z,
    SIDTWIstX: item.sidtw_ist_x,
    SIDTWIstY: item.sidtw_ist_y,
    SIDTWIstZ: item.sidtw_ist_z,
    pointsOrder: item.points_order,
  }));
};
