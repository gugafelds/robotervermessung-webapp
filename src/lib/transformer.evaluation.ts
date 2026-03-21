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
} from '@/types/evaluation.types';

export const transformEDInfoResult = (trajsRaw: EDInfoRaw[]): EDInfo[] => {
  return trajsRaw.map(
    (bahn): EDInfo => ({
      trajID: bahn.traj_id,
      segID: bahn.seg_id,
      EDMinDistance: bahn.ed_min_distance,
      EDMaxDistance: bahn.ed_max_distance,
      EDAvgDistance: bahn.ed_average_distance,
      EDStdDeviation: bahn.ed_standard_deviation,
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

/* export const transformDTWInfoResult = (trajsRaw: DTWInfoRaw[]): DTWInfo[] => {
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
}; */

export const transformEDDeviationResult = (
  data: EDPositionRaw[],
): EDPosition[] => {
  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    EDDistances: item.ed_deviation,
    EDCmdX: item.ed_cmd_x,
    EDCmdY: item.ed_cmd_y,
    EDCmdZ: item.ed_cmd_z,
    EDActX: item.ed_act_x,
    EDActY: item.ed_act_y,
    EDActZ: item.ed_act_z,
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
    SIDTWCmdX: item.sidtw_cmd_x,
    SIDTWCmdY: item.sidtw_cmd_y,
    SIDTWCmdZ: item.sidtw_cmd_z,
    SIDTWActX: item.sidtw_act_x,
    SIDTWActY: item.sidtw_act_y,
    SIDTWActZ: item.sidtw_act_z,
    pointsOrder: item.points_order,
  }));
};

/* export const transformDTWDeviationResult = (
  data: DTWPositionRaw[],
): DTWPosition[] => {
  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    DTWDistances: item.dtw_distances,
    DTWCmdX: item.dtw_cmd_x,
    DTWCmdY: item.dtw_cmd_y,
    DTWCmdZ: item.dtw_cmd_z,
    DTWActX: item.dtw_act_x,
    DTWActY: item.dtw_act_y,
    DTWActZ: item.dtw_act_z,
    pointsOrder: item.points_order,
  }));
}; */

export const transformQDTWDeviationResult = (
  data: QDTWOrientationRaw[],
): QDTWOrientation[] => {
  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    QDTWDistances: item.qdtw_deviation,
    QDTWCmdX: item.qdtw_cmd_x,
    QDTWCmdY: item.qdtw_cmd_y,
    QDTWCmdZ: item.qdtw_cmd_z,
    QDTWCmdW: item.qdtw_cmd_w,
    QDTWActX: item.qdtw_act_x,
    QDTWActY: item.qdtw_act_y,
    QDTWActZ: item.qdtw_act_z,
    QDTWActW: item.qdtw_act_w,
    pointsOrder: item.points_order,
  }));
};

export const transformGDDeviationResult = (
  data: GDOrientationRaw[] | undefined,
): GDOrientation[] => {
  if (!Array.isArray(data)) {
    return [];
  }

  return data.map((item) => ({
    trajID: item.traj_id,
    segID: item.seg_id,
    GDDistances: item.gd_deviation,
    GDCmdX: item.gd_cmd_x,
    GDCmdY: item.gd_cmd_y,
    GDCmdZ: item.gd_cmd_z,
    GDCmdW: item.gd_cmd_w,
    GDActX: item.gd_act_x,
    GDActY: item.gd_act_y,
    GDActZ: item.gd_act_z,
    GDActW: item.gd_act_w,
    pointsOrder: item.points_order,
  }));
};
