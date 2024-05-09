import React from 'react';

import {
  getDTWJohnenMetricsById,
  getEuclideanMetricsById,
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
  const currentDTWJohnenMetrics = await getDTWJohnenMetricsById(params.id);

  return (
    <TrajectoryWrapper
      currentTrajectory={json(currentTrajectory)}
      currentEuclideanMetrics={json(currentEuclideanMetrics)}
      currentDTWJohnenMetrics={json(currentDTWJohnenMetrics)}
    />
  );
}
