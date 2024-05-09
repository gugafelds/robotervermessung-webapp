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
  currentDtw: any;
  setCurrentDtw: any;
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
  const [currentDtw, setCurrentDtw] = useState([]);

  const [visibleEuclidean, showEuclideanPlot] = useState(false);
  const [visibleDTWJohnen, showDTWJohnenPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      currentTrajectory,
      setCurrentTrajectory,
      currentEuclidean,
      setCurrentEuclidean,
      currentDtw,
      setCurrentDtw,
      visibleEuclidean,
      showEuclideanPlot,
      visibleDTWJohnen,
      showDTWJohnenPlot,
    }),
    [
      trajectoriesHeader,
      currentTrajectory,
      currentEuclidean,
      currentDtw,
      visibleEuclidean,
      visibleDTWJohnen,
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
