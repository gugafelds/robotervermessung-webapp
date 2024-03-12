'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { Trajectory } from '@/types/main';

export interface AppState {
  trajectories: Trajectory[];
}

type AppProviderProps = {
  children: ReactNode;
  trajectoriesDb: Trajectory[];
};

const AppContext = createContext<AppState>({} as AppState);

export const AppProvider = ({ children, trajectoriesDb }: AppProviderProps) => {
  const [trajectories] = useState(trajectoriesDb);

  const contextValue = useMemo(
    () => ({
      trajectories,
    }),
    [trajectories],
  );

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  );
};

export const useApp = (): AppState => useContext(AppContext);
