'use client';

import dynamic from 'next/dynamic';
import type { Data } from 'plotly.js';

import { plotLayoutConfig } from '@/src/lib/plot-config';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TrajectoryPlotProps = {
  idealTrajectory: Data;
  realTrajectory: Data;
};

export default function TrajectoryPlot({
  idealTrajectory,
  realTrajectory,
}: TrajectoryPlotProps) {
  const data: Data[] = [idealTrajectory, realTrajectory];

  return (
    <div className="flex">
      <Plot
        data={data}
        layout={plotLayoutConfig}
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
          fillFrame: true,
        }}
      />
    </div>
  );
}
