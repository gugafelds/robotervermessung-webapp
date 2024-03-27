import { getTrajectoryById } from '@/src/actions/trajectory.service';
import { TrajectoryInfo } from '@/src/app/trajectories/[id]/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/[id]/components/TrajectoryPlot';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);

  return (
    <div className="flex justify-center sm:flex-col sm:space-x-0 lg:flex-row lg:space-x-32">
      <TrajectoryInfo currentTrajectory={json(currentTrajectory)} />

      <TrajectoryPlot currentTrajectory={json(currentTrajectory)} />
    </div>
  );
}
