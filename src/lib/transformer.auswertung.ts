import type {
  DFDInfo,
  DFDInfoRaw,
  DFDPosition,
  DFDPositionRaw,
  DTWInfo,
  DTWInfoRaw,
  DTWPosition,
  DTWPositionRaw,
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
  if (!Array.isArray(bahnenRaw)) {
    // eslint-disable-next-line no-console
    console.warn('DFDInfoRaw data is not an array, returning empty array');
    return [];
  }

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

export const transformDTWInfoResult = (bahnenRaw: DTWInfoRaw[]): DTWInfo[] => {
  return bahnenRaw.map(
    (bahn): DTWInfo => ({
      bahnID: bahn.bahn_id,
      segmentID: bahn.segment_id,
      DTWMinDistance: bahn.dtw_min_distance,
      DTWMaxDistance: bahn.dtw_max_distance,
      DTWAvgDistance: bahn.dtw_average_distance,
      DTWStdDeviation: bahn.dtw_standard_deviation,
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
    EASollX: item.ea_soll_x,
    EASollY: item.ea_soll_y,
    EASollZ: item.ea_soll_z,
    EAIstX: item.ea_ist_x,
    EAIstY: item.ea_ist_y,
    EAIstZ: item.ea_ist_z,
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

export const transformDTWDeviationResult = (
  data: DTWPositionRaw[],
): DTWPosition[] => {
  return data.map((item) => ({
    bahnID: item.bahn_id,
    segmentID: item.segment_id,
    DTWDistances: item.dtw_distances,
    DTWSollX: item.dtw_soll_x,
    DTWSollY: item.dtw_soll_y,
    DTWSollZ: item.dtw_soll_z,
    DTWIstX: item.dtw_ist_x,
    DTWIstY: item.dtw_ist_y,
    DTWIstZ: item.dtw_ist_z,
    pointsOrder: item.points_order,
  }));
};
