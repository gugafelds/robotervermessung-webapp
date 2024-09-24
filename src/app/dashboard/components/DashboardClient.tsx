'use client';

import React from 'react';

import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { Typography } from '@/src/components/Typography';

interface DashboardClientProps {
  trajectoriesCount: number;
  componentCounts: Record<string, number>;
  frequencyData: Record<string, string[]>;
}

export default function DashboardClient({
  trajectoriesCount,
  componentCounts,
  frequencyData,
}: DashboardClientProps) {
  // Define the desired order of components
  const componentOrder = [
    'bahnPoseIst',
    'bahnTwistIst',
    'bahnAccelIst',
    'bahnPositionSoll',
    'bahnOrientationSoll',
    'bahnJointStates',
    'bahnEvents',
  ];

  return (
    <div className="p-6">
      <Typography as="h1">Bewegungsdaten</Typography>

      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <DataCard
          componentName="Aufnahmendateien insgesamt"
          value={trajectoriesCount}
        />
      </div>

      <div className="mb-8">
        <Typography as="h2">Collections Punktzahl</Typography>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {componentOrder.map(
            (component) =>
              componentCounts[component] !== undefined && (
                <DataCard
                  key={component} // This key is for React's internal use
                  componentName={component} // New prop for the component name
                  value={componentCounts[component]}
                />
              ),
          )}
        </div>
      </div>

      <div>
        <Typography as="h2">Frequenzdaten (Ist)</Typography>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(frequencyData)
            .sort(([a], [b]) => Number(b) - Number(a))
            .map(([frequency, ids]) => (
              <div key={frequency} className="rounded-lg bg-white p-4 shadow">
                <h3 className="mb-2 text-lg font-semibold">{frequency} Hz</h3>
                <p>{ids.length} Aufnahme(n)</p>
                <details>
                  <summary className="cursor-pointer text-blue-600">
                    IDs anzeigen
                  </summary>
                  <ul className="mt-2 list-disc pl-5">
                    {ids.map((id) => (
                      <li key={id}>{id}</li>
                    ))}
                  </ul>
                </details>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
