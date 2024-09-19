import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import { dataPlotConfig, plotLayoutConfig } from '@/src/lib/plot-config'; // Adjust import path as needed
import type { BahnPoseIst, BahnPositionSoll } from '@/types/main'; // Adjust import path as needed

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Position3DPlotProps {
  realTrajectory: BahnPoseIst[];
  idealTrajectory: BahnPositionSoll[];
}

export const Position3DPlot: React.FC<Position3DPlotProps> = ({
  realTrajectory,
  idealTrajectory,
}) => {
  const realTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'ist', 6, 'darkblue'),
    x: realTrajectory.map((row) => row.xIst),
    y: realTrajectory.map((row) => row.yIst),
    z: realTrajectory.map((row) => row.zIst),
  };

  const idealTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'soll', 6, 'blue'),
    x: idealTrajectory.map((row) => row.xSoll),
    y: idealTrajectory.map((row) => row.ySoll),
    z: idealTrajectory.map((row) => row.zSoll),
  };

  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    autosize: true,
    margin: { l: 0, r: 0, b: 0, t: 0 },
    scene: {
      aspectmode: 'data',
    },
  };

  return (
    <Plot
      data={[realTrajectoryData, idealTrajectoryData]}
      layout={layout}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
      config={{
        displaylogo: false,
        modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
        responsive: true,
      }}
    />
  );
};
