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

const createLinearTimeVector = (timestamps: number[]) => {
  const t1 = 0;
  const t2 = (timestamps[timestamps.length - 1] - timestamps[0]) / 1e9;
  return Array.from(
    { length: timestamps.length },
    (_, i) => t1 + (i * (t2 - t1)) / (timestamps.length - 1),
  );
};

export const TCPAccelPlot: React.FC<TCPAccelerationPlotProps> = ({
  currentBahnAccelIst,
  currentBahnTwistSoll,
}) => {
  const createTcpAccelPlot = () => {
    // Process Ist data
    const timestampsIst = currentBahnAccelIst.map((bahn) =>
      Number(bahn.timestamp),
    );
    const linearTimeIst = createLinearTimeVector(timestampsIst);

    // Process Soll data
    const timestampsSoll = currentBahnTwistSoll.map((bahn) =>
      Number(bahn.timestamp),
    );
    const linearTimeSoll = createLinearTimeVector(timestampsSoll);

    // Extract and smooth Soll speeds (use magnitude)
    const sollSpeeds = currentBahnTwistSoll.map((bahn) =>
      Math.abs(bahn.tcpSpeedSoll),
    );

    // Calculate derived acceleration from Soll speed data
    const [derivativeTimes, derivativeValues] = calculateDerivative(
      linearTimeSoll,
      sollSpeeds,
    );

    // Ensure derivative values are positive (magnitude)
    const derivativeMagnitudes = derivativeValues.map(Math.abs);

    // Calculate maxTime once, considering all relevant timestamps
    const maxTimeAccel = Math.max(...linearTimeIst);

    const istPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: linearTimeIst,
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

  // Usage in your component
  const { plotData: tcpAccelPlotData, maxTimeAccel } = createTcpAccelPlot();

  const tcpAccelLayout: Partial<Layout> = {
    title: 'TCP-Beschleunigung',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.0f',
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
