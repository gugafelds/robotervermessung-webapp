import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import { dataPlotConfig, plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
} from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Position3DPlotProps {
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  idealTrajectory: BahnPositionSoll[];
  isTransformed: boolean;
}

export const Position3DPlot: React.FC<Position3DPlotProps> = ({
  currentBahnPoseTrans,
  currentBahnPoseIst,
  idealTrajectory,
  isTransformed,
}) => {
  // Überprüfe, ob es sich um transformierte Daten handelt

  const realTrajectory = isTransformed
    ? currentBahnPoseTrans
    : currentBahnPoseIst;

  const realTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'ist', 6, 'darkblue'),
    x: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).xTrans : (row as BahnPoseIst).xIst,
    ),
    y: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).yTrans : (row as BahnPoseIst).yIst,
    ),
    z: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).zTrans : (row as BahnPoseIst).zIst,
    ),
    name: isTransformed ? 'transformiert' : 'ist',
  };

  const idealTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'soll', 6, 'blue'),
    x: idealTrajectory.map((row) => row.xSoll),
    y: idealTrajectory.map((row) => row.ySoll),
    z: idealTrajectory.map((row) => row.zSoll),
    name: 'soll',
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
