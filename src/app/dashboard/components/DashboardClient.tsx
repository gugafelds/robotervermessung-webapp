'use client';

import Link from 'next/link';
import React, { useState } from 'react';

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
  const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({});

  const componentOrder = [
    'bahnPoseIst',
    'bahnTwistIst',
    'bahnAccelIst',
    'bahnPositionSoll',
    'bahnOrientationSoll',
    'bahnJointStates',
    'bahnEvents',
  ];

  const toggleAllDetails = () => {
    const allClosed = Object.values(openDetails).every((v) => !v);
    const newOpenDetails = Object.keys(frequencyData).reduce(
      (acc, key) => {
        acc[key] = allClosed;
        return acc;
      },
      {} as Record<string, boolean>,
    );
    setOpenDetails(newOpenDetails);
  };

  const toggleDetails = (frequency: string) => {
    setOpenDetails((prev) => ({ ...prev, [frequency]: !prev[frequency] }));
  };

  return (
    <div className="p-6">
      <Typography as="h1">Bewegungsdaten</Typography>

      <div className="flex flex-col lg:flex-row lg:space-x-6">
        <div className="lg:w-2/3">
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
                      key={component}
                      componentName={component}
                      value={componentCounts[component]}
                    />
                  ),
              )}
            </div>
          </div>
        </div>

        <div className="lg:w-1/3">
          <Typography as="h2">Frequenzdaten (Ist)</Typography>
          {/* eslint-disable-next-line react/button-has-type */}
          <button
            onClick={toggleAllDetails}
            className="mb-4 rounded bg-primary px-4 py-2 text-white transition-colors hover:bg-blue-950"
          >
            Alle anzeigen
          </button>
          <div className="space-y-4">
            {Object.entries(frequencyData)
              .sort(([a], [b]) => Number(b) - Number(a))
              .map(([frequency, ids]) => (
                <div key={frequency} className="rounded-lg bg-white p-4 shadow">
                  <div className="mb-2 flex items-center justify-between">
                    <Typography as="h3" className="text-lg font-semibold">
                      {frequency} Hz
                    </Typography>
                    <Typography as="p">{ids.length} Aufnahme(n)</Typography>
                  </div>
                  <div>
                    {/* eslint-disable-next-line react/button-has-type */}
                    <button
                      onClick={() => toggleDetails(frequency)}
                      className="cursor-pointer text-primary hover:underline"
                    >
                      {openDetails[frequency]
                        ? 'IDs verbergen'
                        : 'IDs anzeigen'}
                    </button>
                    {openDetails[frequency] && (
                      <div className="mt-2 grid grid-cols-4 gap-2">
                        {ids.map((id) => (
                          <Link
                            key={id}
                            href={`/trajectories/${id}`}
                            className="truncate rounded bg-gray-200 px-2 py-1 text-center text-sm transition-colors hover:bg-gray-300"
                          >
                            {id}
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
