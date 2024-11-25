import { getAllBahnInfo } from '@/src/actions/bewegungsdaten.service';
import DashboardServer from '@/src/app/dashboard/components/DashboardServer';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function DashboardPage() {
  const bahnInfo = await getAllBahnInfo();

  return (
    <TrajectoryProvider initialBahnInfo={json(bahnInfo)}>
      <div className="flex justify-center">
        <DashboardServer />
      </div>
    </TrajectoryProvider>
  );
}
