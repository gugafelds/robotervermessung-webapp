'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnAccelIst, BahnAccelSoll } from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TCPAccelerationPlotProps {
  currentBahnAccelIst: BahnAccelIst[];
  currentBahnAccelSoll: BahnAccelSoll[];
}

export const TCPAccelPlot: React.FC<TCPAccelerationPlotProps> = ({
  currentBahnAccelIst,
  currentBahnAccelSoll,
}) => {
  const createTcpAccelPlot = () => {
    // Optimierte Berechnung von globalStartTime
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;

      // Check IST data
      if (currentBahnAccelIst.length > 0) {
        currentBahnAccelIst.forEach((bahn) => {
          minTime = Math.min(minTime, Number(bahn.timestamp));
        });
      }

      // Check SOLL data
      if (currentBahnAccelSoll.length > 0) {
        currentBahnAccelSoll.forEach((bahn) => {
          minTime = Math.min(minTime, Number(bahn.timestamp));
        });
      }

      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    // Process Ist data
    const hasIstData = currentBahnAccelIst.length > 0;
    const timestampsIst = hasIstData
      ? currentBahnAccelIst.map(
          (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
        )
      : [];

    // Process Soll data
    const hasSollData = currentBahnAccelSoll.length > 0;
    const timestampsSoll = hasSollData
      ? currentBahnAccelSoll.map(
          (bahn) => (Number(bahn.timestamp) - globalStartTime) / 1e9,
        )
      : [];

    const getMaxTimeAccel = () => {
      let maxTime = 0;

      if (hasIstData) {
        maxTime = Math.max(maxTime, ...timestampsIst);
      }

      if (hasSollData) {
        maxTime = Math.max(maxTime, ...timestampsSoll);
      }

      return maxTime;
    };

    const maxTimeAccel = getMaxTimeAccel();

    const plotData: Partial<PlotData>[] = [];

    // Add IST data (Vicon)
    if (hasIstData) {
      const viconPlot: Partial<PlotData> = {
        type: 'scatter',
        mode: 'lines',
        visible: true,
        x: timestampsIst,
        y: currentBahnAccelIst.map((bahn) => bahn.tcpAccelIst), // Convert to mm/s²
        line: {
          color: 'green',
          width: 3,
        },
        name: 'Ist-Beschleunigung',
      };
      plotData.push(viconPlot);
    }

    // Add SOLL data
    if (hasSollData) {
      const sollPlot: Partial<PlotData> = {
        type: 'scatter',
        mode: 'lines',
        visible: true,
        x: timestampsSoll,
        y: currentBahnAccelSoll.map((bahn) => bahn.tcpAccelSoll), // Convert to mm/s²
        line: {
          color: 'lightgreen',
          width: 3,
        },
        name: 'Soll-Beschleunigung',
      };
      plotData.push(sollPlot);
    }

    return {
      plotData,
      maxTimeAccel,
    };
  };

  const { plotData: tcpAccelPlotData, maxTimeAccel } = createTcpAccelPlot();

  const tcpAccelLayout: Partial<Layout> = {
    title: 'Beschleunigung',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 'Zeit (s)',
      tickformat: '.2f',
      range: [0, maxTimeAccel],
    },
    yaxis: {
      title: 'mm/s²',
      rangemode: 'tozero',
    },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
    margin: { l: 60, r: 30, t: 50, b: 70 },
    uirevision: 'true',
  };

  return (
    <div className="w-full">
      <Plot
        data={tcpAccelPlotData}
        layout={tcpAccelLayout}
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
