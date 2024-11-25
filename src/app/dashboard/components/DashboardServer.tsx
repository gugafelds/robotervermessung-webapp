import {
  getCollectionSizes,
  getDashboardData,
} from '@/src/actions/dashboard.service';

import DashboardClient from './DashboardClient';

export default async function DashboardServer() {
  // Parallel data fetching für bessere Performance
  const [dashboardData, collectionSizes] = await Promise.all([
    getDashboardData(),
    getCollectionSizes(),
  ]);

  const { trajectoriesCount, componentCounts, frequencyData } = dashboardData;

  return (
    <DashboardClient
      trajectoriesCount={trajectoriesCount}
      componentCounts={componentCounts}
      frequencyData={frequencyData}
      collectionSizes={collectionSizes}
    />
  );
}
