import type {
    EDInfo,
    EDInfoRaw,
    EDPosition,
    EDPositionRaw,
    GDInfo,
    GDInfoRaw,
    GDOrientation,
    GDOrientationRaw,
    QDTWInfo,
    QDTWInfoRaw,
    QDTWOrientation,
    QDTWOrientationRaw,
    SIDTWInfo,
    SIDTWInfoRaw,
    SIDTWPosition,
    SIDTWPositionRaw,
} from "@/types/evaluation.types";

export const transformEDInfoResult = (trajsRaw: EDInfoRaw[]): EDInfo[] => {
  return trajsRaw.map(
    (bahn): EDInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      EDMinDistance: bahn.euclidean_min_distance,
      EDMaxDistance: bahn.euclidean_max_distance,
      EDAvgDistance: bahn.euclidean_average_distance,
      EDStdDeviation: bahn.euclidean_standard_deviation,
    }),
  );
};

export const transformSIDTWInfoResult = (
  trajsRaw: SIDTWInfoRaw[],
): SIDTWInfo[] => {
  return trajsRaw.map(
    (bahn): SIDTWInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      SIDTWMinDistance: bahn.sidtw_min_distance,
      SIDTWMaxDistance: bahn.sidtw_max_distance,
      SIDTWAvgDistance: bahn.sidtw_average_distance,
      SIDTWStdDeviation: bahn.sidtw_standard_deviation,
    }),
  );
};

export const transformGDInfoResult = (trajsRaw: GDInfoRaw[]): GDInfo[] => {
  return trajsRaw.map(
    (bahn): GDInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      GDMinDistance: bahn.gd_min_distance,
      GDMaxDistance: bahn.gd_max_distance,
      GDAvgDistance: bahn.gd_average_distance,
      GDStdDeviation: bahn.gd_standard_deviation,
    }),
  );
};

export const transformQDTWInfoResult = (
  trajsRaw: QDTWInfoRaw[],
): QDTWInfo[] => {
  return trajsRaw.map(
    (bahn): QDTWInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      QDTWMinDistance: bahn.qdtw_min_distance,
      QDTWMaxDistance: bahn.qdtw_max_distance,
      QDTWAvgDistance: bahn.qdtw_average_distance,
      QDTWStdDeviation: bahn.qdtw_standard_deviation,
    }),
  );
};

/*export const transformDTWInfoResult = (trajsRaw: DTWInfoRaw[]): DTWInfo[] => {
  return trajsRaw.map(
    (bahn): DTWInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      DTWMinDistance: bahn.dtw_min_distance,
      DTWMaxDistance: bahn.dtw_max_distance,
      DTWAvgDistance: bahn.dtw_average_distance,
      DTWStdDeviation: bahn.dtw_standard_deviation,
      evaluation: bahn.evaluation,
    }),
  );
};*/

export const transformEDDeviationResult = (
  data: EDPositionRaw[],
): EDPosition[] => {
  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    EDDistances: item.ed_deviation,
    EDSollX: item.ed_cmd_x,
    EDSollY: item.ed_cmd_y,
    EDSollZ: item.ed_cmd_z,
    EDIstX: item.ed_act_x,
    EDIstY: item.ed_act_y,
    EDIstZ: item.ed_act_z,
    pointsOrder: item.points_order,
  }));
};

export const transformSIDTWDeviationResult = (
  data: SIDTWPositionRaw[],
): SIDTWPosition[] => {
  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
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
    trajID: item.traj_id,
    segID: item.seg_id,
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
    trajID: item.traj_id,
    segID: item.seg_id,
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

export const transformGDDeviationResult = (
  data: GDOrientationRaw[] | undefined,
): GDOrientation[] => {
  if (!Array.isArray(data)) {
    console.warn(
      "GDDeviation data is undefined or not an array, returning empty array",
    );
    return [];
  }

  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    GDDistances: item.gd_deviation,
    GDSollX: item.gd_cmd_x,
    GDSollY: item.gd_cmd_y,
    GDSollZ: item.gd_cmd_z,
    GDSollW: item.gd_cmd_w,
    GDIstX: item.gd_act_x,
    GDIstY: item.gd_act_y,
    GDIstZ: item.gd_act_z,
    GDIstW: item.gd_act_w,
    pointsOrder: item.points_order,
  }));
};
