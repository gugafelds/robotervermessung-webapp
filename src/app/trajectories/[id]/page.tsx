import React from 'react';

import {
  getDTWJohnenMetricsById,
  getEuclideanMetricsById,
  getTrajectoryById,
} from '@/src/actions/trajectory.service';
import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);
  const currentEuclideanMetrics = await getEuclideanMetricsById(params.id);
  const currentDTWJohnenMetrics = await getDTWJohnenMetricsById(params.id);

  return (
    <>
      <TrajectoryInfo
        currentTrajectory={json(currentTrajectory)}
        currentDTWJohnenMetrics={json(currentDTWJohnenMetrics)}
        currentEuclideanMetrics={json(currentEuclideanMetrics)}
      />

      <TrajectoryPlot
        currentTrajectory={json(currentTrajectory)}
        currentEuclideanMetrics={json(currentEuclideanMetrics)}
        currentDTWJohnenMetrics={json(currentDTWJohnenMetrics)}
      />
    </>
  );
}
