export interface DistributionEntry {
  bucket: number;
  count: number;
}

export interface DistributionMeta {
  useRanges: boolean;
  min?: number;
  max?: number;
  numBuckets?: number;
  unit: string;
  label: string;
}

export interface Distribution {
  data: DistributionEntry[];
  meta: DistributionMeta;
}

export interface PerformerData {
  traj_id: number;
  seg_id: number;
  sidtw_average_distance: number;
  weight: number;
  waypoints: number;
  stop_point: number;
  max_velocity: number;
  max_acceleration: number;
  trajectory: Array<{
    x: number;
    y: number;
    z: number;
  }>;
}

export interface DashboardData {
  segmentsCount: number;
  trajsCount: number;
  medianSIDTW?: number;
  meanSIDTW?: number;
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
  stats: {
    velocityDistribution: Distribution;
    weightDistribution: Distribution;
    waypointDistribution: Distribution;
    performanceSIDTWDistribution: Distribution;
    stopPointDistribution: Distribution;
  };
  workareaPoints?: Array<{
    x: number;
    y: number;
    z: number;
    sidtw: number;
  }>;
}
