'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

export interface AppState {
  trajectoriesHeader: TrajectoryHeader[];
  trajectoriesData: TrajectoryData[];
}

type AppProviderProps = {
  children: ReactNode;
  trajectoriesHeaderDB: TrajectoryHeader[];
  trajectoriesDataDB: TrajectoryData[];
};

const AppContext = createContext<AppState>({} as AppState);

export const AppProvider = ({
  children,
  trajectoriesHeaderDB,
  trajectoriesDataDB,
}: AppProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);
  const [trajectoriesData] = useState(trajectoriesDataDB);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
      trajectoriesData,
    }),
    [trajectoriesHeader, trajectoriesData],
  );

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  );
};

export const useApp = (): AppState => useContext(AppContext);
