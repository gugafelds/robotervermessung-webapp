'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader, SegmentHeader } from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  segmentsHeader: SegmentHeader[];
  currentTrajectory: any;
  setCurrentTrajectory: any;
  currentSegment: any;
  setCurrentSegment: any;
  currentEuclidean: any;
  setCurrentEuclidean: any;
  currentDTW: any;
  setCurrentDTW: any;
  currentDTWJohnen: any;
  setCurrentDTWJohnen: any;
  currentLCSS: any;
  setCurrentLCSS: any;
  currentDFD: any;
  setCurrentDFD: any;
  visibleEuclidean: boolean;
  showEuclideanPlot: any;
  visibleDTWJohnen: boolean;
  showDTWJohnenPlot: any;
}

type TrajectoryProviderProps = {
  children: ReactNode;
  trajectoriesHeaderDB: TrajectoryHeader[];
  segmentsHeaderDB: SegmentHeader[];
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  trajectoriesHeaderDB,
  segmentsHeaderDB,
}: TrajectoryProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [segmentsHeader] = useState(segmentsHeaderDB);

  const [currentTrajectory, setCurrentTrajectory] = useState([]);
  const [currentSegment, setCurrentSegment] = useState([]);
  const [currentEuclidean, setCurrentEuclidean] = useState([]);
  const [currentDTW, setCurrentDTW] = useState([]);
  const [currentDTWJohnen, setCurrentDTWJohnen] = useState([]);
  const [currentDFD, setCurrentDFD] = useState([]);
  const [currentLCSS, setCurrentLCSS] = useState([]);

  const [visibleEuclidean, showEuclideanPlot] = useState(false);
  // const [visibleDTW, showDTWPlot] = useState(false);
  const [visibleDTWJohnen, showDTWJohnenPlot] = useState(false);
  // const [visibleDFD, showDFDPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      segmentsHeader,
      currentTrajectory,
      setCurrentTrajectory,
      currentSegment,
      setCurrentSegment,
      currentEuclidean,
      setCurrentEuclidean,
      currentDTW,
      setCurrentDTW,
      currentDTWJohnen,
      setCurrentDTWJohnen,
      currentDFD,
      setCurrentDFD,
      currentLCSS,
      setCurrentLCSS,
      visibleEuclidean,
      showEuclideanPlot,
      visibleDTWJohnen,
      showDTWJohnenPlot,
    }),
    [
      trajectoriesHeader,
      segmentsHeader,
      currentTrajectory,
      currentSegment,
      currentEuclidean,
      currentDTW,
      currentDTWJohnen,
      currentDFD,
      currentLCSS,
      visibleEuclidean,
      // visibleDTW,
      visibleDTWJohnen,
      // visibleDFD,
    ],
  );

  return (
    <TrajectoryContext.Provider value={contextValue}>
      {children}
    </TrajectoryContext.Provider>
  );
};

export const useTrajectory = (): TrajectoryState =>
  useContext(TrajectoryContext);
