'use client';

import type { ReactNode } from 'react';
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { getTrajInfo } from '@/src/actions/motion.service';
import type {
  TrajAccelAct,
  TrajAccelCmd,
  TrajInfo,
  TrajJointStates,
  TrajMetadataResult,
  TrajOrientationCmd,
  TrajPoseAct,
  TrajPositionCmd,
  TrajSetpoints,
  TrajVelAct,
  TrajVelCmd,
} from '@/types/motion.types';
import type { PaginationResult } from '@/types/pagination.types';

export interface TrajectoryState {
  trajInfo: TrajInfo[];
  pagination: PaginationResult | null;
  currentPage: number;
  loadPage: (page: number) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
  currentTrajInfo: TrajInfo | null;
  setCurrentTrajInfo: React.Dispatch<React.SetStateAction<TrajInfo | null>>;
  currentTrajMetadata: TrajMetadataResult | null;
  setCurrentTrajMetadata: React.Dispatch<
    React.SetStateAction<TrajMetadataResult | null>
  >;
  currentTrajPoseAct: TrajPoseAct[];
  setCurrentTrajPoseAct: React.Dispatch<React.SetStateAction<TrajPoseAct[]>>;
  currentTrajVelAct: TrajVelAct[];
  setCurrentTrajVelAct: React.Dispatch<React.SetStateAction<TrajVelAct[]>>;
  currentTrajAccelAct: TrajAccelAct[];
  setCurrentTrajAccelAct: React.Dispatch<React.SetStateAction<TrajAccelAct[]>>;
  currentTrajAccelCmd: TrajAccelCmd[];
  setCurrentTrajAccelCmd: React.Dispatch<React.SetStateAction<TrajAccelCmd[]>>;
  currentTrajPositionCmd: TrajPositionCmd[];
  setCurrentTrajPositionCmd: React.Dispatch<
    React.SetStateAction<TrajPositionCmd[]>
  >;
  currentTrajOrientationCmd: TrajOrientationCmd[];
  setCurrentTrajOrientationCmd: React.Dispatch<
    React.SetStateAction<TrajOrientationCmd[]>
  >;
  currentTrajVelCmd: TrajVelCmd[];
  setCurrentTrajVelCmd: React.Dispatch<React.SetStateAction<TrajVelCmd[]>>;
  currentTrajJointStates: TrajJointStates[];
  setCurrentTrajJointStates: React.Dispatch<
    React.SetStateAction<TrajJointStates[]>
  >;
  currentTrajSetpoints: TrajSetpoints[];
  setCurrentTrajSetpoints: React.Dispatch<
    React.SetStateAction<TrajSetpoints[]>
  >;
}

type TrajectoryProviderProps = {
  children: ReactNode;
  initialTrajInfo: TrajInfo[];
  initialPagination: PaginationResult;
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  initialTrajInfo,
  initialPagination,
}: TrajectoryProviderProps) => {
  const [trajInfo, setTrajInfo] = useState<TrajInfo[]>(initialTrajInfo);
  const [pagination, setPagination] = useState<PaginationResult | null>(
    initialPagination,
  );
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [currentTrajInfo, setCurrentTrajInfo] = useState<TrajInfo | null>(null);
  const [currentTrajMetadata, setCurrentTrajMetadata] =
    useState<TrajMetadataResult | null>(null);
  const [currentTrajPoseAct, setCurrentTrajPoseAct] = useState<TrajPoseAct[]>(
    [],
  );
  const [currentTrajVelAct, setCurrentTrajVelAct] = useState<TrajVelAct[]>([]);
  const [currentTrajAccelAct, setCurrentTrajAccelAct] = useState<
    TrajAccelAct[]
  >([]);
  const [currentTrajAccelCmd, setCurrentTrajAccelCmd] = useState<
    TrajAccelCmd[]
  >([]);
  const [currentTrajPositionCmd, setCurrentTrajPositionCmd] = useState<
    TrajPositionCmd[]
  >([]);
  const [currentTrajOrientationCmd, setCurrentTrajOrientationCmd] = useState<
    TrajOrientationCmd[]
  >([]);
  const [currentTrajVelCmd, setCurrentTrajVelCmd] = useState<TrajVelCmd[]>([]);
  const [currentTrajJointStates, setCurrentTrajJointStates] = useState<
    TrajJointStates[]
  >([]);
  const [currentTrajSetpoints, setCurrentTrajSetpoints] = useState<
    TrajSetpoints[]
  >([]);

  useEffect(() => {
    setTrajInfo(initialTrajInfo);
    setPagination(initialPagination);
  }, [initialTrajInfo, initialPagination]);

  // Funktion zum Laden einer bestimmten Seite - mit useCallback
  const loadPage = useCallback(
    async (page: number) => {
      if (!pagination || page < 1 || page > pagination.totalPages) {
        return;
      }

      try {
        const { trajInfo: newTrajInfo, pagination: newPagination } =
          await getTrajInfo({
            page,
            pageSize: pagination.pageSize,
          });

        setTrajInfo(newTrajInfo);
        setPagination(newPagination);
        setCurrentPage(page);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error loading page:', error);
      }
    },
    [pagination],
  );

  // Navigations-Hilfsfunktionen - mit useCallback
  const nextPage = useCallback(async () => {
    if (pagination?.hasNext) {
      await loadPage(currentPage + 1);
    }
  }, [pagination, currentPage, loadPage]);

  const prevPage = useCallback(async () => {
    if (pagination?.hasPrevious) {
      await loadPage(currentPage - 1);
    }
  }, [pagination, currentPage, loadPage]);

  const contextValue = useMemo(
    () => ({
      trajInfo,
      pagination,
      currentPage,
      loadPage,
      nextPage,
      prevPage,
      currentTrajInfo,
      setCurrentTrajInfo,
      currentTrajPoseAct,
      setCurrentTrajPoseAct,
      currentTrajVelAct,
      setCurrentTrajVelAct,
      currentTrajAccelAct,
      setCurrentTrajAccelAct,
      currentTrajAccelCmd,
      setCurrentTrajAccelCmd,
      currentTrajPositionCmd,
      setCurrentTrajPositionCmd,
      currentTrajOrientationCmd,
      setCurrentTrajOrientationCmd,
      currentTrajVelCmd,
      setCurrentTrajVelCmd,
      currentTrajJointStates,
      setCurrentTrajJointStates,
      currentTrajSetpoints,
      setCurrentTrajSetpoints,
      currentTrajMetadata,
      setCurrentTrajMetadata,
    }),
    [
      trajInfo,
      pagination,
      currentPage,
      loadPage,
      nextPage,
      prevPage,
      currentTrajInfo,
      currentTrajPoseAct,
      currentTrajVelAct,
      currentTrajAccelAct,
      currentTrajAccelCmd,
      currentTrajPositionCmd,
      currentTrajOrientationCmd,
      currentTrajVelCmd,
      currentTrajJointStates,
      currentTrajSetpoints,
      currentTrajMetadata,
    ],
  );

  return (
    <TrajectoryContext.Provider value={contextValue}>
      {children}
    </TrajectoryContext.Provider>
  );
};

export const useTrajectory = (): TrajectoryState => {
  const context = useContext(TrajectoryContext);
  if (context === undefined) {
    throw new Error('useTrajectory must be used within a TrajectoryProvider');
  }
  return context;
};
