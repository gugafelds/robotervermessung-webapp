'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

export interface AppState {
  trajectories: any[];
}

type AppProviderProps = {
  children: ReactNode;
  trajectoriesDb: any[];
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
