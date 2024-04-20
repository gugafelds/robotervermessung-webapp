import React from 'react';

import {
  getTrajectoriesEuclideanMetrics,
  getTrajectoriesHeader,
} from '@/src/actions/trajectory.service';
import { Sidebar } from '@/src/app/trajectories/components/Sidebar';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function TrajectoriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const trajectoriesHeader = await getTrajectoriesHeader();
  const trajectoriesEuclideanMetrics = await getTrajectoriesEuclideanMetrics();

  return (
    <TrajectoryProvider
      trajectoriesHeaderDB={json(trajectoriesHeader)}
      trajectoriesEuclideanMetricsDB={json(trajectoriesEuclideanMetrics)}
    >
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}
      </main>
    </TrajectoryProvider>
  );
}
