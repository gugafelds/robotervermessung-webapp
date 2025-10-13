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

export interface DashboardData {
  filenamesCount: number;
  bahnenCount: number;
  stats: {
    velocityDistribution: Distribution;
    weightDistribution: Distribution;
    waypointDistribution: Distribution;
    performanceSIDTWDistribution: Distribution;
    stopPointDistribution: Distribution;
    waitTimeDistribution: Distribution;
  };
  // Optional, da WorkareaPlot jetzt selbst lädt
  workareaPoints?: Array<{
    x: number;
    y: number;
    z: number;
    sidtw: number;
  }>;
}
