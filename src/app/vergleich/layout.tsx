import React from 'react';

import { getBahnInfo } from '@/src/actions/bewegungsdaten.service';
import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

interface VergleichLayoutProps {
  children: React.ReactNode;
}

export default async function VergleichLayout({
  children,
}: VergleichLayoutProps) {
  // Lade Bahndaten für den TrajectoryProvider
  const { bahnInfo: initialBahnInfo, pagination: initialPagination } =
    await getBahnInfo({
      page: 1,
      pageSize: 15, // Mehr Bahnen für besseren Vergleich
    });

  return (
    <TrajectoryProvider
      initialBahnInfo={initialBahnInfo}
      initialPagination={initialPagination}
    >
      <main className="flex flex-col lg:flex-row">
        <div className="h-fullscreen w-fit space-y-2 overflow-y-auto bg-white p-4 shadow-lg">
          <div>
            <h2 className="mb-4 text-xl font-bold text-gray-800">
              Tools & Konfiguration
            </h2>
            <div className="space-y-2">
              <MetaValuesCalculator />
              <MetadataUpload />
            </div>
          </div>
        </div>

        <div className="h-fullscreen flex-1 overflow-y-auto">{children}</div>
      </main>
    </TrajectoryProvider>
  );
}
