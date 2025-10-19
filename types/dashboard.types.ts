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
  bahn_id: number;
  sidtw_average_distance: number;
  weight: number;
  waypoints: number;
  stop_point: number;
  wait_time: number;
  max_velocity: number;
  max_acceleration: number;
  trajectory: Array<{
    x: number;
    y: number;
    z: number;
  }>;
}

export interface DashboardData {
  filenamesCount: number;
  bahnenCount: number;
  medianSIDTW?: number;
  meanSIDTW?: number;
  bestPerformers?: PerformerData[]; // NEU
  worstPerformers?: PerformerData[]; // NEU
  stats: {
    velocityDistribution: Distribution;
    weightDistribution: Distribution;
    waypointDistribution: Distribution;
    performanceSIDTWDistribution: Distribution;
    stopPointDistribution: Distribution;
    waitTimeDistribution: Distribution;
  };
  workareaPoints?: Array<{
    x: number;
    y: number;
    z: number;
    sidtw: number;
  }>;
}
