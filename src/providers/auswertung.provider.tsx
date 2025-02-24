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
  DFDInfo,
  DFDPosition,
  DTWInfo,
  DTWPosition,
  EAInfo,
  EAPosition,
  SIDTWInfo,
  SIDTWPosition,
} from '@/types/auswertung.types';

export interface AuswertungState {
  auswertungInfo: AuswertungInfo;
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
  const [currentDTWInfo, setCurrentDTWInfo] = useState<DTWInfo[]>([]);
  const [currentDiscreteFrechetInfo, setCurrentDiscreteFrechetInfo] = useState<
    DFDInfo[]
  >([]);
  const [currentEuclideanInfo, setCurrentEuclideanInfo] = useState<EAInfo[]>(
    [],
  );

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

  // Aktualisiere den Hauptzustand wenn sich die initialAuswertungInfo ändert
  useEffect(() => {
    setAuswertungInfo(initialAuswertungInfo);
  }, [initialAuswertungInfo]);

  const contextValue = useMemo(
    () => ({
      auswertungInfo,
      currentSIDTWInfo,
      setCurrentSIDTWInfo,
      currentDTWInfo,
      setCurrentDTWInfo,
      currentDiscreteFrechetInfo,
      setCurrentDiscreteFrechetInfo,
      currentEuclideanInfo,
      setCurrentEuclideanInfo,
      currentSIDTWDeviation,
      setCurrentSIDTWDeviation,
      currentDTWDeviation,
      setCurrentDTWDeviation,
      currentDiscreteFrechetDeviation,
      setCurrentDiscreteFrechetDeviation,
      currentEuclideanDeviation,
      setCurrentEuclideanDeviation,
    }),
    [
      auswertungInfo,
      currentSIDTWInfo,
      currentDTWInfo,
      currentDiscreteFrechetInfo,
      currentEuclideanInfo,
      currentSIDTWDeviation,
      currentDTWDeviation,
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
