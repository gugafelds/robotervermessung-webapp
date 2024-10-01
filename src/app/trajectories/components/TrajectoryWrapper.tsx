"use client";

import React, { useEffect } from "react";

import { TrajectoryInfo } from "@/src/app/trajectories/components/TrajectoryInfo";
import { TrajectoryPlot } from "@/src/app/trajectories/components/TrajectoryPlot";
import { useTrajectory } from "@/src/providers/trajectory.provider";
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
} from "@/types/main";

type TrajectoryPageProps = {
  currentBahnInfo: BahnInfo;
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnTwistIst: BahnTwistIst[];
  currentBahnAccelIst: BahnAccelIst[];
  currentBahnPositionSoll: BahnPositionSoll[];
  currentBahnOrientationSoll: BahnOrientationSoll[];
  currentBahnTwistSoll: BahnTwistSoll[];
  currentBahnJointStates: BahnJointStates[];
  currentBahnEvents: BahnEvents[];
};

export function TrajectoryWrapper({
  currentBahnInfo,
  currentBahnPoseIst,
  currentBahnTwistIst,
  currentBahnAccelIst,
  currentBahnPositionSoll,
  currentBahnOrientationSoll,
  currentBahnTwistSoll,
  currentBahnJointStates,
  currentBahnEvents,
}: TrajectoryPageProps) {
  const {
    setCurrentBahnInfo,
    setCurrentBahnPoseIst,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
  } = useTrajectory();

  useEffect(() => {
    setCurrentBahnInfo(currentBahnInfo);
    setCurrentBahnPoseIst(currentBahnPoseIst);
    setCurrentBahnTwistIst(currentBahnTwistIst);
    setCurrentBahnAccelIst(currentBahnAccelIst);
    setCurrentBahnPositionSoll(currentBahnPositionSoll);
    setCurrentBahnOrientationSoll(currentBahnOrientationSoll);
    setCurrentBahnTwistSoll(currentBahnTwistSoll);
    setCurrentBahnJointStates(currentBahnJointStates);
    setCurrentBahnEvents(currentBahnEvents);
  }, [
    currentBahnInfo,
    currentBahnAccelIst,
    currentBahnOrientationSoll,
    currentBahnPoseIst,
    currentBahnPositionSoll,
    currentBahnTwistIst,
    currentBahnTwistSoll,
    currentBahnJointStates,
    currentBahnEvents,
    setCurrentBahnInfo,
    setCurrentBahnAccelIst,
    setCurrentBahnOrientationSoll,
    setCurrentBahnPoseIst,
    setCurrentBahnPositionSoll,
    setCurrentBahnTwistIst,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
  ]);

  return (
    <>
      <TrajectoryInfo />
      <TrajectoryPlot />
    </>
  );
}
