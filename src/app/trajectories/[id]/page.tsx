import type { PlotData } from 'plotly.js';

import {
  getTrajectoriesHeader,
  getTrajectoryById,
} from '@/src/actions/trajectory.service';
import { json } from '@/src/lib/functions';
import { dataPlotConfig } from '@/src/lib/plot-config';

import TrajectoryPlot from './components/TrajectoryPlot';
import TrajectorySidebar from './components/TrajectorySidebar';

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
    <div className="flex space-x-32">
      <TrajectorySidebar
        currentTrajectory={json(currentTrajectory)}
        trajectoriesHeader={json(trajectoriesHeader)}
      />
      <TrajectoryPlot
        idealTrajectory={json(idealTrajectory)}
        realTrajectory={json(realTrajectory)}
      />
    </div>
  );
}
