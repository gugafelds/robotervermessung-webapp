'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader } from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  euclideanDistances: any;
  setEuclidean: any;
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

  const [euclideanDistances, setEuclidean] = useState([]);
  const [visibleEuclidean, showEuclideanPlot] = useState(false);
  const [visibleDTWJohnen, showDTWJohnenPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      euclideanDistances,
      setEuclidean,
      visibleEuclidean,
      showEuclideanPlot,
      visibleDTWJohnen,
      showDTWJohnenPlot,
    }),
    [
      trajectoriesHeader,
      euclideanDistances,
      setEuclidean,
      visibleEuclidean,
      showEuclideanPlot,
      visibleDTWJohnen,
      showDTWJohnenPlot,
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
