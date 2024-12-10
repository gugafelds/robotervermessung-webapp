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

  const { bahnenCount, filenamesCount, componentCounts, frequencyData } =
    dashboardData;

  return (
    <DashboardClient
      bahnenCount={bahnenCount}
      filenamesCount={filenamesCount}
      componentCounts={componentCounts}
      frequencyData={frequencyData}
      collectionSizes={collectionSizes}
    />
  );
}
