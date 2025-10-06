export interface DistributionEntry {
  bucket: number;
  count: number;
}

export interface DashboardData {
  filenamesCount: number;
  bahnenCount: number;
  stats: {
    velocityDistribution: DistributionEntry[];
    weightDistribution: DistributionEntry[];
    waypointDistribution: DistributionEntry[];
    performanceSIDTWDistribution: DistributionEntry[];
    stopPointDistribution: DistributionEntry[];
    waitTimeDistribution: DistributionEntry[];
  };
  workareaPoints: Array<{
    x: number;
    y: number;
    z: number;
    sidtw: number;
  }>;
}
