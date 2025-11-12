import React from 'react';

import { getBahnInfo } from '@/src/actions/bewegungsdaten.service';
import { Sidebar } from '@/src/app/bewegungsdaten/components/Sidebar';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function AuswertungLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { bahnInfo: initialBahnInfo, pagination: initialPagination } =
    await getBahnInfo({
      page: 1,
      pageSize: 20,
    });

  return (
    <TrajectoryProvider
      initialBahnInfo={initialBahnInfo}
      initialPagination={initialPagination}
    >
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}{' '}
      </main>
    </TrajectoryProvider>
  );
}
