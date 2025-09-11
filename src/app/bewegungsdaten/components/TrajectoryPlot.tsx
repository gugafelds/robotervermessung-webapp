'use client';

import { Loader } from 'lucide-react';
import React from 'react';

import { Position3DPlot } from '@/src/app/bewegungsdaten/components/Position3DPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import { TCPAccelPlot } from './TCPAccelPlot';
import { TCPSpeedPlot } from './TCPSpeedPlot';

/**
 * Verfügbarkeit der Plots basierend auf geladenen Daten:
 * - position: Benötigt position_soll, pose_ist/trans, events
 * - orientation: Benötigt orientation_soll, pose_ist/trans, events
 * - twist: Benötigt twist_ist, twist_soll
 * - acceleration: Benötigt accel_ist, twist_soll
 * - joints: Benötigt joint_states
 */
interface PlotAvailability {
  position: boolean; // position_soll + pose_ist/trans + events
  orientation: boolean; // orientation_soll + pose_ist/trans + events
  twist: boolean; // twist_ist + twist_soll
  acceleration: boolean; // accel_ist + accel_soll
  joints: boolean; // joint_states
}

interface TrajectoryPlotProps {
  isTransformed: boolean;
  plotAvailability: PlotAvailability;
}

export const TrajectoryPlot: React.FC<TrajectoryPlotProps> = ({
  isTransformed,
  plotAvailability,
}) => {
  const {
    currentBahnPoseIst,
    currentBahnPoseTrans,
    currentBahnTwistIst,
    currentBahnAccelIst,
    currentBahnAccelSoll,
    currentBahnPositionSoll,
    currentBahnOrientationSoll,
    currentBahnJointStates,
    currentBahnTwistSoll,
    currentBahnEvents,
    currentBahnIMU,
  } = useTrajectory();

  const hasAnyPlotAvailable = Object.values(plotAvailability).some(Boolean);

  if (!hasAnyPlotAvailable) {
    return (
      <div className="flex h-fullscreen w-full flex-wrap justify-center overflow-scroll p-4">
        <div className="my-10 flex size-fit flex-col items-center justify-center rounded-xl bg-gray-200 p-2 shadow-sm">
          <div className="animate-spin">
            <Loader className="mx-auto w-10" color="#003560" />
          </div>
          <Typography as="h5">Es lädt...</Typography>
        </div>
      </div>
    );
  }

  return (
    <div className="grid h-fullscreen w-full grid-cols-2 place-items-center overflow-scroll py-4">
      {plotAvailability.position && (
        <>
          <Position2DPlot
            currentBahnEvents={currentBahnEvents}
            idealTrajectory={currentBahnPositionSoll}
            currentBahnPoseIst={currentBahnPoseIst}
            currentBahnPoseTrans={currentBahnPoseTrans}
            isTransformed={isTransformed}
          />
          <Position3DPlot
            currentBahnPoseIst={currentBahnPoseIst}
            currentBahnPoseTrans={currentBahnPoseTrans}
            currentBahnEvents={currentBahnEvents}
            idealTrajectory={currentBahnPositionSoll}
            isTransformed={isTransformed}
          />
        </>
      )}

      {plotAvailability.orientation && (
        <OrientationPlot
          currentBahnOrientationSoll={currentBahnOrientationSoll}
          currentBahnPoseIst={currentBahnPoseIst}
          currentBahnPoseTrans={currentBahnPoseTrans}
          currentBahnEvents={currentBahnEvents}
          isTransformed={isTransformed}
        />
      )}

      {plotAvailability.joints && (
        <JointStatesPlot currentBahnJointStates={currentBahnJointStates} />
      )}

      {plotAvailability.twist && (
        <TCPSpeedPlot
          currentBahnTwistIst={currentBahnTwistIst}
          currentBahnTwistSoll={currentBahnTwistSoll}
        />
      )}

      {plotAvailability.acceleration && (
        <TCPAccelPlot
          currentBahnAccelIst={currentBahnAccelIst}
          currentBahnAccelSoll={currentBahnAccelSoll}
          currentBahnIMU={currentBahnIMU}
        />
      )}
    </div>
  );
};
