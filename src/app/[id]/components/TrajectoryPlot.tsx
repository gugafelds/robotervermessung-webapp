'use client';

import dynamic from 'next/dynamic';
import type { Data } from 'plotly.js';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TrajectoryPlotProps = {
  idealTraject: Data;
  realTraject: Data;
};

export default function TrajectoryPlot({
  idealTraject,
  realTraject,
}: TrajectoryPlotProps) {
  const data: Data[] = [idealTraject, realTraject];

  return (
    <div className="flex size-full w-full place-items-center justify-center">
      <Plot
        data={data}
        layout={{
          legend: {
            x: 0,
            y: 1,
            traceorder: 'normal',
            font: {
              family: 'sans-serif',
              size: 12,
              color: '#000',
            },
            bgcolor: '#E2E2E2',
            bordercolor: '#FFFFFF',
            borderwidth: 2,
          },
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
