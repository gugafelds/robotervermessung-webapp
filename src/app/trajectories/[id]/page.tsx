import { getTrajectoryById } from '@/src/actions/trajectory.service';
import { TrajectoryContainer } from '@/src/app/trajectories/[id]/components/TrajectoryContainer';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentTrajectory = await getTrajectoryById(params.id);

  return <TrajectoryContainer currentTrajectory={json(currentTrajectory)} />;
}
