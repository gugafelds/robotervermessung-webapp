'use client';

import { Loader } from 'lucide-react';
import React from 'react';

import { Position3DPlot } from '@/src/app/motion/components/Position3DPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import { SetpointsInfo } from './SetpointsInfo';
import { TCPAccelPlot } from './TCPAccelPlot';
import { TCPVelPlot } from './TCPVelPlot';

interface PlotAvailability {
  position: boolean;
  orientation: boolean;
  velocity: boolean;
  acceleration: boolean;
  joints: boolean;
}

interface TrajectoryPlotProps {
  plotAvailability: PlotAvailability;
}

export const TrajectoryPlot: React.FC<TrajectoryPlotProps> = ({
  plotAvailability,
}) => {
  const {
    currentTrajPoseAct,
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
          <Typography as="h5">Loading...</Typography>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-fullscreen w-full flex-col overflow-scroll">
      <div className="px-4 pt-4">
        <SetpointsInfo />
      </div>
      <div className="grid h-fullscreen w-full grid-cols-2 place-items-center overflow-scroll py-4">
        {plotAvailability.position && (
          <>
            <Position2DPlot
              currentTrajSetpoints={currentTrajSetpoints}
              idealTrajectory={currentTrajPositionCmd}
              currentTrajPoseAct={currentTrajPoseAct}
            />
            <Position3DPlot
              currentTrajPoseAct={currentTrajPoseAct}
              currentTrajSetpoints={currentTrajSetpoints}
              idealTrajectory={currentTrajPositionCmd}
            />
          </>
        )}

        {plotAvailability.orientation && (
          <OrientationPlot
            currentTrajOrientationCmd={currentTrajOrientationCmd}
            currentTrajPoseAct={currentTrajPoseAct}
            currentTrajSetpoints={currentTrajSetpoints}
          />
        )}

        {plotAvailability.joints && (
          <JointStatesPlot currentTrajJointStates={currentTrajJointStates} />
        )}

        {plotAvailability.velocity && (
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
    </div>
  );
};
