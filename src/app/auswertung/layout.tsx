import React from 'react';

import { getAllAuswertungInfo } from '@/src/actions/auswertung.service';
import { Sidebar } from '@/src/app/auswertung/components/Sidebar';
import { AuswertungProvider } from '@/src/providers/auswertung.provider';

export default async function AuswertungLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const auswertungInfo = await getAllAuswertungInfo();

  return (
    <AuswertungProvider initialAuswertungInfo={auswertungInfo}>
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}
      </main>
    </AuswertungProvider>
  );
}
