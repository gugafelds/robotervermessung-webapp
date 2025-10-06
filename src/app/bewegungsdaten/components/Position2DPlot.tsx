'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import type {
  BahnEvents,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
} from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Position2DPlotProps {
  idealTrajectory: BahnPositionSoll[];
  currentBahnEvents: BahnEvents[];
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  isTransformed: boolean;
}

export const Position2DPlot: React.FC<Position2DPlotProps> = ({
  idealTrajectory,
  currentBahnEvents,
  currentBahnPoseIst,
  currentBahnPoseTrans,
  isTransformed,
}) => {
  const createCombinedPositionPlot = (): {
    plotData: Partial<PlotData>[];
    maxTimePos: number;
  } => {
    const currentPoseData = isTransformed
      ? currentBahnPoseTrans
      : currentBahnPoseIst;

    // Neue optimierte Berechnung von globalStartTime
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;

      idealTrajectory.forEach((b) => {
        minTime = Math.min(minTime, Number(b.timestamp));
      });

      currentBahnEvents.forEach((b) => {
        minTime = Math.min(minTime, Number(b.timestamp));
      });

      currentPoseData.forEach((b) => {
        minTime = Math.min(minTime, Number(b.timestamp));
      });

      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    const positionSollData = idealTrajectory.map((b) => ({
      x: (Number(b.timestamp) - globalStartTime) / 1e9,
      xPos: b.xSoll,
      yPos: b.ySoll,
      zPos: b.zSoll,
    }));

    const positionIstData = currentPoseData.map((b) => {
      const x = (Number(b.timestamp) - globalStartTime) / 1e9;
      if (isTransformed) {
        const transPose = b as BahnPoseTrans;
        return {
          x,
          xPos: transPose.xTrans,
          yPos: transPose.yTrans,
          zPos: transPose.zTrans,
        };
      }
      const istPose = b as BahnPoseIst;
      return {
        x,
        xPos: istPose.xIst,
        yPos: istPose.yIst,
        zPos: istPose.zIst,
      };
    });

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

    const getMaxTimePos = () => {
      let maxTime = 0;

      positionSollData.forEach((d) => {
        maxTime = Math.max(maxTime, d.x);
      });

      xAchievedData.x.forEach((x) => {
        maxTime = Math.max(maxTime, x);
      });

      positionIstData.forEach((d) => {
        maxTime = Math.max(maxTime, d.x);
      });

      return maxTime;
    };

    const maxTimePos = getMaxTimePos();

    const plotData: Partial<PlotData>[] = [
      // X Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'X-Sollposition',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.xPos),
        line: { color: 'red', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'X-Istposition',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.xPos),
        line: { color: 'darkred', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'X-Zielpunkte',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.xReached),
        marker: { color: 'red', size: 12, symbol: 'circle' },
      },
      // Y Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Y-Sollposition',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.yPos),
        line: { color: 'green', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Y-Istposition',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.yPos),
        line: { color: 'darkgreen', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Y-Zielpunkte',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.yReached),
        marker: { color: 'green', size: 12, symbol: 'circle' },
      },
      // Z Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Z-Sollposition',
        x: positionSollData.map((d) => d.x),
        y: positionSollData.map((d) => d.zPos),
        line: { color: 'blue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Z-Istposition',
        x: positionIstData.map((d) => d.x),
        y: positionIstData.map((d) => d.zPos),
        line: { color: 'darkblue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Z-Zielpunkte',
        x: currentBahnEvents.map(
          (b) => (Number(b.timestamp) - globalStartTime) / 1e9,
        ),
        y: currentBahnEvents.map((b) => b.zReached),
        marker: { color: 'blue', size: 12, symbol: 'circle' },
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
    legend: { orientation: 'h', y: -0.15 }, // Legende näher zum Plot
    hovermode: 'x unified',
    margin: { l: 60, r: 20, b: 80, t: 50 }, // Kleinere Margins = mehr Platz für Plot
    uirevision: 'true',
  };

  return (
    <div className="w-full">
      <Plot
        data={combinedPositionPlotData}
        layout={combinedPositionLayout}
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
            'select2d',
          ],
          responsive: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
    </div>
  );
};
