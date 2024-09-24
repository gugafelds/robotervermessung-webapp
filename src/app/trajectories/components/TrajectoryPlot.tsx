/* eslint-disable react/button-has-type */

'use client';

import { CubeIcon } from '@heroicons/react/20/solid';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';

import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import { ConsistencyCheck } from './ConsistencyCheck';

import { JointStatesPlot } from './JointStatesPlot';
import { OrientationPlot } from './OrientationPlot';
import { Position2DPlot } from './Position2DPlot';
import SlideOver from './SlideOver';
import { TCPAccelPlot } from './TCPAccelPlot';
import { TCPSpeedPlot } from './TCPSpeedPlot';

export const TrajectoryPlot = () => {
  const {
    bahnInfo,
    bahnInfo: [{ bahnID }],
    currentBahnPoseIst,
    currentBahnTwistIst,
    currentBahnAccelIst,
    currentBahnPositionSoll,
    currentBahnOrientationSoll,
    currentBahnJointStates,
    currentBahnTwistSoll,
    currentBahnEvents,
  } = useTrajectory();

  /*
  const euclideanDistancePlot: Partial<PlotData>[] =
    visibleEuclidean && currentEuclidean.euclideanIntersections
      ? currentEuclidean.euclideanIntersections.map(
          (inter: any, index: number) => ({
            ...dataPlotConfig(
              'lines+markers',
              'euc',
              3,
              'rgba(100, 100, 100, 0.9)',
              index === 0,
            ),
            ...inter,
          }),
        )
      : [];

  const dtwJohnenDistancePlot: Partial<PlotData>[] =
    visibleDTWJohnen &&
    currentDTWJohnen.dtwJohnenX &&
    currentDTWJohnen.dtwJohnenY
      ? currentDTWJohnen.dtwJohnenX.map((inter: any, index: number) => ({
          ...dataPlotConfig(
            'lines+markers',
            'dtw',
            3,
            'rgba(210, 105, 30, 0.9)',
            index === 0,
          ),
          x: [inter[0], currentDTWJohnen.dtwJohnenY[index][0]],
          y: [inter[1], currentDTWJohnen.dtwJohnenY[index][1]],
          z: [inter[2], currentDTWJohnen.dtwJohnenY[index][2]],
        }))
      : [];

  const dtwJohnenPathPlot: Partial<PlotData> =
    visibleDTWJohnen && currentDTWJohnen.dtwPath
      ? {
          type: 'scatter',
          mode: 'lines',
          x: currentDTWJohnen.dtwPath[1]
            ? currentDTWJohnen.dtwPath[1]
            : [currentDTWJohnen.dtwPath[1]],
          y: currentDTWJohnen.dtwPath[0]
            ? currentDTWJohnen.dtwPath[0]
            : [currentDTWJohnen.dtwPath[0]],
          line: {
            color: 'rgb(255, 0, 0)',
            width: 4,
          },
        }
      : {};

  const dtwJohnenAccdistHeatmap: Partial<PlotData> =
    visibleDTWJohnen && currentDTWJohnen.dtwAccDist
      ? {
          type: 'heatmap',
          z: currentDTWJohnen.dtwAccDist,
          colorscale: 'Plasma',
          showscale: true,
        }
      : {};

  const euclideanErrorPlot: Partial<PlotData> =
    currentEuclidean.euclideanDistances
      ? {
          type: 'scatter',
          mode: 'lines',
          y: currentEuclidean.euclideanDistances.map(
            (value: number) => value * 1000,
          ),
          line: {
            color: 'rgba(217,26,96, 0.8)',
            width: 1,
          },
        }
      : {};

  const euclideanMaxErrorPlot: Partial<PlotData> =
    currentEuclidean.euclideanDistances
      ? {
          type: 'scatter',
          mode: 'markers',
          x: [
            currentEuclidean.euclideanDistances.indexOf(
              currentEuclidean.euclideanMaxDistance,
            ),
          ],
          y: [currentEuclidean.euclideanMaxDistance * 1000],
          marker: {
            color: 'red',
            size: 6,
          },
        }
      : {};

  const combinedLayoutEuclideanError: Partial<Layout> = {
    ...plotLayout2DConfigEuclideanError,
    shapes: currentEuclidean.euclideanDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentEuclidean.euclideanDistances.length,
            y0: currentEuclidean.euclideanAverageDistance * 1000,
            y1: currentEuclidean.euclideanAverageDistance * 1000,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };

  const dtwJohnenErrorPlot: Partial<PlotData> =
    currentDTWJohnen.dtwJohnenDistances
      ? {
          type: 'scatter',
          mode: 'lines',
          y: currentDTWJohnen.dtwJohnenDistances.map(
            (value: number) => value * 1000,
          ),
          line: {
            color: 'rgba(217,26,96, 0.8)',
            width: 1,
          },
        }
      : {};

  const dtwJohnenMaxErrorPlot: Partial<PlotData> =
    currentDTWJohnen.dtwJohnenDistances
      ? {
          type: 'scatter',
          mode: 'markers',
          x: [
            currentDTWJohnen.dtwJohnenDistances.indexOf(
              currentDTWJohnen.dtwJohnenMaxDistance,
            ),
          ],
          y: [currentDTWJohnen.dtwJohnenMaxDistance * 1000],
          marker: {
            color: 'red',
            size: 6,
          },
        }
      : {};

  const combinedLayoutDTWJohnenError: Partial<Layout> = {
    ...plotLayout2DConfigDTWJohnenError,
    shapes: currentDTWJohnen.dtwJohnenDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentDTWJohnen.dtwJohnenDistances.length,
            y0: currentDTWJohnen.dtwJohnenAverageDistance * 1000,
            y1: currentDTWJohnen.dtwJohnenAverageDistance * 1000,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };

  const dtwErrorPlot: Partial<PlotData> = currentDTW.dtwDistances
    ? {
        type: 'scatter',
        mode: 'lines',
        y: currentDTW.dtwDistances.map((value: number) => value * 1000),
        line: {
          color: 'rgba(217,26,96, 0.8)',
          width: 1,
        },
      }
    : {};

  const dtwMaxErrorPlot: Partial<PlotData> = currentDTW.dtwDistances
    ? {
        type: 'scatter',
        mode: 'markers',
        x: [currentDTW.dtwDistances.indexOf(currentDTW.dtwMaxDistance)],
        y: [currentDTW.dtwMaxDistance * 1000],
        marker: {
          color: 'red',
          size: 6,
        },
      }
    : {};

  const combinedLayoutDTWError: Partial<Layout> = {
    ...plotLayout2DConfigDTWError,
    shapes: currentDTW.dtwDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentDTW.dtwDistances.length,
            y0: currentDTW.dtwAverageDistance * 1000,
            y1: currentDTW.dtwAverageDistance * 1000,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };

  const dfdErrorPlot: Partial<PlotData> = currentDFD.dfdDistances
    ? {
        type: 'scatter',
        mode: 'lines',
        y: currentDFD.dfdDistances.map((value: number) => value * 1000),
        line: {
          color: 'rgba(217,26,96, 0.8)',
          width: 1,
        },
      }
    : {};

  const indexOfMaxDistance =
    currentDFD.dfdDistances && Array.isArray(currentDFD.dfdDistances)
      ? currentDFD.dfdDistances.reduce(
          (
            closestIndex: number,
            currentValue: number,
            currentIndex: number,
            array: any,
          ) => {
            const currentDifference = Math.abs(
              currentValue - currentDFD.dfdMaxDistance,
            );
            const closestDifference = Math.abs(
              array[closestIndex] - currentDFD.dfdMaxDistance,
            );

            return currentDifference < closestDifference
              ? currentIndex
              : closestIndex;
          },
          0,
        )
      : -1;

  const dfdMaxErrorPlot: Partial<PlotData> =
    currentDFD.dfdDistances && indexOfMaxDistance !== -1
      ? {
          type: 'scatter',
          mode: 'markers',
          x: [indexOfMaxDistance],
          y: [currentDFD.dfdMaxDistance * 1000],
          marker: {
            color: 'red',
            size: 6,
          },
        }
      : {};

  const combinedLayoutDFDError: Partial<Layout> = {
    ...plotLayout2DConfigDFDError,
    shapes: currentDFD.dfdDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentDFD.dfdDistances.length,
            y0: currentDFD.dfdAverageDistance * 1000,
            y1: currentDFD.dfdAverageDistance * 1000,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };

  const lcssErrorPlot: Partial<PlotData> = currentLCSS.lcssDistances
    ? {
        type: 'scatter',
        mode: 'lines',
        y: currentLCSS.lcssDistances.map((value: number) => value * 1000),
        line: {
          color: 'rgba(217,26,96, 0.8)',
          width: 1,
        },
      }
    : {};

  const lcssMaxErrorPlot: Partial<PlotData> = currentLCSS.lcssDistances
    ? {
        type: 'scatter',
        mode: 'markers',
        x: [currentLCSS.lcssDistances.indexOf(currentLCSS.lcssMaxDistance)],
        y: [currentLCSS.lcssMaxDistance * 1000],
        marker: {
          color: 'red',
          size: 6,
        },
      }
    : {};

  const combinedLayoutLCSSError: Partial<Layout> = {
    ...plotLayout2DConfigLCSSError,
    shapes: currentLCSS.lcssDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentLCSS.lcssDistances.length,
            y0: currentLCSS.lcssAverageDistance * 1000,
            y1: currentLCSS.lcssAverageDistance * 1000,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };
  */

  const searchedIndex = bahnID;
  const currentTrajectoryID = bahnInfo.findIndex(
    (item) => item.bahnID === searchedIndex,
  );

  if (currentTrajectoryID === -1) {
    return (
      <div className="m-10 size-fit place-items-baseline rounded-2xl bg-gray-300 p-10 shadow-xl">
        <div>
          <ExclamationTriangleIcon className="mx-auto w-16" color="#003560" />
        </div>
        <Typography as="h3">no plot was found</Typography>
      </div>
    );
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [isSlideOverOpen, setIsSlideOverOpen] = useState(false);

  const openSlideOver = () => setIsSlideOverOpen(true);
  const closeSlideOver = () => setIsSlideOverOpen(false);

  return (
    <div className="flex h-fullscreen w-full flex-wrap overflow-scroll p-4">
      <SlideOver
        title="3D-Plot"
        open={isSlideOverOpen}
        onClose={closeSlideOver}
        realTrajectory={currentBahnPoseIst}
        idealTrajectory={currentBahnPositionSoll}
      />

      <Position2DPlot
        currentBahnEvents={currentBahnEvents}
        idealTrajectory={currentBahnPositionSoll}
        currentBahnPoseIst={currentBahnPoseIst}
      />

      <OrientationPlot
        currentBahnOrientationSoll={currentBahnOrientationSoll}
        currentBahnPoseIst={currentBahnPoseIst}
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
