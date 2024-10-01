'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type { BahnEvents, BahnPoseIst, BahnPositionSoll } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Position2DPlotProps {
  idealTrajectory: BahnPositionSoll[];
  currentBahnEvents: BahnEvents[];
  currentBahnPoseIst: BahnPoseIst[];
}

export const Position2DPlot: React.FC<Position2DPlotProps> = ({
  idealTrajectory,
  currentBahnEvents,
  currentBahnPoseIst,
}) => {
  const createCombinedPositionPlot = (): {
    plotData: Partial<PlotData>[];
    maxTimePos: number;
  } => {
    const globalStartTime = Math.min(
      ...idealTrajectory.map((b) => Number(b.timestamp)),
      ...currentBahnEvents.map((b) => Number(b.timestamp)),
      ...currentBahnPoseIst.map((b) => Number(b.timestamp)),
    );

    const positionSollData = idealTrajectory.map((b) => ({
      x: (Number(b.timestamp) - globalStartTime) / 1e9,
      xPos: b.xSoll,
      yPos: b.ySoll,
      zPos: b.zSoll,
    }));

    const positionIstData = currentBahnPoseIst.map((b) => ({
      x: (Number(b.timestamp) - globalStartTime) / 1e9,
      xPos: b.xIst,
      yPos: b.yIst,
      zPos: b.zIst,
    }));

    const createStairStepData = (
      data: { x: number; pos: number }[],
    ): { x: number[]; y: number[] } => {
      const x: number[] = [];
      const y: number[] = [];
      data.forEach((point, index) => {
        if (index > 0) {
          x.push(point.x);
          y.push(y[y.length - 1]);
        }
        x.push(point.x);
        y.push(point.pos);
      });
      return { x, y };
    };

    const xAchievedData = createStairStepData(
      currentBahnEvents.map((b) => ({
        x: (Number(b.timestamp) - globalStartTime) / 1e9,
        pos: b.xReached,
      })),
    );
    const yAchievedData = createStairStepData(
      currentBahnEvents.map((b) => ({
        x: (Number(b.timestamp) - globalStartTime) / 1e9,
        pos: b.yReached,
      })),
    );
    const zAchievedData = createStairStepData(
      currentBahnEvents.map((b) => ({
        x: (Number(b.timestamp) - globalStartTime) / 1e9,
        pos: b.zReached,
      })),
    );

    const maxTimePos = Math.max(
      ...positionSollData.map((d) => d.x),
      ...xAchievedData.x,
      ...positionIstData.map((d) => d.x),
    );

    const plotData: Partial<PlotData>[] = [
      // X Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'X Position Soll',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.xPos),
        line: { color: 'blue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'X Position Ist',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.xPos),
        line: { color: 'darkblue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'X Position Achieved',
        x: xAchievedData.x,
        y: xAchievedData.y,
        line: { color: 'lightblue', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'X Position Achieved',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.xReached),
        marker: { color: 'blue', size: 8, symbol: 'circle' },
      },
      // Y Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Y Position Soll',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.yPos),
        line: { color: 'green', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Y Position Ist',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.yPos),
        line: { color: 'darkgreen', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Y Position Achieved',
        x: yAchievedData.x,
        y: yAchievedData.y,
        line: { color: 'lightgreen', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Y Position Achieved',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.yReached),
        marker: { color: 'green', size: 8, symbol: 'circle' },
      },
      // Z Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Z Position Soll',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.zPos),
        line: { color: 'red', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Z Position Ist',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.zPos),
        line: { color: 'darkred', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Z Position Achieved',
        x: zAchievedData.x,
        y: zAchievedData.y,
        line: { color: 'pink', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Z Position Achieved',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.zReached),
        marker: { color: 'red', size: 8, symbol: 'circle' },
      },
    ];

    return { plotData, maxTimePos };
  };

  const { plotData: combinedPositionPlotData, maxTimePos: positionMaxTime } =
    createCombinedPositionPlot();

  const combinedPositionLayout: Partial<Layout> = {
    title: 'Position',
    font: {
      family: 'Helvetica',
    },
    xaxis: { title: 's', range: [0, positionMaxTime], tickformat: '.2f' },
    yaxis: { title: 'mm' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={combinedPositionPlotData}
        layout={combinedPositionLayout}
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
