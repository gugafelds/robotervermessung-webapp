import React from 'react';

import { getTrajInfo } from '@/src/actions/motion.service';
import { Sidebar } from '@/src/app/motion/components/Sidebar';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

export default async function EvaluationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { trajInfo: initialTrajInfo, pagination: initialPagination } =
    await getTrajInfo({
      page: 1,
      pageSize: 40,
    });

  return (
    <TrajectoryProvider
      initialTrajInfo={initialTrajInfo}
      initialPagination={initialPagination}
    >
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}{' '}
      </main>
    </TrajectoryProvider>
  );
}
