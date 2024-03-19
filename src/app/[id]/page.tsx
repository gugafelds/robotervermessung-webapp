import type { PlotData } from 'plotly.js';

import { getTrajectoryById } from '@/src/actions/trajectory.service';
import TrajectoryPlot from '@/src/app/[id]/components/TrajectoryPlot';
import { dataPlotConfig } from '@/src/lib/plot-config';
import TrajectoryCard from './components/TrajectoryCard';
import { AppProvider } from '@/src/providers/app.provider';
import { getTrajectories } from '@/src/actions/trajectory.service';


type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);
  const trajectories = await getTrajectories();

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
    <main>
      <div style={{ display: 'flex' }}>
        <div style={{ flex: 1 }}>
          <TrajectoryPlot
            realTrajectory={realTrajectory}
            idealTrajectory={idealTrajectory}
          />
        </div>
        <div style={{ flex: 1, marginLeft: '20px' }}>
          <TrajectoryCard
            currentTrajectory={JSON.parse(JSON.stringify(currentTrajectory))}
            trajectories={JSON.parse(JSON.stringify(trajectories))}  // Supondo que a propriedade do cabeçalho da trajetória seja chamada "header"
          />
        </div>
      </div>
    </main>
  );
}