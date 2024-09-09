'use client';

import React, { useEffect } from 'react';

import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { SegmentInfo } from '@/src/app/trajectories/components/SegmentInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryDFDMetrics,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWMetrics,
  TrajectoryEuclideanMetrics,
  TrajectoryLCSSMetrics,
} from '@/types/main';

type TrajectoryPageProps = {
  currentTrajectory: TrajectoryData;
  currentDTWMetrics: TrajectoryDTWMetrics;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
  currentDTWJohnenMetrics: TrajectoryDTWJohnenMetrics;
  currentDFDMetrics: TrajectoryDFDMetrics;
  currentLCSSMetrics: TrajectoryLCSSMetrics;
};

export function TrajectoryWrapper({
  currentTrajectory,
  currentEuclideanMetrics,
  currentDTWMetrics,
  currentDTWJohnenMetrics,
  currentDFDMetrics,
  currentLCSSMetrics,
}: TrajectoryPageProps) {
  const {
    setCurrentTrajectory,
    setCurrentEuclidean,
    setCurrentDTWJohnen,
    setCurrentLCSS,
    setCurrentDTW,
    setCurrentDFD,
  } = useTrajectory();

  useEffect(() => {
    setCurrentDTW(currentDTWMetrics);
    setCurrentTrajectory(currentTrajectory);
    setCurrentEuclidean(currentEuclideanMetrics);
    setCurrentDTWJohnen(currentDTWJohnenMetrics);
    setCurrentDFD(currentDFDMetrics);
    setCurrentLCSS(currentLCSSMetrics);
  }, []);

  const isSegment = currentTrajectory.segmentId && currentTrajectory.segmentId.includes('_');
  
  return (
    <>
      {isSegment ? <SegmentInfo /> : <TrajectoryInfo />}
      <TrajectoryPlot />
    </>
  );
}