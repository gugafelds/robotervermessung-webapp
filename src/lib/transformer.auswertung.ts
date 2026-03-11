import type {
  EAInfo,
  EAInfoRaw,
  EAPosition,
  EAPositionRaw,
  QADInfo,
  QADInfoRaw,
  QADOrientation,
  QADOrientationRaw,
  QDTWInfo,
  QDTWInfoRaw,
  QDTWOrientation,
  QDTWOrientationRaw,
  SIDTWInfo,
  SIDTWInfoRaw,
  SIDTWPosition,
  SIDTWPositionRaw,
} from "@/types/auswertung.types";

export const transformEAInfoResult = (bahnenRaw: EAInfoRaw[]): EAInfo[] => {
  return bahnenRaw.map(
    (bahn): EAInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      EAMinDistance: bahn.euclidean_min_distance,
      EAMaxDistance: bahn.euclidean_max_distance,
      EAAvgDistance: bahn.euclidean_average_distance,
      EAStdDeviation: bahn.euclidean_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};

/*export const transformDFDInfoResult = (bahnenRaw: DFDInfoRaw[]): DFDInfo[] => {
  if (!Array.isArray(bahnenRaw)) {
    // eslint-disable-next-line no-console
    console.warn('DFDInfoRaw data is not an array, returning empty array');
    return [];
  }

  return bahnenRaw.map(
    (bahn): DFDInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      DFDMinDistance: bahn.dfd_min_distance,
      DFDMaxDistance: bahn.dfd_max_distance,
      DFDAvgDistance: bahn.dfd_average_distance,
      DFDStdDeviation: bahn.dfd_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};*/

export const transformSIDTWInfoResult = (
  bahnenRaw: SIDTWInfoRaw[],
): SIDTWInfo[] => {
  return bahnenRaw.map(
    (bahn): SIDTWInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      SIDTWMinDistance: bahn.sidtw_min_distance,
      SIDTWMaxDistance: bahn.sidtw_max_distance,
      SIDTWAvgDistance: bahn.sidtw_average_distance,
      SIDTWStdDeviation: bahn.sidtw_standard_deviation,
    }),
  );
};

export const transformQADInfoResult = (bahnenRaw: QADInfoRaw[]): QADInfo[] => {
  return bahnenRaw.map(
    (bahn): QADInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      QADMinDistance: bahn.gd_min_distance,
      QADMaxDistance: bahn.gd_max_distance,
      QADAvgDistance: bahn.gd_average_distance,
      QADStdDeviation: bahn.gd_standard_deviation,
    }),
  );
};

export const transformQDTWInfoResult = (
  bahnenRaw: QDTWInfoRaw[],
): QDTWInfo[] => {
  return bahnenRaw.map(
    (bahn): QDTWInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      QDTWMinDistance: bahn.qdtw_min_distance,
      QDTWMaxDistance: bahn.qdtw_max_distance,
      QDTWAvgDistance: bahn.qdtw_average_distance,
      QDTWStdDeviation: bahn.qdtw_standard_deviation,
    }),
  );
};

/*export const transformDTWInfoResult = (bahnenRaw: DTWInfoRaw[]): DTWInfo[] => {
  return bahnenRaw.map(
    (bahn): DTWInfo => ({
      bahnID: bahn.traj_id,
      segmentID: bahn.seg_id,
      DTWMinDistance: bahn.dtw_min_distance,
      DTWMaxDistance: bahn.dtw_max_distance,
      DTWAvgDistance: bahn.dtw_average_distance,
      DTWStdDeviation: bahn.dtw_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};*/

export const transformEADeviationResult = (
  data: EAPositionRaw[],
): EAPosition[] => {
  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    EADistances: item.ed_deviation,
    EASollX: item.ed_cmd_x,
    EASollY: item.ed_cmd_y,
    EASollZ: item.ed_cmd_z,
    EAIstX: item.ed_act_x,
    EAIstY: item.ed_act_y,
    EAIstZ: item.ed_act_z,
    pointsOrder: item.points_order,
  }));
};

/*export const transformDFDDeviationResult = (
  data: DFDPositionRaw[],
): DFDPosition[] => {
  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    DFDDistances: item.dfd_distances,
    DFDSollX: item.dfd_cmd_x,
    DFDSollY: item.dfd_cmd_y,
    DFDSollZ: item.dfd_cmd_z,
    DFDIstX: item.dfd_act_x,
    DFDIstY: item.dfd_act_y,
    DFDIstZ: item.dfd_act_z,
    pointsOrder: item.points_order,
  }));
};*/

export const transformSIDTWDeviationResult = (
  data: SIDTWPositionRaw[],
): SIDTWPosition[] => {
  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    SIDTWDistances: item.sidtw_deviation,
    SIDTWSollX: item.sidtw_cmd_x,
    SIDTWSollY: item.sidtw_cmd_y,
    SIDTWSollZ: item.sidtw_cmd_z,
    SIDTWIstX: item.sidtw_act_x,
    SIDTWIstY: item.sidtw_act_y,
    SIDTWIstZ: item.sidtw_act_z,
    pointsOrder: item.points_order,
  }));
};

/*export const transformDTWDeviationResult = (
  data: DTWPositionRaw[],
): DTWPosition[] => {
  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    DTWDistances: item.dtw_distances,
    DTWSollX: item.dtw_cmd_x,
    DTWSollY: item.dtw_cmd_y,
    DTWSollZ: item.dtw_cmd_z,
    DTWIstX: item.dtw_act_x,
    DTWIstY: item.dtw_act_y,
    DTWIstZ: item.dtw_act_z,
    pointsOrder: item.points_order,
  }));
};*/

export const transformQDTWDeviationResult = (
  data: QDTWOrientationRaw[],
): QDTWOrientation[] => {
  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    QDTWDistances: item.qdtw_deviation,
    QDTWSollX: item.qdtw_cmd_x,
    QDTWSollY: item.qdtw_cmd_y,
    QDTWSollZ: item.qdtw_cmd_z,
    QDTWSollW: item.qdtw_cmd_w,
    QDTWIstX: item.qdtw_act_x,
    QDTWIstY: item.qdtw_act_y,
    QDTWIstZ: item.qdtw_act_z,
    QDTWIstW: item.qdtw_act_w,
    pointsOrder: item.points_order,
  }));
};

export const transformQADDeviationResult = (
  data: QADOrientationRaw[] | undefined,
): QADOrientation[] => {
  if (!Array.isArray(data)) {
    console.warn(
      "QADDeviation data is undefined or not an array, returning empty array",
    );
    return [];
  }

  return data.map((item) => ({
    bahnID: item.traj_id,
    segmentID: item.seg_id,
    QADDistances: item.gd_deviation,
    QADSollX: item.gd_cmd_x,
    QADSollY: item.gd_cmd_y,
    QADSollZ: item.gd_cmd_z,
    QADSollW: item.gd_cmd_w,
    QADIstX: item.gd_act_x,
    QADIstY: item.gd_act_y,
    QADIstZ: item.gd_act_z,
    QADIstW: item.gd_act_w,
    pointsOrder: item.points_order,
  }));
};
