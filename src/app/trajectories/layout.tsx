import React from 'react';

import { getTrajectoriesHeader } from '@/src/actions/trajectory.service';
import { Sidebar } from '@/src/app/trajectories/components/Sidebar';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function TrajectoriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const trajectoriesHeader = await getTrajectoriesHeader();

  return (
    <TrajectoryProvider trajectoriesHeaderDB={json(trajectoriesHeader)}>
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}
      </main>
    </TrajectoryProvider>
  );
}
