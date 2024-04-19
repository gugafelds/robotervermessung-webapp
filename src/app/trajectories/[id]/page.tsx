import React from 'react';

import { getTrajectoryById } from '@/src/actions/trajectory.service';
import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);

  return (
    <>
      <TrajectoryInfo currentTrajectory={json(currentTrajectory)} />

      <TrajectoryPlot currentTrajectory={json(currentTrajectory)} />
    </>
  );
}
