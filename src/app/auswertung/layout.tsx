import React from 'react';

import { getAuswertungBahnIDs } from '@/src/actions/auswertung.service';
import { Sidebar } from '@/src/app/auswertung/components/Sidebar';
import { AuswertungProvider } from '@/src/providers/auswertung.provider';

export default async function AuswertungLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Lade nur die erste Seite mit einer angemessenen Anzahl von Einträgen
  const result = await getAuswertungBahnIDs({
    page: 1,
    pageSize: 20, // Wähle eine sinnvolle Größe für die initiale Anzeige
  });

  return (
    <AuswertungProvider
      initialAuswertungBahnIDs={result.auswertungBahnIDs}
      initialPagination={result.pagination}
    >
      <main className="flex flex-col lg:flex-row">
        <Sidebar />
        {children}
      </main>
    </AuswertungProvider>
  );
}
