'use client';

import React, { useEffect } from 'react';

import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryDFDMetrics,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWMetrics,
  TrajectoryEuclideanMetrics,
} from '@/types/main';

type TrajectoryPageProps = {
  currentTrajectory: TrajectoryData;
  currentDTWMetrics: TrajectoryDTWMetrics;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
  currentDTWJohnenMetrics: TrajectoryDTWJohnenMetrics;
  currentDFDMetrics: TrajectoryDFDMetrics;
};

export function TrajectoryWrapper({
  currentTrajectory,
  currentEuclideanMetrics,
  currentDTWMetrics,
  currentDTWJohnenMetrics,
  currentDFDMetrics,
}: TrajectoryPageProps) {
  const {
    setCurrentTrajectory,
    setCurrentEuclidean,
    setCurrentDTWJohnen,
    setCurrentDTW,
    setCurrentDFD,
  } = useTrajectory();

  useEffect(() => {
    setCurrentDTW(currentDTWMetrics);
    setCurrentTrajectory(currentTrajectory);
    setCurrentEuclidean(currentEuclideanMetrics);
    setCurrentDTWJohnen(currentDTWJohnenMetrics);
    setCurrentDFD(currentDFDMetrics);
  }, []);

  return (
    <>
      <TrajectoryInfo />
      <TrajectoryPlot />
    </>
  );
}
