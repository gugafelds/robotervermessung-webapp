'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

export interface AppState {
  trajectoriesHeader: TrajectoryHeader[];
  trajectoriesData: TrajectoryData[];
  currentTrajectory: TrajectoryData;
  setCurrentTrajectory: (data: TrajectoryData) => void;
}

type AppProviderProps = {
  children: ReactNode;
  trajectoriesHeaderDB: TrajectoryHeader[];
  trajectoriesDataDB: TrajectoryData[];
  currentTrajectoryDB: TrajectoryData;
};

const AppContext = createContext<AppState>({} as AppState);

export const AppProvider = ({
  children,
  trajectoriesHeaderDB,
  trajectoriesDataDB,
  currentTrajectoryDB,
}: AppProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [trajectoriesData] = useState(trajectoriesDataDB);
  const [currentTrajectory, setCurrentTrajectory] =
    useState(currentTrajectoryDB);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      trajectoriesData,
      currentTrajectory,
      setCurrentTrajectory,
    }),
    [trajectoriesHeader, trajectoriesData, currentTrajectory],
  );

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  );
};

export const useApp = (): AppState => useContext(AppContext);
