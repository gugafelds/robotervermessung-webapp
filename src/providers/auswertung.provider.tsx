'use client';

import type { ReactNode } from 'react';
import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import type {
  AuswertungInfo,
  DFDDeviation,
  DFDInfo,
  EADeviation,
  EAInfo,
  SIDTWDeviation,
  SIDTWInfo,
} from '@/types/auswertung.types';

export interface AuswertungState {
  auswertungInfo: AuswertungInfo;
  currentSIDTWInfo: SIDTWInfo[];
  setCurrentSIDTWInfo: React.Dispatch<React.SetStateAction<SIDTWInfo[]>>;
  currentDiscreteFrechetInfo: DFDInfo[];
  setCurrentDiscreteFrechetInfo: React.Dispatch<
    React.SetStateAction<DFDInfo[]>
  >;
  currentEuclideanInfo: EAInfo[];
  setCurrentEuclideanInfo: React.Dispatch<React.SetStateAction<EAInfo[]>>;
  currentSIDTWDeviation: SIDTWDeviation[];
  setCurrentSIDTWDeviation: React.Dispatch<
    React.SetStateAction<SIDTWDeviation[]>
  >;
  currentEuclideanDeviation: EADeviation[];
  setCurrentEuclideanDeviation: React.Dispatch<
    React.SetStateAction<EADeviation[]>
  >;
  currentDiscreteFrechetDeviation: DFDDeviation[];
  setCurrentDiscreteFrechetDeviation: React.Dispatch<
    React.SetStateAction<DFDDeviation[]>
  >;
}

type AuswertungProviderProps = {
  children: ReactNode;
  initialAuswertungInfo: AuswertungInfo;
};

const AuswertungContext = createContext<AuswertungState>({} as AuswertungState);

export const AuswertungProvider = ({
  children,
  initialAuswertungInfo,
}: AuswertungProviderProps) => {
  // Hauptzustand für die gesamten Auswertungsinformationen
  const [auswertungInfo, setAuswertungInfo] = useState<AuswertungInfo>(
    initialAuswertungInfo,
  );

  // Info Zustände
  const [currentSIDTWInfo, setCurrentSIDTWInfo] = useState<SIDTWInfo[]>([]);
  const [currentDiscreteFrechetInfo, setCurrentDiscreteFrechetInfo] = useState<
    DFDInfo[]
  >([]);
  const [currentEuclideanInfo, setCurrentEuclideanInfo] = useState<EAInfo[]>(
    [],
  );

  // Deviation Zustände
  const [currentSIDTWDeviation, setCurrentSIDTWDeviation] = useState<
    SIDTWDeviation[]
  >([]);
  const [currentDiscreteFrechetDeviation, setCurrentDiscreteFrechetDeviation] =
    useState<DFDDeviation[]>([]);
  const [currentEuclideanDeviation, setCurrentEuclideanDeviation] = useState<
    EADeviation[]
  >([]);

  // Aktualisiere den Hauptzustand wenn sich die initialAuswertungInfo ändert
  useEffect(() => {
    setAuswertungInfo(initialAuswertungInfo);
  }, [initialAuswertungInfo]);

  const contextValue = useMemo(
    () => ({
      auswertungInfo,
      currentSIDTWInfo,
      setCurrentSIDTWInfo,
      currentDiscreteFrechetInfo,
      setCurrentDiscreteFrechetInfo,
      currentEuclideanInfo,
      setCurrentEuclideanInfo,
      currentSIDTWDeviation,
      setCurrentSIDTWDeviation,
      currentDiscreteFrechetDeviation,
      setCurrentDiscreteFrechetDeviation,
      currentEuclideanDeviation,
      setCurrentEuclideanDeviation,
    }),
    [
      auswertungInfo,
      currentSIDTWInfo,
      currentDiscreteFrechetInfo,
      currentEuclideanInfo,
      currentSIDTWDeviation,
      currentDiscreteFrechetDeviation,
      currentEuclideanDeviation,
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
