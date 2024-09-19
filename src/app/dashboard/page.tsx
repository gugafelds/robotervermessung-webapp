import { getBahnCount } from '@/src/actions/dashboard.service';
import { DataCard } from '@/src/app/dashboard/components/DataCard';

export default async function Dashboard() {
  const trajectoriesCount = await getBahnCount();

  return (
    <section className="flex flex-col p-5 lg:flex-row">
      <DataCard title="Aufnahmendateien insgesamt" value={trajectoriesCount} />
    </section>
  );
}
