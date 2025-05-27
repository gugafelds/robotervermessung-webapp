import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import { dataPlotConfig, plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  BahnEvents,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
} from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Position3DPlotProps {
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  idealTrajectory: BahnPositionSoll[];
  currentBahnEvents: BahnEvents[];
  isTransformed: boolean;
}

export const Position3DPlot: React.FC<Position3DPlotProps> = ({
  currentBahnPoseTrans,
  currentBahnPoseIst,
  idealTrajectory,
  currentBahnEvents,
  isTransformed,
}) => {
  const realTrajectory = isTransformed
    ? currentBahnPoseTrans
    : currentBahnPoseIst;

  const realTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'ist', 4, 'darkblue'),
    x: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).xTrans : (row as BahnPoseIst).xIst,
    ),
    y: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).yTrans : (row as BahnPoseIst).yIst,
    ),
    z: realTrajectory.map((row) =>
      isTransformed ? (row as BahnPoseTrans).zTrans : (row as BahnPoseIst).zIst,
    ),
    name: isTransformed ? 'Transformierte Bahn' : 'Istbahn',
  };

  const idealTrajectoryData: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'soll', 3, 'blue'),
    x: idealTrajectory.map((row) => row.xSoll),
    y: idealTrajectory.map((row) => row.ySoll),
    z: idealTrajectory.map((row) => row.zSoll),
    name: 'Sollbahn',
  };

  // Startpunkt für Ist-Daten
  const getStartPointCoordinate = (coordinate: 'x' | 'y' | 'z'): number => {
    if (realTrajectory.length === 0) return 0;

    const firstPoint = realTrajectory[0];
    if (isTransformed) {
      const transPoint = firstPoint as BahnPoseTrans;
      if (coordinate === 'x') return transPoint.xTrans;
      if (coordinate === 'y') return transPoint.yTrans;
      return transPoint.zTrans;
    }
    const istPoint = firstPoint as BahnPoseIst;
    if (coordinate === 'x') return istPoint.xIst;
    if (coordinate === 'y') return istPoint.yIst;
    return istPoint.zIst;
  };

  const startPointData: Partial<PlotData> = {
    type: 'scatter3d',
    mode: 'markers',
    name: 'Startpunkt',
    x: [getStartPointCoordinate('x')],
    y: [getStartPointCoordinate('y')],
    z: [getStartPointCoordinate('z')],
    marker: {
      size: 4,
      color: 'green',
      symbol: 'diamond', // Andere verfügbare Symbole: 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down', 'pentagon', 'hexagon', 'star'
      opacity: 1,
      line: {
        color: 'darkgreen',
        width: 2,
      },
    },
    hoverlabel: {
      bgcolor: 'green',
    },
    visible: true,
  };

  // Zielpunkte
  const targetPointsData: Partial<PlotData> = {
    type: 'scatter3d',
    mode: 'markers',
    name: 'Zielpunkte',
    x: currentBahnEvents.map((row) => row.xReached),
    y: currentBahnEvents.map((row) => row.yReached),
    z: currentBahnEvents.map((row) => row.zReached),
    marker: {
      size: 4,
      color: 'red',
      symbol: 'circle',
      opacity: 1,
      sizeref: 2,
    },
    hoverlabel: {
      bgcolor: 'red',
    },
    visible: true,
  };

  // Verbindungslinien zwischen den Zielpunkten
  const targetLinesData: Partial<PlotData> = {
    type: 'scatter3d',
    mode: 'lines',
    name: 'Zielpunkt-Verbindungen',
    x: currentBahnEvents.map((row) => row.xReached),
    y: currentBahnEvents.map((row) => row.yReached),
    z: currentBahnEvents.map((row) => row.zReached),
    line: {
      color: 'rgba(255, 0, 0, 0.3)',
      width: 2,
    },
    showlegend: false,
  };

  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    autosize: true,
    margin: { l: 0, r: 0, b: 0, t: 0 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.15,
      x: 0.5,
      xanchor: 'center',
    },
  };

  return (
    <Plot
      data={[
        realTrajectoryData,
        idealTrajectoryData,
        targetLinesData,
        targetPointsData,
        startPointData, // Startpunkt hinzugefügt
      ]}
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
