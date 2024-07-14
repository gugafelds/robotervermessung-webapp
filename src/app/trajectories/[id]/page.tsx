import React from 'react';

import {
  getDFDMetricsById,
  getDTWJohnenMetricsById,
  getDTWMetricsById,
  getEuclideanMetricsById,
  getLCSSMetricsById,
  getTrajectoryById,
} from '@/src/actions/trajectory.service';
import { TrajectoryWrapper } from '@/src/app/trajectories/components/TrajectoryWrapper';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);
  const currentEuclideanMetrics = await getEuclideanMetricsById(params.id);
  const currentDTWMetrics = await getDTWMetricsById(params.id);
  const currentDTWJohnenMetrics = await getDTWJohnenMetricsById(params.id);
  const currentDFDMetrics = await getDFDMetricsById(params.id);
  const currentLCSSMetrics = await getLCSSMetricsById(params.id);

  return (
    <TrajectoryWrapper
      currentTrajectory={json(currentTrajectory)}
      currentDTWMetrics={json(currentDTWMetrics)}
      currentEuclideanMetrics={json(currentEuclideanMetrics)}
      currentDTWJohnenMetrics={json(currentDTWJohnenMetrics)}
      currentDFDMetrics={json(currentDFDMetrics)}
      currentLCSSMetrics={json(currentLCSSMetrics)}
    />
  );
}
