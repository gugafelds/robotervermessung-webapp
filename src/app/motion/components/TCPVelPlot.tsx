'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { TrajVelAct, TrajVelCmd } from '@/types/motion.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPSpeedPlotProps {
  currentTrajVelAct: TrajVelAct[];
  currentTrajVelCmd: TrajVelCmd[];
}

export const TCPVelPlot: React.FC<TCPSpeedPlotProps> = ({
  currentTrajVelAct,
  currentTrajVelCmd,
}) => {
  const createTcpSpeedPlot = (): {
    plotData: Partial<PlotData>[];
    maxTimeSpeed: number;
  } => {
    // Direkte Berechnung statt Funktionsdefinition
    let minTime = Number.MAX_VALUE;
    currentTrajVelAct.forEach((traj) => {
      minTime = Math.min(minTime, Number(traj.timestamp));
    });
    currentTrajVelCmd.forEach((traj) => {
      minTime = Math.min(minTime, Number(traj.timestamp));
    });
    const globalStartTime = minTime;

    // Process Ist data
    const timestampsIst = currentTrajVelAct.map((traj) => {
      const elapsedNanoseconds = Number(traj.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9;
    });

    // Process Soll data
    const timestampsSoll = currentTrajVelCmd.map((traj) => {
      const elapsedNanoseconds = Number(traj.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9;
    });

    // Direkte Berechnung von maxTimeSpeed
    let maxTime = 0;
    timestampsIst.forEach((time) => {
      maxTime = Math.max(maxTime, time);
    });
    timestampsSoll.forEach((time) => {
      maxTime = Math.max(maxTime, time);
    });
    const maxTimeSpeed = maxTime;

    const istPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: timestampsIst,
      y: currentTrajVelAct.map((traj) => traj.tcpSpeedAct),
      line: {
        color: 'blue',
        width: 3,
      },
      name: 'Measured',
    };

    const sollPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: timestampsSoll,
      y: currentTrajVelCmd.map((traj) => traj.tcpSpeedCmd),
      line: {
        color: 'lightblue',
        width: 3,
      },
      name: 'Commanded',
    };

    return {
      plotData: [istPlot, sollPlot],
      maxTimeSpeed,
    };
  };

  const { plotData: tcpSpeedPlotData, maxTimeSpeed } = createTcpSpeedPlot();

  const tcpSpeedLayout: Partial<Layout> = {
    title: { text: 'Velocity' },
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: { text: 's' },
      tickformat: '.2f',
      range: [0, maxTimeSpeed],
    },
    yaxis: { title: { text: 'mm/s' } },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
    uirevision: 'true',
  };

  return (
    <div className="w-full">
      <Plot
        data={tcpSpeedPlotData}
        layout={tcpSpeedLayout}
        useResizeHandler
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'lasso2d',
            'zoomIn2d',
            'zoomOut2d',
            'autoScale2d',
            'pan2d',
          ],
          responsive: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
    </div>
  );
};
