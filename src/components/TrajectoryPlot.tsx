'use client';

import dynamic from 'next/dynamic';
import type { Data } from 'plotly.js';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export default function TrajectoryPlot() {
  const data: Data[] = [
    {
      x: [1, 4, 7, 6, 12],
      y: [1, 3, 8, 9, 12],
      z: [1, 5, 6, 9, 5],
      mode: 'lines',
      type: 'scatter3d',
    },
  ];

  return (
    <div className="flex size-full w-full place-items-center justify-center">
      <Plot
        data={data}
        layout={{
          width: 800,
          height: 600,
          scene: {
            xaxis: { title: 'X Axis' },
            yaxis: { title: 'Y Axis' },
            zaxis: { title: 'Z Axis' },
          },
        }}
      />
    </div>
  );
}
