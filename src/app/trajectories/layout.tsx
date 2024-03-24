import React from 'react';

import { getTrajectoriesHeader } from '@/src/actions/trajectory.service';
import { Sidebar } from '@/src/app/trajectories/components/Sidebar';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function TrajectoryPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const trajectoriesHeader = await getTrajectoriesHeader();

  return (
    <TrajectoryProvider trajectoriesHeaderDB={trajectoriesHeader}>
      <main className="flex">
        <Sidebar />
        {children}
      </main>
    </TrajectoryProvider>
  );
}
