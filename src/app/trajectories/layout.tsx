import React from 'react';

import { Sidebar } from '@/src/app/trajectories/components/Sidebar';

export default async function TrajectoryPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="flex">
      <Sidebar />
      <div>{children}</div>
    </main>
  );
}
