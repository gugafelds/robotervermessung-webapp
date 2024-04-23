'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type {
  TrajectoryEuclideanMetrics,
  TrajectoryDTWJohnenMetrics,
  TrajectoryHeader,
} from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  trajectoriesEuclideanMetrics: TrajectoryEuclideanMetrics[];
  trajectoriesDTWJohnenMetrics: TrajectoryDTWJohnenMetrics[];
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
  trajectoriesEuclideanMetricsDB: TrajectoryEuclideanMetrics[];
  trajectoriesDTWJohnenMetricsDB: TrajectoryDTWJohnenMetrics[];
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  trajectoriesHeaderDB,
  trajectoriesEuclideanMetricsDB,
  trajectoriesDTWJohnenMetricsDB,
}: TrajectoryProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [trajectoriesEuclideanMetrics] = useState(
    trajectoriesEuclideanMetricsDB,
  );
  const [trajectoriesDTWJohnenMetrics] = useState(
    trajectoriesDTWJohnenMetricsDB,
  );


  const [euclideanDistances, setEuclidean] = useState([]);
  const [visibleEuclidean, showEuclideanPlot] = useState(false);
  const [visibleDTWJohnen, showDTWJohnenPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      trajectoriesEuclideanMetrics,
      trajectoriesDTWJohnenMetrics,
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
      trajectoriesEuclideanMetrics,
      trajectoriesDTWJohnenMetrics,
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
