'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';

import { Typography } from '@/src/components/Typography';
import {
  dataPlotConfig,
  heatMapLayoutConfig,
  plotLayout2DConfigAcceleration,
  plotLayout2DConfigDTWJohnenError,
  plotLayout2DConfigEuclideanError,
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
    currentDtw,
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

  const dtwDistancePlot: Partial<PlotData>[] =
    visibleDTWJohnen && currentDtw.dtwJohnenX && currentDtw.dtwJohnenY
      ? currentDtw.dtwJohnenX.map((inter: any, index: number) => ({
          ...dataPlotConfig(
            'lines+markers',
            'dtw',
            3,
            'rgba(210, 105, 30, 0.9)',
            index === 0,
          ),
          x: [inter[0], currentDtw.dtwJohnenY[index][0]],
          y: [inter[1], currentDtw.dtwJohnenY[index][1]],
          z: [inter[2], currentDtw.dtwJohnenY[index][2]],
        }))
      : [];

  const dtwPathPlot: Partial<PlotData> =
    visibleDTWJohnen && currentDtw.dtwPath
      ? {
          type: 'scatter',
          mode: 'lines',
          x: Array.isArray(currentDtw.dtwPath[1])
            ? currentDtw.dtwPath[1]
            : [currentDtw.dtwPath[1]],
          y: Array.isArray(currentDtw.dtwPath[0])
            ? currentDtw.dtwPath[0]
            : [currentDtw.dtwPath[0]],
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

  const dtwAccdistHeatmap: Partial<PlotData> =
    visibleDTWJohnen && currentDtw.dtwAccDist
      ? {
          type: 'heatmap',
          z: currentDtw.dtwAccDist,
          colorscale: 'Plasma',
          showscale: true,
        }
      : {};

  const euclideanErrorPlot: Partial<PlotData> =
    currentEuclidean.euclideanDistances
      ? {
          type: 'scatter',
          mode: 'lines',
          y: currentEuclidean.euclideanDistances,
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
          y: [currentEuclidean.euclideanMaxDistance],
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
            y0: currentEuclidean.euclideanAverageDistance,
            y1: currentEuclidean.euclideanAverageDistance,
            line: {
              color: 'rgba(31,119,180, 0.8)',
              width: 2,
              dash: 'dash',
            },
          },
        ]
      : [],
  };

  const dtwJohnenErrorPlot: Partial<PlotData> = currentDtw.dtwJohnenDistances
    ? {
        type: 'scatter',
        mode: 'lines',
        y: currentDtw.dtwJohnenDistances,
        line: {
          color: 'rgba(217,26,96, 0.8)',
          width: 1,
        },
      }
    : {};

  const dtwJohnenMaxErrorPlot: Partial<PlotData> = currentDtw.dtwJohnenDistances
    ? {
        type: 'scatter',
        mode: 'markers',
        x: [
          currentDtw.dtwJohnenDistances.indexOf(
            currentDtw.dtwJohnenMaxDistance,
          ),
        ],
        y: [currentDtw.dtwJohnenMaxDistance],
        marker: {
          color: 'red',
          size: 6,
        },
      }
    : {};

  const combinedLayoutDTWJohnenError: Partial<Layout> = {
    ...plotLayout2DConfigDTWJohnenError,
    shapes: currentDtw.dtwJohnenDistances
      ? [
          {
            type: 'line',
            x0: 0,
            x1: currentDtw.dtwJohnenDistances.length,
            y0: currentDtw.dtwJohnenAverageDistance,
            y1: currentDtw.dtwJohnenAverageDistance,
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
        <Plot
          data={[
            idealTrajectory,
            realTrajectory,
            ...euclideanDistancePlot,
            ...dtwDistancePlot,
          ]}
          useResizeHandler
          layout={plotLayoutConfig}
          config={{
            displaylogo: false,
            modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
            responsive: true,
          }}
        />

        {visibleDTWJohnen && currentDtw.dtwAccDist && (
          <Plot
            data={[dtwAccdistHeatmap, dtwPathPlot]}
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

          {currentDtw.dtwJohnenDistances && (
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
        </div>
      </div>
    </div>
  );
};
