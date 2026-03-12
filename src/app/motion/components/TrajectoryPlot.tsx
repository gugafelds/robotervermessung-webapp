'use client';

import { Loader } from 'lucide-react';
import React from 'react';

import { Position3DPlot } from '@/src/app/motion/components/Position3DPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import { TCPAccelPlot } from './TCPAccelPlot';
import { TCPVelPlot } from './TCPVelPlot';

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
    currentTrajPoseAct,
    currentTrajPoseTrans,
    currentTrajVelAct,
    currentTrajAccelAct,
    currentTrajAccelCmd,
    currentTrajPositionCmd,
    currentTrajOrientationCmd,
    currentTrajJointStates,
    currentTrajVelCmd,
    currentTrajSetpoints,
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
            currentTrajSetpoints={currentTrajSetpoints}
            idealTrajectory={currentTrajPositionCmd}
            currentTrajPoseAct={currentTrajPoseAct}
            currentTrajPoseTrans={currentTrajPoseTrans}
            isTransformed={isTransformed}
          />
          <Position3DPlot
            currentTrajPoseAct={currentTrajPoseAct}
            currentTrajPoseTrans={currentTrajPoseTrans}
            currentTrajSetpoints={currentTrajSetpoints}
            idealTrajectory={currentTrajPositionCmd}
            isTransformed={isTransformed}
          />
        </>
      )}

      {plotAvailability.orientation && (
        <OrientationPlot
          currentTrajOrientationCmd={currentTrajOrientationCmd}
          currentTrajPoseAct={currentTrajPoseAct}
          currentTrajPoseTrans={currentTrajPoseTrans}
          currentTrajSetpoints={currentTrajSetpoints}
          isTransformed={isTransformed}
        />
      )}

      {plotAvailability.joints && (
        <JointStatesPlot currentTrajJointStates={currentTrajJointStates} />
      )}

      {plotAvailability.twist && (
        <TCPVelPlot
          currentTrajVelAct={currentTrajVelAct}
          currentTrajVelCmd={currentTrajVelCmd}
        />
      )}

      {plotAvailability.acceleration && (
        <TCPAccelPlot
          currentTrajAccelAct={currentTrajAccelAct}
          currentTrajAccelCmd={currentTrajAccelCmd}
        />
      )}
    </div>
  );
};
