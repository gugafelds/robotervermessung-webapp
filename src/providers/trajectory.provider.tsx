'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader, SegmentHeader, BahnInfo, BahnPoseIst, BahnTwistIst, BahnAccelIst, BahnPositionSoll, BahnOrientationSoll } from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  bahnInfo: BahnInfo[];
  currentBahnPoseIst: BahnPoseIst[];
  setCurrentBahnPoseIst: any;
  currentBahnTwistIst: BahnTwistIst[];
  setCurrentBahnTwistIst: any;
  currentBahnAccelIst: BahnAccelIst[];
  setCurrentBahnAccelIst: any;
  currentBahnPositionSoll: BahnPositionSoll[];
  setCurrentBahnPositionSoll: any;
  currentBahnOrientationSoll: BahnOrientationSoll[];
  setCurrentBahnOrientationSoll: any;
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
  bahnInfoDB: BahnInfo[];
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  trajectoriesHeaderDB,
  segmentsHeaderDB,
  bahnInfoDB,
}: TrajectoryProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [segmentsHeader] = useState(segmentsHeaderDB);
  const [bahnInfo] = useState(bahnInfoDB);

  const [currentTrajectory, setCurrentTrajectory] = useState([]);
  const [currentBahnPoseIst, setCurrentBahnPoseIst] = useState([]);
  const [currentBahnTwistIst, setCurrentBahnTwistIst] = useState([]);
  const [currentBahnAccelIst, setCurrentBahnAccelIst] = useState([]);
  const [currentBahnPositionSoll, setCurrentBahnPositionSoll] = useState([]);
  const [currentBahnOrientationSoll, setCurrentBahnOrientationSoll] = useState([]);
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
      bahnInfo,
      currentBahnPoseIst,
      setCurrentBahnPoseIst,
      currentBahnTwistIst,
      setCurrentBahnTwistIst,
      currentBahnAccelIst,
      setCurrentBahnAccelIst,
      currentBahnPositionSoll,
      setCurrentBahnPositionSoll,
      currentBahnOrientationSoll,
      setCurrentBahnOrientationSoll,
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
      bahnInfo,
      currentBahnPoseIst,
      currentBahnTwistIst,
      currentBahnAccelIst,
      currentBahnPositionSoll,
      currentBahnOrientationSoll,
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
