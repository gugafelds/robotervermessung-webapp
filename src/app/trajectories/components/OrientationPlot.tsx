'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import { quaternionToEuler } from '@/src/lib/functions';
import type { BahnOrientationSoll, BahnPoseIst } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface OrientationPlotProps {
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnOrientationSoll: BahnOrientationSoll[];
}

export const OrientationPlot: React.FC<OrientationPlotProps> = ({
  currentBahnPoseIst,
  currentBahnOrientationSoll,
}) => {
  const createCombinedEulerAnglePlotData = (): {
    plotData: Partial<PlotData>[];
    maxTimeOrientation: number;
  } => {
    // Find the global start time
    const globalStartTime = Math.min(
      ...currentBahnPoseIst.map((bahn) => Number(bahn.timestamp)),
      ...currentBahnOrientationSoll.map((bahn) => Number(bahn.timestamp)),
    );

    // Process Ist data
    const timestampsIst = currentBahnPoseIst.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });
    const eulerAnglesIst = currentBahnPoseIst.map((bahn) =>
      quaternionToEuler(bahn.qxIst, bahn.qyIst, bahn.qzIst, bahn.qwIst),
    );

    // Process Soll data
    const timestampsSoll = currentBahnOrientationSoll.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });
    const eulerAnglesSoll = currentBahnOrientationSoll.map((bahn) =>
      quaternionToEuler(bahn.qxSoll, bahn.qySoll, bahn.qzSoll, bahn.qwSoll),
    );

    const maxTimeOrientation = Math.max(...timestampsIst, ...timestampsSoll);

    const plotData: Partial<PlotData>[] = [
      // Ist data
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) => angles[0]),
        name: 'Roll (Ist)',
        line: { color: 'red' },
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) => angles[1]),
        name: 'Pitch (Ist)',
        line: { color: 'green' },
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) => angles[2]),
        name: 'Yaw (Ist)',
        line: { color: 'blue' },
      },
      // Soll data
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[0]),
        name: 'Roll (Soll)',
        line: { color: 'pink' },
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[1]),
        name: 'Pitch (Soll)',
        line: { color: 'lightgreen' },
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[2]),
        name: 'Yaw (Soll)',
        line: { color: 'lightblue' },
      },
    ];
    return { plotData, maxTimeOrientation };
  };

  const { plotData: combinedEulerPlotData, maxTimeOrientation } =
    createCombinedEulerAnglePlotData();

  const combinedEulerLayout: Partial<Layout> = {
    title: 'Euler-Winkel',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.2f',
      range: [0, maxTimeOrientation],
    },
    yaxis: { title: '°' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={combinedEulerPlotData}
        layout={combinedEulerLayout}
        useResizeHandler
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
          responsive: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
    </div>
  );
};
