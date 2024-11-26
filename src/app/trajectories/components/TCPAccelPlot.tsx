'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnAccelIst, BahnTwistSoll } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPAccelerationPlotProps {
  currentBahnAccelIst: BahnAccelIst[];
  currentBahnTwistSoll: BahnTwistSoll[];
}

const calculateDerivative = (times: number[], values: number[]) => {
  const derivative = [];
  const derivativeTimes = times.slice(1);
  // eslint-disable-next-line no-plusplus
  for (let i = 1; i < times.length; i++) {
    const dt = times[i] - times[i - 1];
    const dv = values[i] - values[i - 1];
    derivative.push(dv / dt);
  }
  return [derivativeTimes, derivative] as const;
};

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

    // Extract and smooth Soll speeds (use magnitude)
    const sollSpeeds = currentBahnTwistSoll.map((bahn) =>
      Math.abs(bahn.tcpSpeedSoll),
    );

    // Calculate derived acceleration from Soll speed data
    const [derivativeTimes, derivativeValues] = calculateDerivative(
      timestampsSoll,
      sollSpeeds,
    );

    // Ensure derivative values are positive (magnitude)
    const derivativeMagnitudes = derivativeValues.map(Math.abs);

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

    const sollPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: derivativeTimes,
      y: derivativeMagnitudes.map((value: number) => value / 1000),
      line: {
        color: 'lightgreen',
        width: 3,
      },
      name: 'Abgeleitet-Soll',
    };

    return {
      plotData: [istPlot, sollPlot],
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
