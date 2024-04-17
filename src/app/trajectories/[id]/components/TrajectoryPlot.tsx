'use client';

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import dynamic from 'next/dynamic';
import type { PlotData } from 'plotly.js';
import { useEffect } from 'react';

import { Typography } from '@/src/components/Typography';
import { dataPlotConfig, plotLayoutConfig } from '@/src/lib/plot-config';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type { TrajectoryData } from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TrajectoryPlotProps = {
  currentTrajectory: TrajectoryData;
};

export const TrajectoryPlot = ({ currentTrajectory }: TrajectoryPlotProps) => {
  const { trajectoriesHeader, euclideanDistances, setEuclidean } =
    useTrajectory();

  useEffect(() => {
    setEuclidean([]);
  }, []);

  const realTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'ist', 6),
    x: currentTrajectory.xIst,
    y: currentTrajectory.yIst,
    z: currentTrajectory.zIst,
  };

  const idealTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('lines', 'soll', 6),
    x: currentTrajectory.xSoll,
    y: currentTrajectory.ySoll,
    z: currentTrajectory.zSoll,
  };

  const euclideanDistancePlot: Partial<PlotData>[] = euclideanDistances.map(
    (inter: any, index: number) => ({
      ...dataPlotConfig(
        'lines+markers',
        'distance',
        3,
        'rgba(100, 100, 100, 0.9)',
        index === 0,
      ),
      ...inter,
    }),
  );

  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
  );

  if (currentTrajectoryID === -1) {
    return (
      <div className="m-10 size-fit place-items-baseline rounded-2xl bg-gray-300 p-10 shadow-xl">
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
        data={[idealTrajectory, realTrajectory, ...euclideanDistancePlot]}
        layout={plotLayoutConfig}
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
          fillFrame: true,
        }}
      />
    </div>
  );
};
