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

import {
  getAuswertungBahnIDs,
  getAuswertungInfoById,
} from '@/src/actions/auswertung.service';
import type {
  AuswertungBahnIDs,
  DFDInfo,
  DFDPosition,
  DTWInfo,
  DTWPosition,
  EAInfo,
  EAPosition,
  QADInfo,
  QADOrientation,
  QDTWInfo,
  QDTWOrientation,
  SIDTWInfo,
  SIDTWPosition,
} from '@/types/auswertung.types';
import type { AuswertungIDsResponse } from '@/types/pagination.types';

export interface AuswertungState {
  auswertungBahnIDs: AuswertungBahnIDs;
  currentSIDTWInfo: SIDTWInfo[];
  setCurrentSIDTWInfo: React.Dispatch<React.SetStateAction<SIDTWInfo[]>>;
  currentDTWInfo: DTWInfo[];
  setCurrentDTWInfo: React.Dispatch<React.SetStateAction<DTWInfo[]>>;
  currentDiscreteFrechetInfo: DFDInfo[];
  setCurrentDiscreteFrechetInfo: React.Dispatch<
    React.SetStateAction<DFDInfo[]>
  >;
  currentEuclideanInfo: EAInfo[];
  setCurrentEuclideanInfo: React.Dispatch<React.SetStateAction<EAInfo[]>>;
  currentSIDTWDeviation: SIDTWPosition[];
  setCurrentSIDTWDeviation: React.Dispatch<
    React.SetStateAction<SIDTWPosition[]>
  >;
  currentDTWDeviation: DTWPosition[];
  setCurrentDTWDeviation: React.Dispatch<React.SetStateAction<DTWPosition[]>>;
  currentEuclideanDeviation: EAPosition[];
  setCurrentEuclideanDeviation: React.Dispatch<
    React.SetStateAction<EAPosition[]>
  >;
  currentDiscreteFrechetDeviation: DFDPosition[];
  setCurrentDiscreteFrechetDeviation: React.Dispatch<
    React.SetStateAction<DFDPosition[]>
  >;
  currentQADDeviation: QADOrientation[];
  setCurrentQADDeviation: React.Dispatch<
    React.SetStateAction<QADOrientation[]>
  >;
  currentQDTWDeviation: QDTWOrientation[];
  setCurrentQDTWDeviation: React.Dispatch<
    React.SetStateAction<QDTWOrientation[]>
  >;

  // Paginierungseigenschaften
  pagination: AuswertungIDsResponse['pagination'];
  currentPage: number;
  loadPage: (page: number) => Promise<void>;
  fetchInfoForBahnId: (bahnId: string) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
  isLoading: boolean;
}

type AuswertungProviderProps = {
  children: ReactNode;
  initialAuswertungBahnIDs: AuswertungBahnIDs;
  initialPagination: AuswertungIDsResponse['pagination'];
};

const AuswertungContext = createContext<AuswertungState>({} as AuswertungState);

export const AuswertungProvider = ({
  children,
  initialAuswertungBahnIDs,
  initialPagination,
}: AuswertungProviderProps) => {
  // Hauptzustand für die Auswertungsinformationen
  const [auswertungBahnIDs, setAuswertungBahnIDs] = useState<AuswertungBahnIDs>(
    initialAuswertungBahnIDs,
  );

  // Paginierungszustände
  const [pagination, setPagination] =
    useState<AuswertungIDsResponse['pagination']>(initialPagination);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Info Zustände
  const [currentSIDTWInfo, setCurrentSIDTWInfo] = useState<SIDTWInfo[]>([]);
  const [currentDTWInfo, setCurrentDTWInfo] = useState<DTWInfo[]>([]);
  const [currentDiscreteFrechetInfo, setCurrentDiscreteFrechetInfo] = useState<
    DFDInfo[]
  >([]);
  const [currentEuclideanInfo, setCurrentEuclideanInfo] = useState<EAInfo[]>(
    [],
  );
  const [currentQADInfo, setCurrentQADInfo] = useState<QADInfo[]>([]);
  const [currentQDTWInfo, setCurrentQDTWInfo] = useState<QDTWInfo[]>([]);

  // Deviation Zustände
  const [currentSIDTWDeviation, setCurrentSIDTWDeviation] = useState<
    SIDTWPosition[]
  >([]);
  const [currentDTWDeviation, setCurrentDTWDeviation] = useState<DTWPosition[]>(
    [],
  );
  const [currentDiscreteFrechetDeviation, setCurrentDiscreteFrechetDeviation] =
    useState<DFDPosition[]>([]);
  const [currentEuclideanDeviation, setCurrentEuclideanDeviation] = useState<
    EAPosition[]
  >([]);
  const [currentQADDeviation, setCurrentQADDeviation] = useState<
    QADOrientation[]
  >([]);
  const [currentQDTWDeviation, setCurrentQDTWDeviation] = useState<
    QDTWOrientation[]
  >([]);

  // Aktualisiere den Hauptzustand
  useEffect(() => {
    setAuswertungBahnIDs(initialAuswertungBahnIDs);
    setPagination(initialPagination);
    setCurrentPage(1);
  }, [initialAuswertungBahnIDs, initialPagination]);

  // Funktion zum Laden einer bestimmten Seite - mit useCallback
  const loadPage = useCallback(
    async (page: number) => {
      if (
        !pagination ||
        page < 1 ||
        (pagination.totalPages && page > pagination.totalPages)
      ) {
        return;
      }

      try {
        setIsLoading(true);

        const result = await getAuswertungBahnIDs({
          page,
          pageSize: pagination.pageSize,
        });

        setAuswertungBahnIDs(result.auswertungBahnIDs);
        setPagination(result.pagination);
        setCurrentPage(page);
      } catch (error) {
        // Using error level for actual errors
        if (process.env.NODE_ENV !== 'production') {
          // eslint-disable-next-line no-console
          console.error('Error loading page:', error);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [pagination],
  );

  // Funktion zum Laden von Info für eine spezifische Bahn-ID - mit useCallback
  const fetchInfoForBahnId = useCallback(async (bahnId: string) => {
    try {
      setIsLoading(true);

      const infoResult = await getAuswertungInfoById(bahnId);

      // Update the specific info states
      setCurrentSIDTWInfo(infoResult.info_sidtw);
      setCurrentDTWInfo(infoResult.info_dtw);
      setCurrentDiscreteFrechetInfo(infoResult.info_dfd);
      setCurrentEuclideanInfo(infoResult.info_euclidean);
      setCurrentQADInfo(infoResult.info_qad);
      setCurrentQDTWInfo(infoResult.info_qdtw);
    } catch (error) {
      // Using error level for actual errors
      if (process.env.NODE_ENV !== 'production') {
        // eslint-disable-next-line no-console
        console.error(`Error fetching info for Bahn ID ${bahnId}:`, error);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Navigations-Hilfsfunktionen mit useCallback
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
      auswertungBahnIDs,
      pagination,
      currentPage,
      loadPage,
      fetchInfoForBahnId,
      nextPage,
      prevPage,
      isLoading,
      currentSIDTWInfo,
      setCurrentSIDTWInfo,
      currentDTWInfo,
      setCurrentDTWInfo,
      currentDiscreteFrechetInfo,
      setCurrentDiscreteFrechetInfo,
      currentEuclideanInfo,
      setCurrentEuclideanInfo,
      currentQADInfo,
      setCurrentQADInfo,
      currentQDTWInfo,
      setCurrentQDTWInfo,
      currentSIDTWDeviation,
      setCurrentSIDTWDeviation,
      currentDTWDeviation,
      setCurrentDTWDeviation,
      currentDiscreteFrechetDeviation,
      setCurrentDiscreteFrechetDeviation,
      currentEuclideanDeviation,
      setCurrentEuclideanDeviation,
      currentQADDeviation,
      setCurrentQADDeviation,
      currentQDTWDeviation,
      setCurrentQDTWDeviation,
    }),
    [
      auswertungBahnIDs,
      pagination,
      currentPage,
      isLoading,
      currentSIDTWInfo,
      currentDTWInfo,
      currentDiscreteFrechetInfo,
      currentEuclideanInfo,
      currentQADInfo,
      currentQDTWInfo,
      currentSIDTWDeviation,
      currentDTWDeviation,
      currentDiscreteFrechetDeviation,
      currentEuclideanDeviation,
      currentQADDeviation,
      currentQDTWDeviation,
      loadPage,
      fetchInfoForBahnId,
      nextPage,
      prevPage,
    ],
  );

  return (
    <AuswertungContext.Provider value={contextValue}>
      {children}
    </AuswertungContext.Provider>
  );
};

export const useAuswertung = (): AuswertungState => {
  const context = useContext(AuswertungContext);
  if (context === undefined) {
    throw new Error('useAuswertung must be used within a AuswertungProvider');
  }
  return context;
};
