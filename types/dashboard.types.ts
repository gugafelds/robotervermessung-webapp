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
  metric_value: number;
  weight: number;
  waypoints: number;
  stop_point: number;
  max_velocity: number;
  max_acceleration: number;
  tag?: string;
  trajectory?: Array<{ x: number; y: number; z: number }>;
}

export interface DashboardData {
  segmentsCount: number;
  trajsCount: number;
  medianSIDTW?: number;
  meanSIDTW?: number;
  stats: {
    velocityDistribution: Distribution;
    weightDistribution: Distribution;
    waypointDistribution: Distribution;
    performanceSIDTWDistribution: Distribution;
    stopPointDistribution: Distribution;
  };
}

export type MetricType = 'sidtw' | 'ed' | 'qdtw' | 'gd';

export const METRICS: Record<MetricType, { label: string; unit: string }> = {
  sidtw: { label: 'SIDTW', unit: 'mm' },
  ed:    { label: 'ED',    unit: 'mm' },
  qdtw:  { label: 'QDTW', unit: 'rad' },
  gd:    { label: 'GD',   unit: 'rad' },
};
