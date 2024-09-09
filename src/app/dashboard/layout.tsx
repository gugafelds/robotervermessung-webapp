import React from 'react';

import { getSegmentsHeader, getTrajectoriesHeader } from '@/src/actions/trajectory.service';
import { json } from '@/src/lib/functions';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const trajectoriesHeader = await getTrajectoriesHeader();
  const segmentsHeader = await getSegmentsHeader();


  return (
    <TrajectoryProvider trajectoriesHeaderDB={json(trajectoriesHeader)} segmentsHeaderDB={json(segmentsHeader)}>
      <main className="flex flex-col lg:flex-row">{children}</main>
    </TrajectoryProvider>
  );
}
