'use client';

import type { ReactNode } from 'react';
import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import type {
  BahnAccelIst,
  BahnEvents,
  BahnInfo,
  BahnJointStates,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPositionSoll,
  BahnTwistIst,
  BahnTwistSoll,
} from '@/types/main';

export interface TrajectoryState {
  bahnInfo: BahnInfo[];
  currentBahnInfo: BahnInfo | null;
  setCurrentBahnInfo: React.Dispatch<React.SetStateAction<BahnInfo | null>>;
  currentBahnPoseIst: BahnPoseIst[];
  setCurrentBahnPoseIst: React.Dispatch<React.SetStateAction<BahnPoseIst[]>>;
  currentBahnTwistIst: BahnTwistIst[];
  setCurrentBahnTwistIst: React.Dispatch<React.SetStateAction<BahnTwistIst[]>>;
  currentBahnAccelIst: BahnAccelIst[];
  setCurrentBahnAccelIst: React.Dispatch<React.SetStateAction<BahnAccelIst[]>>;
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
}

type TrajectoryProviderProps = {
  children: ReactNode;
  initialBahnInfo: BahnInfo[];
};

const TrajectoryContext = createContext<TrajectoryState>({} as TrajectoryState);

export const TrajectoryProvider = ({
  children,
  initialBahnInfo,
}: TrajectoryProviderProps) => {
  const [bahnInfo, setBahnInfo] = useState<BahnInfo[]>(initialBahnInfo);
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

  useEffect(() => {
    setBahnInfo(initialBahnInfo);
  }, [initialBahnInfo]);

  const contextValue = useMemo(
    () => ({
      bahnInfo,
      currentBahnInfo,
      setCurrentBahnInfo,
      currentBahnPoseIst,
      setCurrentBahnPoseIst,
      currentBahnTwistIst,
      setCurrentBahnTwistIst,
      currentBahnAccelIst,
      setCurrentBahnAccelIst,
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
    }),
    [
      bahnInfo,
      currentBahnInfo,
      currentBahnPoseIst,
      currentBahnTwistIst,
      currentBahnAccelIst,
      currentBahnPositionSoll,
      currentBahnOrientationSoll,
      currentBahnTwistSoll,
      currentBahnJointStates,
      currentBahnEvents,
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
