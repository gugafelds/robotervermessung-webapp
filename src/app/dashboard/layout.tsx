import React from 'react';

import { getBahnInfo } from '@/src/actions/trajectory.service';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const bahnInfo = await getBahnInfo();

  return (
    <TrajectoryProvider bahnInfoDB={json(bahnInfo)}>
      <main className="flex flex-col lg:flex-row">{children}</main>
    </TrajectoryProvider>
  );
}
