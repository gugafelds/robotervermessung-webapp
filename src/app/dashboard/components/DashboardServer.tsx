import {
  getCollectionSizes,
  getDashboardData,
} from '@/src/actions/dashboard.service';

import DashboardClient from './DashboardClient';

export default async function DashboardServer() {
  const { trajectoriesCount, componentCounts, frequencyData } =
    await getDashboardData();
  const collectionSizes = await getCollectionSizes();

  return (
    <DashboardClient
      trajectoriesCount={trajectoriesCount}
      componentCounts={componentCounts}
      frequencyData={frequencyData}
      collectionSizes={collectionSizes}
    />
  );
}
