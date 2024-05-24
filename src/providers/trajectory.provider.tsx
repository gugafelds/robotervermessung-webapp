'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader } from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  currentTrajectory: any;
  setCurrentTrajectory: any;
  currentEuclidean: any;
  setCurrentEuclidean: any;
  currentDTW: any;
  setCurrentDTW: any;
  currentDTWJohnen: any;
  setCurrentDTWJohnen: any;
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
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  trajectoriesHeaderDB,
}: TrajectoryProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);

  const [currentTrajectory, setCurrentTrajectory] = useState([]);
  const [currentEuclidean, setCurrentEuclidean] = useState([]);
  const [currentDTW, setCurrentDTW] = useState([]);
  const [currentDTWJohnen, setCurrentDTWJohnen] = useState([]);
  const [currentDFD, setCurrentDFD] = useState([]);

  const [visibleEuclidean, showEuclideanPlot] = useState(false);
  // const [visibleDTW, showDTWPlot] = useState(false);
  const [visibleDTWJohnen, showDTWJohnenPlot] = useState(false);
  // const [visibleDFD, showDFDPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      currentTrajectory,
      setCurrentTrajectory,
      currentEuclidean,
      setCurrentEuclidean,
      currentDTW,
      setCurrentDTW,
      currentDTWJohnen,
      setCurrentDTWJohnen,
      currentDFD,
      setCurrentDFD,
      visibleEuclidean,
      showEuclideanPlot,
      visibleDTWJohnen,
      showDTWJohnenPlot,
    }),
    [
      trajectoriesHeader,
      currentTrajectory,
      currentEuclidean,
      currentDTW,
      currentDTWJohnen,
      currentDFD,
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
