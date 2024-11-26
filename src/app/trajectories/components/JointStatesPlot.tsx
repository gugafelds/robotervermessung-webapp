'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnJointStates } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface JointStatesPlotProps {
  currentBahnJointStates: BahnJointStates[];
}

export const JointStatesPlot: React.FC<JointStatesPlotProps> = ({
  currentBahnJointStates,
}) => {
  const createJointStatesPlot = (): {
    plotData: Partial<PlotData>[];
    maxTimeJoints: number;
  } => {
    // Optimierte Berechnung von globalStartTime
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;
      currentBahnJointStates.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });
      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    // Process data
    const timestamps = currentBahnJointStates.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });

    // Optimierte Berechnung von maxTimeJoints
    const getMaxTimeJoints = () => {
      let maxTime = 0;
      timestamps.forEach((time) => {
        maxTime = Math.max(maxTime, time);
      });
      return maxTime;
    };

    const maxTimeJoints = getMaxTimeJoints();

    const plotData: Partial<PlotData>[] = [
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint1),
        line: { color: 'red', width: 3 },
        name: 'Joint 1',
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint2),
        line: { color: 'blue', width: 3 },
        name: 'Joint 2',
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint3),
        line: { color: 'green', width: 3 },
        name: 'Joint 3',
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint4),
        line: { color: 'purple', width: 3 },
        name: 'Joint 4',
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint5),
        line: { color: 'orange', width: 3 },
        name: 'Joint 5',
      },
      {
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: currentBahnJointStates.map((bahn) => bahn.joint6),
        line: { color: 'brown', width: 3 },
        name: 'Joint 6',
      },
    ];

    return {
      plotData,
      maxTimeJoints,
    };
  };

  const { plotData: jointStatesPlotData, maxTimeJoints } =
    createJointStatesPlot();

  const jointStatesLayout: Partial<Layout> = {
    title: 'Joint States',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.2f',
      range: [0, maxTimeJoints],
    },
    yaxis: { title: '°' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={jointStatesPlotData}
        layout={jointStatesLayout}
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
