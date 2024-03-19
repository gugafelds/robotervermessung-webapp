import type { PlotData } from 'plotly.js';

import {
  getTrajectoriesHeader,
  getTrajectoryById,
} from '@/src/actions/trajectory.service';
import { json } from '@/src/lib/functions';
import { dataPlotConfig } from '@/src/lib/plot-config';

import { TrajectoryContainer } from './components/TrajectoryContainer';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);
  const trajectoriesHeader = await getTrajectoriesHeader();

  const realTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('ist'),
    x: currentTrajectory.xIst,
    y: currentTrajectory.yIst,
    z: currentTrajectory.zIst,
  };

  const idealTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('soll'),
    x: currentTrajectory.xSoll,
    y: currentTrajectory.ySoll,
    z: currentTrajectory.zSoll,
  };

  return (
    <TrajectoryContainer
      currentTrajectory={json(currentTrajectory)}
      idealTrajectory={json(idealTrajectory)}
      realTrajectory={json(realTrajectory)}
      trajectoriesHeader={json(trajectoriesHeader)}
    />
  );
}
