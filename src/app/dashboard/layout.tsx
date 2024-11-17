import React from 'react';

import { getAllBahnInfo } from '@/src/actions/bewegungsdaten.service';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const bahnInfo = await getAllBahnInfo();

  return (
    <TrajectoryProvider initialBahnInfo={json(bahnInfo)}>
      <main className="flex-col">{children}</main>
    </TrajectoryProvider>
  );
}
