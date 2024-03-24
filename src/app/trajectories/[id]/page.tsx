import { getTrajectoryById } from '@/src/actions/trajectory.service';
import { TrajectoryInfo } from '@/src/app/trajectories/[id]/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/[id]/components/TrajectoryPlot';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);

  return (
    <div className="flex space-x-32">
      <TrajectoryInfo currentTrajectory={currentTrajectory} />

      <TrajectoryPlot currentTrajectory={currentTrajectory} />
    </div>
  );
}
