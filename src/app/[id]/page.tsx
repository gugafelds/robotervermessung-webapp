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
    ...dataPlotConfig('Ist'),
    x: trajectory.data.xIst,
    y: trajectory.data.yIst,
    z: trajectory.data.zIst,
  };

  const idealTrajectory: Partial<PlotData> = {
    ...dataPlotConfig('Soll'),
    x: trajectory.data.xSoll,
    y: trajectory.data.ySoll,
    z: trajectory.data.zSoll,
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
