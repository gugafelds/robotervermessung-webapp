import React from 'react';

import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';

interface VergleichLayoutProps {
  children: React.ReactNode;
}

export default function VergleichLayout({ children }: VergleichLayoutProps) {
  return (
    <div className="bg-gray-50">
      <div className="flex">
        {/* Left Sidebar - bleibt konstant für alle Vergleich-Seiten */}
        <div className="h-fullscreen w-fit space-y-6 overflow-y-auto bg-white p-6 shadow-lg">
          <div>
            <h2 className="mb-4 text-xl font-bold text-gray-800">
              Tools & Konfiguration
            </h2>
            <div className="space-y-6">
              <MetaValuesCalculator />
              <MetadataUpload />
            </div>
          </div>
        </div>

        {/* Main Content Area - children werden hier gerendert */}
        <div className="h-fullscreen flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-6xl space-y-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
