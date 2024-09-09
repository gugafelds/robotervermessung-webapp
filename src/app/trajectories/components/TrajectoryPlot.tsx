'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';

import { Typography } from '@/src/components/Typography';
import {
  dataPlotConfig,
  heatMapLayoutConfig,
  plotLayout2DConfigAcceleration,
  plotLayout2DConfigDFDError,
  plotLayout2DConfigDTWError,
  plotLayout2DConfigDTWJohnenError,
  plotLayout2DConfigEuclideanError,
  plotLayout2DConfigLCSSError,
  plotLayout2DConfigVelocity,
  plotLayoutConfig,
} from '@/src/lib/plot-config';
import { useTrajectory } from '@/src/providers/trajectory.provider';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export const TrajectoryPlot = () => {
  const {
    trajectoriesHeader,
    currentTrajectory,
    currentEuclidean,
    currentDTW,
    currentDFD,
    currentDTWJohnen,
    currentLCSS,
    visibleEuclidean,
    visibleDTWJohnen,
  } = useTrajectory();

  const realTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'ist', 6, 'rgb(217,26,96)'),
    x: currentTrajectory.xIst,
    y: currentTrajectory.yIst,
    z: currentTrajectory.zIst,
  };

  /* const xIstTrajectory: Partial<PlotData> = currentTrajectory.timestampIst
    ? {
        type: 'scatter',
        mode: 'lines',
        x: currentTrajectory.timestampIst.lenght,
        y: currentTrajectory.xIst,
        line: {
          color: 'rgb(255, 0, 0)',
          width: 4,
        },
      }
    : {};

  const xSollTrajectory: Partial<PlotData> = currentTrajectory.timestampSoll
    ? {
        type: 'scatter',
        mode: 'lines',
        x: currentTrajectory.timestampSoll.lenght,
        y: currentTrajectory.xSoll,
        line: {
          color: 'rgb(255, 0, 0)',
          width: 4,
        },
      }
    : {};
  
    */

  const idealTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'soll', 6),
    x: currentTrajectory.xSoll,
    y: currentTrajectory.ySoll,
    z: currentTrajectory.zSoll,
  };

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

  const tcpVelocityPlot: Partial<PlotData> = currentTrajectory.tcpVelocityIst
    ? {
        type: 'scatter',
        mode: 'lines',
        x: currentTrajectory.timestampIst,
        y: currentTrajectory.tcpVelocityIst,
        line: {
          color: 'rgba(217,26,96, 0.8)',
          width: 3,
        },
      }
    : {};

  const combinedLayoutVelocity: Partial<Layout> = {
    ...plotLayout2DConfigVelocity,
    shapes:
      currentTrajectory.tcpVelocityIst && currentTrajectory.tcpVelocitySoll
        ? [
            {
              type: 'line',
              x0: currentTrajectory.timestampIst
                ? currentTrajectory.timestampIst[0]
                : 0,
              x1: currentTrajectory.timestampIst
                ? currentTrajectory.timestampIst[
                    currentTrajectory.timestampIst.length - 1
                  ]
                : 1,
              y0: currentTrajectory.tcpVelocitySoll,
              y1: currentTrajectory.tcpVelocitySoll,
              line: {
                color: 'rgba(31,119,180, 0.7)',
                width: 2,
                dash: 'dash',
              },
            },
          ]
        : [],
    annotations: !currentTrajectory.tcpVelocityIst
      ? [
          {
            xref: 'paper',
            yref: 'paper',
            x: 0.5,
            y: 0.5,
            text: 'keine Daten :(',
            showarrow: false,
            font: {
              size: 15,
              color: 'black',
            },
            align: 'center',
          },
        ]
      : [],
  };

  const tcpAccelerationPlot: Partial<PlotData> =
    currentTrajectory.tcpAcceleration
      ? {
          type: 'scatter',
          mode: 'lines',
          x: currentTrajectory.timestampIst,
          y: currentTrajectory.tcpAcceleration,
          line: {
            color: 'rgba(217,26,96, 0.8)',
            width: 3,
          },
        }
      : {};

  const combinedLayoutAcceleration: Partial<Layout> = {
    ...plotLayout2DConfigAcceleration,
    annotations: !currentTrajectory.tcpAcceleration
      ? [
          {
            xref: 'paper',
            yref: 'paper',
            x: 0.5,
            y: 0.5,
            text: 'keine Daten :(',
            showarrow: false,
            font: {
              size: 15,
              color: 'black',
            },
            align: 'center',
          },
        ]
      : [],
  };

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

  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
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

  return (
    <div className="h-fullscreen flex-row overflow-scroll">
      <div className="m-4 flex-row">
        <Plot
          data={[
            idealTrajectory,
            realTrajectory,
            ...euclideanDistancePlot,
            ...dtwJohnenDistancePlot,
          ]}
          useResizeHandler
          layout={plotLayoutConfig}
          config={{
            displaylogo: false,
            modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
            responsive: true,
          }}
        />

        {visibleDTWJohnen && currentDTWJohnen.dtwAccDist && (
          <Plot
            data={[dtwJohnenAccdistHeatmap, dtwJohnenPathPlot]}
            useResizeHandler
            layout={heatMapLayoutConfig}
            config={{
              displaylogo: false,
              modeBarButtonsToRemove: ['toImage', 'orbitRotation', 'pan2d'],
              responsive: true,
            }}
          />
        )}

        <div className="m-4 flex-row">
          <Plot
            className=""
            data={[tcpVelocityPlot]}
            useResizeHandler
            layout={combinedLayoutVelocity}
            config={{
              displaylogo: false,
              modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
              responsive: true,
            }}
          />

          <Plot
            data={[tcpAccelerationPlot]}
            useResizeHandler
            layout={combinedLayoutAcceleration}
            config={{
              displaylogo: false,
              modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
              responsive: true,
            }}
          />
        </div>

        <div className="m-4 flex-row">
          {currentEuclidean.euclideanDistances && (
            <Plot
              className=""
              data={[euclideanErrorPlot, euclideanMaxErrorPlot]}
              useResizeHandler
              layout={combinedLayoutEuclideanError}
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
                responsive: true,
              }}
            />
          )}

          {currentDTW.dtwDistances && (
            <Plot
              className=""
              data={[dtwErrorPlot, dtwMaxErrorPlot]}
              useResizeHandler
              layout={combinedLayoutDTWError}
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
                responsive: true,
              }}
            />
          )}

          {currentDTWJohnen.dtwJohnenDistances && (
            <Plot
              className=""
              data={[dtwJohnenErrorPlot, dtwJohnenMaxErrorPlot]}
              useResizeHandler
              layout={combinedLayoutDTWJohnenError}
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
                responsive: true,
              }}
            />
          )}

          {currentDFD.dfdDistances && (
            <Plot
              className=""
              data={[dfdErrorPlot, dfdMaxErrorPlot]}
              useResizeHandler
              layout={combinedLayoutDFDError}
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
                responsive: true,
              }}
            />
          )}

          {currentDFD.dfdDistances && (
            <Plot
              className=""
              data={[lcssErrorPlot, lcssMaxErrorPlot]}
              useResizeHandler
              layout={combinedLayoutLCSSError}
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
                responsive: true,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
};
