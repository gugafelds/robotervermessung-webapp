import React from 'react';

import {
  getDFDMetricsById,
  getDTWJohnenMetricsById,
  getDTWMetricsById,
  getEuclideanMetricsById,
  getLCSSMetricsById,
  getTrajectoryById,
  getBahnPoseIstById,
  getBahnTwistIstById,
  getBahnAccelIstById,
  getBahnPositionSollById,
  getBahnOrientationSollById,
} from '@/src/actions/trajectory.service';
import { TrajectoryWrapper } from '@/src/app/trajectories/components/TrajectoryWrapper';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);
  const currentBahnPoseIst = await getBahnPoseIstById(params.id);
  const currentBahnTwistIst = await getBahnTwistIstById(params.id);
  const currentBahnAccelIst = await getBahnAccelIstById(params.id);
  const currentBahnPositionSoll = await getBahnPositionSollById(params.id);
  const currentBahnOrientationSoll = await getBahnOrientationSollById(params.id);
  const currentEuclideanMetrics = await getEuclideanMetricsById(params.id);
  const currentDTWMetrics = await getDTWMetricsById(params.id);
  const currentDTWJohnenMetrics = await getDTWJohnenMetricsById(params.id);
  const currentDFDMetrics = await getDFDMetricsById(params.id);
  const currentLCSSMetrics = await getLCSSMetricsById(params.id);

  return (
    <TrajectoryWrapper
      currentTrajectory={json(currentTrajectory)}
      currentBahnPoseIst={json(currentBahnPoseIst)}
      currentBahnTwistIst={json(currentBahnTwistIst)}
      currentBahnAccelIst={json(currentBahnAccelIst)}
      currentBahnPositionSoll={json(currentBahnPositionSoll)}
      currentBahnOrientationSoll={json(currentBahnOrientationSoll)}
      currentDTWMetrics={json(currentDTWMetrics)}
      currentEuclideanMetrics={json(currentEuclideanMetrics)}
      currentDTWJohnenMetrics={json(currentDTWJohnenMetrics)}
      currentDFDMetrics={json(currentDFDMetrics)}
      currentLCSSMetrics={json(currentLCSSMetrics)}
    />
  );
}
