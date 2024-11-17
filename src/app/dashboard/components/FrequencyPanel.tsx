import Link from 'next/link';
import React, { useState } from 'react';

import { Typography } from '@/src/components/Typography';

interface FrequencyPanelProps {
  frequencyData: Record<string, string[]>;
}

export function FrequencyPanel({ frequencyData }: FrequencyPanelProps) {
  const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({});

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
    <div className="h-fullscreen w-80 overflow-hidden bg-gray-50">
      <div className="flex h-full flex-col">
        <div className="p-4">
          <Typography as="h4">Frequenzdaten</Typography>
          {/* eslint-disable-next-line react/button-has-type */}
          <button
            onClick={toggleAllDetails}
            className="my-2 w-full rounded bg-primary p-1 text-white transition-colors hover:bg-blue-950"
          >
            Alle anzeigen
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
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
                      <div className="mt-2 grid grid-cols-2 gap-2">
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
