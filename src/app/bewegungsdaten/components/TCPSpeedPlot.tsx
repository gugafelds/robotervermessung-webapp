'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnTwistIst, BahnTwistSoll } from '@/types/bewegungsdaten.types';

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
    // Direkte Berechnung statt Funktionsdefinition
    let minTime = Number.MAX_VALUE;
    currentBahnTwistIst.forEach((bahn) => {
      minTime = Math.min(minTime, Number(bahn.timestamp));
    });
    currentBahnTwistSoll.forEach((bahn) => {
      minTime = Math.min(minTime, Number(bahn.timestamp));
    });
    const globalStartTime = minTime;

    // Process Ist data
    const timestampsIst = currentBahnTwistIst.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9;
    });

    // Process Soll data
    const timestampsSoll = currentBahnTwistSoll.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
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
      y: currentBahnTwistIst.map((bahn) => bahn.tcpSpeedIst),
      line: {
        color: 'blue',
        width: 3,
      },
      name: 'Ist-Geschwindigkeit',
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
      name: 'Soll-Geschwindigkeit',
    };

    return {
      plotData: [istPlot, sollPlot],
      maxTimeSpeed,
    };
  };

  const { plotData: tcpSpeedPlotData, maxTimeSpeed } = createTcpSpeedPlot();

  const tcpSpeedLayout: Partial<Layout> = {
    title: 'Geschwindigkeit',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.2f',
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
