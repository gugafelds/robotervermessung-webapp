'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnAccelIst, BahnTwistSoll } from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPAccelerationPlotProps {
  currentBahnAccelIst: BahnAccelIst[];
  currentBahnTwistSoll: BahnTwistSoll[];
}

export const TCPAccelPlot: React.FC<TCPAccelerationPlotProps> = ({
  currentBahnAccelIst,
  currentBahnTwistSoll,
}) => {
  const createTcpAccelPlot = () => {
    // Optimierte Berechnung von globalStartTime
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;

      currentBahnAccelIst.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      currentBahnTwistSoll.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    // Process Ist data
    const timestampsIst = currentBahnAccelIst.map(
      (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
    );

    // Process Soll data
    const timestampsSoll = currentBahnTwistSoll.map(
      (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
    );

    // Optimierte Berechnung von maxTimeAccel
    const getMaxTimeAccel = () => {
      let maxTime = 0;

      timestampsIst.forEach((time) => {
        maxTime = Math.max(maxTime, time);
      });

      timestampsSoll.forEach((time) => {
        maxTime = Math.max(maxTime, time);
      });

      return maxTime;
    };

    const maxTimeAccel = getMaxTimeAccel();

    const istPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: timestampsIst,
      y: currentBahnAccelIst.map((bahn) => Math.abs(bahn.tcpAccelIst)),
      line: {
        color: 'green',
        width: 3,
      },
      name: 'Beschleunigung-Ist',
    };

    return {
      plotData: [istPlot],
      maxTimeAccel,
    };
  };

  const { plotData: tcpAccelPlotData, maxTimeAccel } = createTcpAccelPlot();

  const tcpAccelLayout: Partial<Layout> = {
    title: 'TCP-Beschleunigung',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.2f',
      range: [0, maxTimeAccel],
    },
    yaxis: { title: 'm/s²' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={tcpAccelPlotData}
        layout={tcpAccelLayout}
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
