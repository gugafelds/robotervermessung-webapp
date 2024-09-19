'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnTwistIst, BahnTwistSoll } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPSpeedPlotProps {
  currentBahnTwistIst: BahnTwistIst[];
  currentBahnTwistSoll: BahnTwistSoll[];
}

export const TCPSpeedPlot: React.FC<TCPSpeedPlotProps> = ({
  currentBahnTwistIst,
  currentBahnTwistSoll,
}) => {
  const createTcpSpeedPlot = (): {
    plotData: Partial<PlotData>[];
    maxTimeSpeed: number;
  } => {
    // Process Ist data
    const startTimeIst = Math.min(
      ...currentBahnTwistIst.map((bahn) => Number(bahn.timestamp)),
    );
    const timestampsIst = currentBahnTwistIst.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - startTimeIst;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });

    // Process Soll data
    const startTimeSoll = Math.min(
      ...currentBahnTwistSoll.map((bahn) => Number(bahn.timestamp)),
    );
    const timestampsSoll = currentBahnTwistSoll.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - startTimeSoll;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });

    const maxTimeSpeed = Math.max(...timestampsIst, ...timestampsSoll);

    const istPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: timestampsIst,
      y: currentBahnTwistIst.map((bahn) => bahn.tcpSpeedIst),
      line: {
        color: 'blue',
        width: 3,
      },
      name: 'TCP-Geschwindigkeit (Ist)',
    };

    const sollPlot: Partial<PlotData> = {
      type: 'scatter',
      mode: 'lines',
      x: timestampsSoll,
      y: currentBahnTwistSoll.map((bahn) => bahn.tcpSpeedSoll),
      line: {
        color: 'lightblue',
        width: 3,
      },
      name: 'TCP-Geschwindigkeit (Soll)',
    };

    return {
      plotData: [istPlot, sollPlot],
      maxTimeSpeed,
    };
  };

  const { plotData: tcpSpeedPlotData, maxTimeSpeed } = createTcpSpeedPlot();

  const tcpSpeedLayout: Partial<Layout> = {
    title: 'TCP-Geschwindigkeit',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.0f',
      range: [0, maxTimeSpeed],
    },
    yaxis: { title: 'mm/s' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={tcpSpeedPlotData}
        layout={tcpSpeedLayout}
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
