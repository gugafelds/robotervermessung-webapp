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
      symbol: 'diamond',
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
    title: '3D-Position',
    autosize: true,
    height: 500,
    scene: {
      camera: {
        up: { x: 0, y: 0, z: 1 },
        center: { x: 0, y: 0, z: -0.1 },
        eye: { x: 1.15, y: 1, z: 1 },
      },
      aspectmode: 'cube',
      dragmode: 'orbit',
      xaxis: { title: 'X [mm]', showgrid: true, zeroline: true },
      yaxis: { title: 'Y [mm]', showgrid: true, zeroline: true },
      zaxis: { title: 'Z [mm]', showgrid: true, zeroline: true },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    uirevision: 'true',
    showlegend: true,
    width: 600,
    legend: {
      orientation: 'h',
      y: -0.15,
      x: 0.5,
      xanchor: 'center',
      bgcolor: 'rgba(255,255,255,0.8)',
    },
  };

  if (!realTrajectoryData) {
    return null;
  }

  return (
    <div className="m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-2 shadow-sm">
      <Plot
        data={[
          realTrajectoryData,
          idealTrajectoryData,
          targetLinesData,
          targetPointsData,
          startPointData,
        ]}
        layout={layout}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
        className="border border-gray-400"
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'zoom3d',
            'tableRotation',
            'pan3d',
            'resetCameraDefault3d',
          ],
          responsive: true,
        }}
      />
    </div>
  );
};
