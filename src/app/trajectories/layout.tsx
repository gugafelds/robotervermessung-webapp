import React from 'react';

import { Sidebar } from './components/Sidebar';

export default async function TrajectoriesPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main style={{ display: 'flex' }}>
      <Sidebar />
      <div>{children}</div>
    </main>
  );
}
