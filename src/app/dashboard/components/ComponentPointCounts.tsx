'use client';

import React from 'react';

import { getComponentPointCounts } from '@/src/actions/dashboard.service';

import { DataCard } from './DataCard';

export async function ComponentPointCounts() {
  const counts = await getComponentPointCounts();

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
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Component Point Counts</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {componentOrder.map(
          (component) =>
            counts[component] !== undefined && (
              <DataCard key={component} value={counts[component]} />
            ),
        )}
      </div>
    </div>
  );
}
