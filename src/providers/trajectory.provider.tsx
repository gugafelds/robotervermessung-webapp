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

import { getBahnInfo } from '@/src/actions/bewegungsdaten.service';
import type {
  BahnAccelIst,
  BahnAccelSoll,
  BahnEvents,
  BahnInfo,
  BahnJointStates,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
  BahnTwistIst,
  BahnTwistSoll,
} from '@/types/bewegungsdaten.types';
import type { PaginationResult } from '@/types/pagination.types';

export interface TrajectoryState {
  bahnInfo: BahnInfo[];
  pagination: PaginationResult | null;
  currentPage: number;
  loadPage: (page: number) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
  currentBahnInfo: BahnInfo | null;
  setCurrentBahnInfo: React.Dispatch<React.SetStateAction<BahnInfo | null>>;
  currentBahnPoseIst: BahnPoseIst[];
  setCurrentBahnPoseIst: React.Dispatch<React.SetStateAction<BahnPoseIst[]>>;
  currentBahnTwistIst: BahnTwistIst[];
  setCurrentBahnTwistIst: React.Dispatch<React.SetStateAction<BahnTwistIst[]>>;
  currentBahnAccelIst: BahnAccelIst[];
  setCurrentBahnAccelIst: React.Dispatch<React.SetStateAction<BahnAccelIst[]>>;
  currentBahnAccelSoll: BahnAccelSoll[];
  setCurrentBahnAccelSoll: React.Dispatch<
    React.SetStateAction<BahnAccelSoll[]>
  >;
  currentBahnPositionSoll: BahnPositionSoll[];
  setCurrentBahnPositionSoll: React.Dispatch<
    React.SetStateAction<BahnPositionSoll[]>
  >;
  currentBahnOrientationSoll: BahnOrientationSoll[];
  setCurrentBahnOrientationSoll: React.Dispatch<
    React.SetStateAction<BahnOrientationSoll[]>
  >;
  currentBahnTwistSoll: BahnTwistSoll[];
  setCurrentBahnTwistSoll: React.Dispatch<
    React.SetStateAction<BahnTwistSoll[]>
  >;
  currentBahnJointStates: BahnJointStates[];
  setCurrentBahnJointStates: React.Dispatch<
    React.SetStateAction<BahnJointStates[]>
  >;
  currentBahnEvents: BahnEvents[];
  setCurrentBahnEvents: React.Dispatch<React.SetStateAction<BahnEvents[]>>;
  currentBahnPoseTrans: BahnPoseTrans[];
  setCurrentBahnPoseTrans: React.Dispatch<
    React.SetStateAction<BahnPoseTrans[]>
  >;
}

type TrajectoryProviderProps = {
  children: ReactNode;
  initialBahnInfo: BahnInfo[];
  initialPagination: PaginationResult;
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  initialBahnInfo,
  initialPagination,
}: TrajectoryProviderProps) => {
  const [bahnInfo, setBahnInfo] = useState<BahnInfo[]>(initialBahnInfo);
  const [pagination, setPagination] = useState<PaginationResult | null>(
    initialPagination,
  );
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [currentBahnInfo, setCurrentBahnInfo] = useState<BahnInfo | null>(null);
  const [currentBahnPoseIst, setCurrentBahnPoseIst] = useState<BahnPoseIst[]>(
    [],
  );
  const [currentBahnTwistIst, setCurrentBahnTwistIst] = useState<
    BahnTwistIst[]
  >([]);
  const [currentBahnAccelIst, setCurrentBahnAccelIst] = useState<
    BahnAccelIst[]
  >([]);
  const [currentBahnAccelSoll, setCurrentBahnAccelSoll] = useState<
    BahnAccelSoll[]
  >([]);
  const [currentBahnPositionSoll, setCurrentBahnPositionSoll] = useState<
    BahnPositionSoll[]
  >([]);
  const [currentBahnOrientationSoll, setCurrentBahnOrientationSoll] = useState<
    BahnOrientationSoll[]
  >([]);
  const [currentBahnTwistSoll, setCurrentBahnTwistSoll] = useState<
    BahnTwistSoll[]
  >([]);
  const [currentBahnJointStates, setCurrentBahnJointStates] = useState<
    BahnJointStates[]
  >([]);
  const [currentBahnEvents, setCurrentBahnEvents] = useState<BahnEvents[]>([]);
  const [currentBahnPoseTrans, setCurrentBahnPoseTrans] = useState<
    BahnPoseTrans[]
  >([]);

  useEffect(() => {
    setBahnInfo(initialBahnInfo);
    setPagination(initialPagination);
  }, [initialBahnInfo, initialPagination]);

  // Funktion zum Laden einer bestimmten Seite - mit useCallback
  const loadPage = useCallback(
    async (page: number) => {
      if (!pagination || page < 1 || page > pagination.totalPages) {
        return;
      }

      try {
        const { bahnInfo: newBahnInfo, pagination: newPagination } =
          await getBahnInfo({
            page,
            pageSize: pagination.pageSize,
          });

        setBahnInfo(newBahnInfo);
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
      bahnInfo,
      pagination,
      currentPage,
      loadPage,
      nextPage,
      prevPage,
      currentBahnInfo,
      setCurrentBahnInfo,
      currentBahnPoseIst,
      setCurrentBahnPoseIst,
      currentBahnTwistIst,
      setCurrentBahnTwistIst,
      currentBahnAccelIst,
      setCurrentBahnAccelIst,
      currentBahnAccelSoll,
      setCurrentBahnAccelSoll,
      currentBahnPositionSoll,
      setCurrentBahnPositionSoll,
      currentBahnOrientationSoll,
      setCurrentBahnOrientationSoll,
      currentBahnTwistSoll,
      setCurrentBahnTwistSoll,
      currentBahnJointStates,
      setCurrentBahnJointStates,
      currentBahnEvents,
      setCurrentBahnEvents,
      currentBahnPoseTrans,
      setCurrentBahnPoseTrans,
    }),
    [
      bahnInfo,
      pagination,
      currentPage,
      loadPage,
      nextPage,
      prevPage,
      currentBahnInfo,
      currentBahnPoseIst,
      currentBahnTwistIst,
      currentBahnAccelIst,
      currentBahnAccelSoll,
      currentBahnPositionSoll,
      currentBahnOrientationSoll,
      currentBahnTwistSoll,
      currentBahnJointStates,
      currentBahnEvents,
      currentBahnPoseTrans,
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
