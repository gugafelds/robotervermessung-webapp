'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryEuclideanMetrics, TrajectoryHeader } from '@/types/main';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
  trajectoriesEuclideanMetrics: TrajectoryEuclideanMetrics[];
  euclideanDistances: any;
  setEuclidean: any;
  visibleEuclidean: boolean;
  showEuclideanPlot: any;
}

type TrajectoryProviderProps = {
  children: ReactNode;
  trajectoriesHeaderDB: TrajectoryHeader[];
  trajectoriesEuclideanMetricsDB: TrajectoryEuclideanMetrics[];
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  trajectoriesHeaderDB,
  trajectoriesEuclideanMetricsDB,
}: TrajectoryProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [trajectoriesEuclideanMetrics] = useState(trajectoriesEuclideanMetricsDB);
  const [euclideanDistances, setEuclidean] = useState([]);
  const [visibleEuclidean, showEuclideanPlot] = useState(false);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      trajectoriesEuclideanMetrics,
      euclideanDistances,
      setEuclidean,
      visibleEuclidean,
      showEuclideanPlot,
    }),
    [
      trajectoriesHeader,
      euclideanDistances,
      trajectoriesEuclideanMetrics,
      setEuclidean,
      visibleEuclidean,
      showEuclideanPlot,
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
