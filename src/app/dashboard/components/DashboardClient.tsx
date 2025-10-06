/* eslint-disable react/button-has-type */

'use client';

import dynamic from 'next/dynamic';
import React, { useState } from 'react';

import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { WorkareaPlot } from '@/src/app/dashboard/components/WorkareaPlot';
import { Typography } from '@/src/components/Typography';
import type { DashboardData } from '@/types/dashboard.types';

type TabType =
  | 'weight'
  | 'velocity'
  | 'waypoint'
  | 'performance_sidtw'
  | 'stopPoint'
  | 'waitTime';

interface TabConfig {
  id: string;
  label: string;
  data: Array<{ bucket: number; count: number }>;
  unit: string;
  min: number;
  max: number;
  numBuckets: number;
  useRanges: boolean;
}

export default function DashboardClient({
  filenamesCount,
  bahnenCount,
  stats,
  workareaPoints,
}: DashboardData) {
  const [activeTab, setActiveTab] = useState<TabType>('weight');

  const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

  const getBucketRange = (
    bucketNum: number,
    min: number,
    max: number,
    numBuckets: number,
  ) => {
    const bucketWidth = (max - min) / numBuckets;
    const start = min + (bucketNum - 1) * bucketWidth;
    const end = min + bucketNum * bucketWidth;
    return `${start.toFixed(2)}-${end.toFixed(2)}`;
  };

  const tabs: TabConfig[] = [
    {
      id: 'weight',
      label: 'Last',
      data: stats.weightDistribution,
      unit: 'kg',
      min: 0,
      max: 0,
      numBuckets: 0,
      useRanges: false,
    },
    {
      id: 'velocity',
      label: 'Geschwindigkeit',
      data: stats.velocityDistribution,
      unit: 'mm/s',
      min: 0,
      max: 0,
      numBuckets: 0,
      useRanges: false,
    },
    {
      id: 'waypoint',
      label: 'Zielpunkte',
      data: stats.waypointDistribution,
      unit: '-',
      min: 0,
      max: 0,
      numBuckets: 0,
      useRanges: false,
    },
    {
      id: 'performance_sidtw',
      label: 'Genauigkeit',
      data: stats.performanceSIDTWDistribution,
      unit: 'mm',
      min: 0,
      max: 3.2475,
      numBuckets: 10,
      useRanges: true,
    },
    {
      id: 'stopPoint',
      label: 'Stopp-Punkte',
      data: stats.stopPointDistribution,
      unit: '%',
      min: 0,
      max: 0,
      numBuckets: 0,
      useRanges: false,
    },
    {
      id: 'waitTime',
      label: 'Wartezeit',
      data: stats.waitTimeDistribution,
      unit: 's',
      min: 0,
      max: 0,
      numBuckets: 0,
      useRanges: false,
    },
  ];

  const activeTabData = tabs.find((tab) => tab.id === activeTab);
  const sortedData = activeTabData
    ? [...activeTabData.data].sort((a, b) => a.bucket - b.bucket)
    : [];

  // X-Achsen Labels erstellen
  const xLabels = activeTabData?.useRanges
    ? sortedData.map((d) =>
        getBucketRange(
          d.bucket,
          activeTabData.min,
          activeTabData.max,
          activeTabData.numBuckets,
        ),
      )
    : sortedData.map((d) => d.bucket);

  return (
    <div className="justify-center p-6">
      <Typography as="h2" className="py-2">
        Bewegungsdaten
      </Typography>

      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <DataCard componentName="Roboterbahnen insgesamt" value={bahnenCount} />
        <DataCard
          componentName="Aufnahmendateien insgesamt"
          value={filenamesCount}
        />
      </div>

      <Typography as="h2" className="py-2">
        Datenverteilung
      </Typography>

      <div className="rounded-2xl bg-white p-6 shadow">
        {/* Tab Navigation */}
        <div className="mb-6 flex flex-wrap gap-2 border-b">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
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

        {/* Chart */}
        <Typography as="h3" className="mb-4">
          {activeTabData?.label}
        </Typography>
        <Plot
          data={[
            {
              x: xLabels,
              y: sortedData.map((d) => d.count),
              type: 'bar',
              marker: { color: '#003560' },
            },
          ]}
          layout={{
            autosize: true,
            height: 300,
            margin: { t: 20, r: 20, l: 80, b: 80 },
            xaxis: {
              title: `${activeTabData?.label} [${activeTabData?.unit}]`,
              type: 'category',
            },
            yaxis: { title: 'Anzahl' },
          }}
          style={{ width: '100%' }}
          config={{ responsive: true }}
        />
      </div>

      {/* Arbeitsraum */}
      <Typography as="h2" className="mt-8 py-2">
        Arbeitsraum
      </Typography>
      <WorkareaPlot data={workareaPoints} />
    </div>
  );
}
