import type { PlotData } from 'plotly.js';

import { getTrajectoryById } from '@/src/actions/trajectory.service';
import TrajectoryPlot from '@/src/app/[id]/components/TrajectoryPlot';
import { dataPlotConfig } from '@/src/lib/plot-config';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const trajectory = await getTrajectoryById(params.id);

  const realTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('ist'),
    x: trajectory.xIst,
    y: trajectory.yIst,
    z: trajectory.zIst,
  };

  const idealTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('soll'),
    x: trajectory.xSoll,
    y: trajectory.ySoll,
    z: trajectory.zSoll,
  };

  return (
    <main>
      <TrajectoryPlot
        realTrajectory={realTrajectory}
        idealTrajectory={idealTrajectory}
      />
    </main>
  );
}
