'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader } from '@/types/main';

export interface AppState {
  trajectoriesHeader: TrajectoryHeader[];
}

type AppProviderProps = {
  children: ReactNode;
  trajectoriesHeaderDB: TrajectoryHeader[];
};

const AppContext = createContext<AppState>({} as AppState);

export const AppProvider = ({
  children,
  trajectoriesHeaderDB,
}: AppProviderProps) => {
  const [trajectoriesHeader] = useState(trajectoriesHeaderDB);

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
    }),
    [trajectoriesHeader],
  );

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  );
};

export const useApp = (): AppState => useContext(AppContext);
