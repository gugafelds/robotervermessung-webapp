'use client';

import { CubeIcon } from '@heroicons/react/20/solid';
import { ChartBarIcon } from '@heroicons/react/24/outline';
import { Loader } from 'lucide-react';
import Link from 'next/link';
import React, { useState } from 'react';

import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

import { ConsistencyCheck } from './ConsistencyCheck';
import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import SlideOver from './SlideOver';
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
  acceleration: boolean; // accel_ist + twist_soll
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
    currentBahnInfo,
    currentBahnPoseIst,
    currentBahnPoseTrans,
    currentBahnTwistIst,
    currentBahnAccelIst,
    currentBahnPositionSoll,
    currentBahnOrientationSoll,
    currentBahnJointStates,
    currentBahnTwistSoll,
    currentBahnEvents,
    currentBahnIMU,
  } = useTrajectory();

  const [isSlideOverOpen, setIsSlideOverOpen] = useState(false);

  const openSlideOver = () => setIsSlideOverOpen(true);
  const closeSlideOver = () => setIsSlideOverOpen(false);

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
    <div className="flex h-fullscreen w-full flex-wrap justify-center overflow-scroll p-4">
      {plotAvailability.position && (
        <>
          <SlideOver
            title="3D-Plot"
            open={isSlideOverOpen}
            onClose={closeSlideOver}
            currentBahnPoseIst={currentBahnPoseIst}
            currentBahnPoseTrans={currentBahnPoseTrans}
            currentBahnEvents={currentBahnEvents}
            idealTrajectory={currentBahnPositionSoll}
            isTransformed={isTransformed}
          />

          <Position2DPlot
            currentBahnEvents={currentBahnEvents}
            idealTrajectory={currentBahnPositionSoll}
            currentBahnPoseIst={currentBahnPoseIst}
            currentBahnPoseTrans={currentBahnPoseTrans}
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

      {plotAvailability.twist && (
        <TCPSpeedPlot
          currentBahnTwistIst={currentBahnTwistIst}
          currentBahnTwistSoll={currentBahnTwistSoll}
        />
      )}

      {plotAvailability.acceleration && (
        <TCPAccelPlot
          currentBahnAccelIst={currentBahnAccelIst}
          currentBahnIMU={currentBahnIMU}
        />
      )}

      {plotAvailability.joints && (
        <JointStatesPlot currentBahnJointStates={currentBahnJointStates} />
      )}

      {plotAvailability.position && (
        // eslint-disable-next-line react/button-has-type
        <button
          onClick={openSlideOver}
          className="fixed right-4 top-28 flex -translate-y-1/2 items-center rounded-lg bg-primary px-4 py-2 font-bold text-white shadow-lg transition duration-300 ease-in-out hover:bg-gray-800"
        >
          <CubeIcon className="mr-2 size-5" />
          3D-Plot
        </button>
      )}

      <div className="fixed right-4 top-40 flex -translate-y-1/2 items-center rounded-lg bg-primary px-4 py-2 font-bold text-white shadow-lg transition duration-300 ease-in-out hover:bg-gray-800">
        {currentBahnInfo && (
          <Link
            href={`/auswertung/${currentBahnInfo.bahnID}`}
            className="flex items-center"
          >
            <ChartBarIcon className="mr-2 size-5" />
            <span>Auswertung</span>
          </Link>
        )}
      </div>

      {hasAnyPlotAvailable && (
        <ConsistencyCheck
          currentBahnTwistIst={currentBahnTwistIst}
          currentBahnTwistSoll={currentBahnTwistSoll}
          currentBahnPoseIst={currentBahnPoseIst}
          idealTrajectory={currentBahnPositionSoll}
          currentBahnEvents={currentBahnEvents}
          currentBahnOrientationSoll={currentBahnOrientationSoll}
          currentBahnAccelIst={currentBahnAccelIst}
          currentBahnJointStates={currentBahnJointStates}
          currentBahnPoseTrans={currentBahnPoseTrans}
          isTransformed={isTransformed}
        />
      )}
    </div>
  );
};
