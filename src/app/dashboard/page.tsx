import { getTrajectoriesCount } from '@/src/actions/dashboard.service';
import { DataCard } from '@/src/app/dashboard/components/DataCard';

export default async function Dashboard() {
  const trajectoriesCount = await getTrajectoriesCount();

  return (
    <section className="flex flex-col p-5 lg:flex-row">
      <DataCard title="Total Trajectories" value={trajectoriesCount} />
    </section>
  );
}
