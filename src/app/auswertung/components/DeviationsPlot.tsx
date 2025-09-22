// DeviationsPlot.tsx - Wrapper Component mit View Toggle

'use client';

import React from 'react';

import { PosDeviationPlot2D } from '@/src/app/auswertung/components/PosDeviationPlot2D';
import { PosDeviationPlot3D } from '@/src/app/auswertung/components/PosDeviationPlot3D';

interface DeviationsPlotProps {
  hasDeviationData: boolean;
  bahnId: string;
  selectedSegment: string;
  onSegmentChange: (segment: string) => void;
}

export const DeviationsPlot: React.FC<DeviationsPlotProps> = ({
  hasDeviationData,
  bahnId,
  selectedSegment,
  onSegmentChange,
}) => {
  if (!hasDeviationData) {
    return (
      <div className="w-full">
        <button
          disabled
          className="rounded bg-gray-300 px-4 py-2 text-gray-600"
        >
          Keine Abweichungsdaten verfügbar
        </button>
      </div>
    );
  }

  return (
    <div className="flex justify-items-stretch space-x-2 p-4">
      {/* Render entsprechende Komponente */}
      <PosDeviationPlot2D
        hasDeviationData={hasDeviationData}
        bahnId={bahnId}
        selectedSegment={selectedSegment}
        onSegmentChange={onSegmentChange}
      />
      <PosDeviationPlot3D
        hasDeviationData={hasDeviationData}
        bahnId={bahnId}
        selectedSegment={selectedSegment}
        onSegmentChange={onSegmentChange}
      />
    </div>
  );
};
