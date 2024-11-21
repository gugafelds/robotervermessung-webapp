'use client';

import { CubeIcon } from '@heroicons/react/20/solid';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

import { ConsistencyCheck } from './ConsistencyCheck';
import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import SlideOver from './SlideOver';
import { TCPAccelPlot } from './TCPAccelPlot';
import { TCPSpeedPlot } from './TCPSpeedPlot';

interface TrajectoryPlotProps {
  isTransformed: boolean;
}

export const TrajectoryPlot: React.FC<TrajectoryPlotProps> = ({
  isTransformed,
}) => {
  const {
    bahnInfo,
    currentBahnPoseIst,
    currentBahnPoseTrans,
    currentBahnTwistIst,
    currentBahnAccelIst,
    currentBahnPositionSoll,
    currentBahnOrientationSoll,
    currentBahnJointStates,
    currentBahnTwistSoll,
    currentBahnEvents,
  } = useTrajectory();

  const [isSlideOverOpen, setIsSlideOverOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!bahnInfo || bahnInfo.length === 0) {
      setError('No Bahn info available');
    } else {
      setError(null);
    }
  }, [bahnInfo]);

  const openSlideOver = () => setIsSlideOverOpen(true);
  const closeSlideOver = () => setIsSlideOverOpen(false);

  if (error) {
    return (
      <div className="m-10 size-fit place-items-baseline rounded-2xl bg-gray-300 p-10 shadow-xl">
        <div>
          <ExclamationTriangleIcon className="mx-auto w-16" color="#003560" />
        </div>
        <Typography as="h3">{error}</Typography>
      </div>
    );
  }

  // Check if all required data is available
  const isDataAvailable =
    (isTransformed ? currentBahnPoseTrans : currentBahnPoseIst) &&
    currentBahnTwistIst &&
    currentBahnAccelIst &&
    currentBahnPositionSoll &&
    currentBahnOrientationSoll &&
    currentBahnJointStates &&
    currentBahnTwistSoll &&
    currentBahnEvents;

  if (!isDataAvailable) {
    return (
      <div className="m-10 size-fit place-items-baseline rounded-2xl bg-gray-300 p-10 shadow-xl">
        <div>
          <ExclamationTriangleIcon className="mx-auto w-16" color="#003560" />
        </div>
        <Typography as="h3">Loading data...</Typography>
      </div>
    );
  }

  return (
    <div className="flex h-fullscreen w-full flex-wrap overflow-scroll p-4">
      <SlideOver
        title="3D-Plot"
        open={isSlideOverOpen}
        onClose={closeSlideOver}
        currentBahnPoseIst={currentBahnPoseIst}
        currentBahnPoseTrans={currentBahnPoseTrans}
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

      <OrientationPlot
        currentBahnOrientationSoll={currentBahnOrientationSoll}
        currentBahnPoseIst={currentBahnPoseIst}
        currentBahnPoseTrans={currentBahnPoseTrans}
        isTransformed={isTransformed}
      />

      <TCPSpeedPlot
        currentBahnTwistIst={currentBahnTwistIst}
        currentBahnTwistSoll={currentBahnTwistSoll}
      />

      <TCPAccelPlot
        currentBahnAccelIst={currentBahnAccelIst}
        currentBahnTwistSoll={currentBahnTwistSoll}
      />

      <JointStatesPlot currentBahnJointStates={currentBahnJointStates} />

      {/* eslint-disable-next-line react/button-has-type */}
      <button
        onClick={openSlideOver}
        className="fixed right-4 top-28 flex -translate-y-1/2 items-center rounded-lg bg-primary px-4 py-2 font-bold text-white shadow-lg transition duration-300 ease-in-out hover:bg-gray-800"
      >
        <CubeIcon className="mr-2 size-5" />
        3D-Plot
      </button>

      <ConsistencyCheck
        currentBahnTwistIst={currentBahnTwistIst}
        currentBahnTwistSoll={currentBahnTwistSoll}
        currentBahnPoseIst={currentBahnPoseIst}
        idealTrajectory={currentBahnPositionSoll}
        currentBahnEvents={currentBahnEvents}
        currentBahnOrientationSoll={currentBahnOrientationSoll}
        currentBahnAccelIst={currentBahnAccelIst}
        currentBahnJointStates={currentBahnJointStates}
      />
    </div>
  );
};
