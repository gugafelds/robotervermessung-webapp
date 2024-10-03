// File: src/app/dashboard/DashboardServer.tsx

import { getDashboardData } from '@/src/actions/dashboard.service';

import DashboardClient from './DashboardClient';

export default async function DashboardServer() {
  const { trajectoriesCount, componentCounts, frequencyData } =
    await getDashboardData();

  return (
    <DashboardClient
      trajectoriesCount={trajectoriesCount}
      componentCounts={componentCounts}
      frequencyData={frequencyData}
    />
  );
}
