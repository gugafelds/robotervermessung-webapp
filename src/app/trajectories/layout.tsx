import React from 'react';

import { getAllBahnInfo } from '@/src/actions/bewegungsdaten.service';
import { Sidebar } from '@/src/app/trajectories/components/Sidebar';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function TrajectoriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const bahnInfo = await getAllBahnInfo();

  return (
    <TrajectoryProvider initialBahnInfo={bahnInfo}>
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}
      </main>
    </TrajectoryProvider>
  );
}
