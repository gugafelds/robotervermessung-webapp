'use client';

import React, { useEffect } from 'react';

import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryDTWJohnenMetrics,
  TrajectoryEuclideanMetrics,
} from '@/types/main';

type TrajectoryPageProps = {
  currentTrajectory: TrajectoryData;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
  currentDTWJohnenMetrics: TrajectoryDTWJohnenMetrics;
};

export function TrajectoryWrapper({
  currentTrajectory,
  currentEuclideanMetrics,
  currentDTWJohnenMetrics,
}: TrajectoryPageProps) {
  const { setCurrentTrajectory, setCurrentEuclidean, setCurrentDtw } =
    useTrajectory();

  useEffect(() => {
    setCurrentTrajectory(currentTrajectory);
    setCurrentEuclidean(currentEuclideanMetrics);
    setCurrentDtw(currentDTWJohnenMetrics);
  }, []);

  return (
    <>
      <TrajectoryInfo />
      <TrajectoryPlot />
    </>
  );
}
