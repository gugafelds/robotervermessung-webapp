// DashboardServer.tsx
import {
  getBahnCount,
  getComponentPointCounts,
  getFrequencyData,
} from '@/src/actions/dashboard.service';

import DashboardClient from './DashboardClient';

export default async function DashboardServer() {
  const trajectoriesCount = await getBahnCount();
  const componentCounts = await getComponentPointCounts();
  const frequencyData = await getFrequencyData();

  return (
    <DashboardClient
      trajectoriesCount={trajectoriesCount}
      componentCounts={componentCounts}
      frequencyData={frequencyData}
    />
  );
}
