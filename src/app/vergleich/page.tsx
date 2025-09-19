import React from 'react';

import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';
import SimilaritySearchWrapper from '@/src/app/vergleich/components/SimilaritySearchWrapper';

export default function BahnVergleichPage() {
  return (
    <div className="bg-gray-50">
      <div className="flex">
        {/* Left Sidebar */}
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

        {/* Main Content Area */}
        <div className="h-fullscreen flex-1 overflow-y-auto p-8">
          <div className="mx-auto max-w-6xl space-y-6">
            <div>
              <h1 className="mb-2 text-3xl font-bold text-gray-900">
                Ähnlichkeitssuche
              </h1>
              <p className="text-gray-600">
                Finden Sie ähnliche Bahnen und Segmente basierend auf
                Feature-Analyse
              </p>
            </div>

            {/* Client Component mit aller Search-Logik */}
            <SimilaritySearchWrapper />
          </div>
        </div>
      </div>
    </div>
  );
}
