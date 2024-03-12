import type { Data } from 'plotly.js';

import { getTrajectoryById } from '@/src/actions/trajectory.service';
import TrajectoryPlot from '@/src/app/[id]/components/TrajectoryPlot';

export default async function TrajectoryPage({
  params,
}: {
  params: { id: string };
}) {
  const trajectory = await getTrajectoryById(params.id);

  const realTraject: Data = {
    x: trajectory.data.x_ist,
    y: trajectory.data.y_ist,
    z: trajectory.data.z_ist,
    mode: 'lines',
    type: 'scatter3d',
    name: 'Ist',
  };

  const idealTraject: Data = {
    x: trajectory.data.x_soll,
    y: trajectory.data.y_soll,
    z: trajectory.data.z_soll,
    mode: 'lines',
    type: 'scatter3d',
    name: 'Soll',
  };

  return (
    <main>
      <TrajectoryPlot realTraject={realTraject} idealTraject={idealTraject} />
    </main>
  );
}
