'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import dynamic from 'next/dynamic';
import type { PlotData } from 'plotly.js';

import { Typography } from '@/src/components/Typography';
import { dataPlotConfig, plotLayout2DConfig, plotLayoutConfig, heatMapLayoutConfig } from '@/src/lib/plot-config';
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

  const tcpVelocityPlot: Partial<PlotData> = {

          type: 'scatter',
          mode: 'lines',
          x: currentTrajectory.timestampIst,

          y:currentTrajectory.tcpVelocityIst,
          xaxis: "autorange", 
          line: {
            color: 'rgba(100, 100, 100, 0.9)',
            width: 3,
          }};
      

  const dtwAccdistHeatmap: Partial<PlotData> =
    visibleDTWJohnen && currentDtw.dtwAccDist
      ? {
          type: 'heatmap',
          z: currentDtw.dtwAccDist,
          colorscale: 'Plasma',
          showscale: true,
        }
      : {};

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
    <div className="flex h-fullscreen flex-1 flex-col gap-x-2 overflow-scroll">
      <div className="self-center">
      <Plot
          data={[
            tcpVelocityPlot,
          ]}
          useResizeHandler
          layout={plotLayout2DConfig}
          config={{
            displaylogo: false,
            modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
            responsive: true,
          }}
        />
        
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
      </div>
      {visibleDTWJohnen && currentDtw.dtwAccDist && (
        <div className="self-center ">
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
        </div>
      )}
    </div>
  );
};
