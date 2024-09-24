'use client';

import React from 'react';

import { getFrequencyData } from '@/src/actions/dashboard.service';

export async function FrequencyData() {
  const frequencyData = await getFrequencyData();

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Frequenzdaten (IST)</h2>
      <div className="space-y-4">
        {Object.entries(frequencyData)
          .sort(([a], [b]) => Number(b) - Number(a)) // Sort frequencies in descending order
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
  );
}
