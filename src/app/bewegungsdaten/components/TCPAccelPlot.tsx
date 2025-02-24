'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnAccelIst, BahnIMU } from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPAccelerationPlotProps {
  currentBahnAccelIst: BahnAccelIst[];
  currentBahnIMU: BahnIMU[];
}

export const TCPAccelPlot: React.FC<TCPAccelerationPlotProps> = ({
  currentBahnAccelIst,
  currentBahnIMU,
}) => {
  const createTcpAccelPlot = () => {
    // Optimierte Berechnung von globalStartTime
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;

      currentBahnAccelIst.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      if (currentBahnIMU.length > 0) {
        currentBahnIMU.forEach((bahn) => {
          minTime = Math.min(minTime, Number(bahn.timestamp));
        });
      }

      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    // Process Ist data
    const timestampsIst = currentBahnAccelIst.map(
      (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
    );

    // Process IMU data only if available
    const hasIMUData = currentBahnIMU.length > 0;
    const timestampsIMU = hasIMUData
      ? currentBahnIMU.map(
          (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
        )
      : [];

    const getMaxTimeAccel = () => {
      let maxTime = Math.max(...timestampsIst);

      if (hasIMUData) {
        maxTime = Math.max(maxTime, ...timestampsIMU);
      }

      return maxTime;
    };

    const maxTimeAccel = getMaxTimeAccel();

    const viconPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      visible: hasIMUData ? 'legendonly' : true, // Nur versteckt wenn IMU-Daten vorhanden
      x: timestampsIst,
      y: currentBahnAccelIst.map((bahn) => Math.abs(bahn.tcpAccelIst)),
      line: {
        color: 'green',
        width: 3,
      },
      name: 'Beschleunigung-Vicon',
    };

    const plotData = [viconPlot];

    // IMU Plot nur hinzufügen wenn Daten vorhanden
    if (hasIMUData) {
      const IMUPlot: Partial<PlotData> = {
        type: 'scatter',
        mode: 'lines',
        x: timestampsIMU,
        y: currentBahnIMU.map((bahn) => Math.abs(bahn.tcpAccelPi)),
        line: {
          color: 'darkred',
          width: 4,
        },
        name: 'Beschleunigung-Sensehat',
      };
      plotData.push(IMUPlot);
    }

    return {
      plotData,
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
