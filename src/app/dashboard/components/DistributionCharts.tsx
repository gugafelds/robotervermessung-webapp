/* eslint-disable react/button-has-type */

'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';

import { Typography } from '@/src/components/Typography';
import type { DashboardData } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TabType =
  | 'weight'
  | 'velocity'
  | 'waypoint'
  | 'performance_sidtw'
  | 'stopPoint';

const tabs: { id: TabType; label: string }[] = [
  { id: 'weight', label: 'Payload' },
  { id: 'velocity', label: 'Velocity' },
  { id: 'waypoint', label: 'Setpoint' },
  { id: 'performance_sidtw', label: 'Accuracy' },
  { id: 'stopPoint', label: 'Stop point' },
];

interface Props {
  stats: DashboardData['stats'];
}

export function DistributionCharts({ stats }: Props) {
  const [activeTab, setActiveTab] = useState<TabType>('weight');

  const distMap: Record<
    TabType,
    DashboardData['stats'][keyof DashboardData['stats']]
  > = {
    weight: stats.weightDistribution,
    velocity: stats.velocityDistribution,
    waypoint: stats.waypointDistribution,
    performance_sidtw: stats.performanceSIDTWDistribution,
    stopPoint: stats.stopPointDistribution,
  };

  const active = distMap[activeTab];
  const sorted = [...active.data].sort((a, b) => a.bucket - b.bucket);

  const getBucketRange = (bucket: number) => {
    const { min = 0, max = 1, numBuckets = 1 } = active.meta;
    const w = (max - min) / numBuckets;
    return `${(min + (bucket - 1) * w).toFixed(2)}-${(min + bucket * w).toFixed(2)}`;
  };

  const xLabels = active.meta.useRanges
    ? sorted.map((d) => getBucketRange(d.bucket))
    : sorted.map((d) => d.bucket);

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
      <Typography as="h2">Data distribution</Typography>
      <div className="mb-6 flex flex-wrap gap-4 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-primary text-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <Plot
        data={[
          {
            x: xLabels,
            y: sorted.map((d) => d.count),
            type: 'bar',
            marker: { color: '#003560' },
          },
        ]}
        layout={{
          autosize: true,
          height: 450,
          margin: { t: 20, r: 20, l: 80, b: 80 },
          xaxis: {
            title: { text: `${active.meta.label} [${active.meta.unit}]` },
            type: 'category',
          },
          yaxis: { title: { text: 'Amount' } },
        }}
        style={{ width: '100%' }}
        config={{
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'lasso2d',
            'zoomIn2d',
            'zoomOut2d',
            'autoScale2d',
            'pan2d',
            'select2d',
          ],
        }}
      />
    </div>
  );
}
