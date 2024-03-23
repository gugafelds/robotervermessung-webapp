'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import dynamic from 'next/dynamic';
import type { Data } from 'plotly.js';

import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TrajectoryPlotProps = {
  trajectoriesHeader: TrajectoryHeader[];
  currentTrajectory: TrajectoryData;
  idealTrajectory: Data;
  realTrajectory: Data;
};

export default function TrajectoryPlot({
  trajectoriesHeader,
  currentTrajectory,
  idealTrajectory,
  realTrajectory,
}: TrajectoryPlotProps) {
  const data: Data[] = [idealTrajectory, realTrajectory];

  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
  );

  if (currentTrajectoryID === -1) {
    return (
      <div className="m-10 w-fit place-items-baseline rounded-2xl bg-gray-300 p-10 shadow-xl">
        <div>
          <ExclamationTriangleIcon className="mx-auto w-16" color="#003560" />
        </div>
        <Typography as="h3">no plot was found</Typography>
      </div>
    );
  }

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
