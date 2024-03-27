'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useMemo, useState } from 'react';

import type { TrajectoryHeader } from '@/types/main';

import { json } from '../lib/functions';

export interface TrajectoryState {
  trajectoriesHeader: TrajectoryHeader[];
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

  const contextValue = useMemo(
    () => ({
      trajectoriesHeader,
    }),
    [trajectoriesHeader],
  );

  return (
    <TrajectoryContext.Provider value={json(contextValue)}>
      {children}
    </TrajectoryContext.Provider>
  );
};

export const useTrajectory = (): TrajectoryState =>
  useContext(TrajectoryContext);
