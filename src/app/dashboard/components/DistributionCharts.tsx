/* eslint-disable react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getDashboardData } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import type { DashboardData } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type TabType =
  | 'weight'
  | 'velocity'
  | 'waypoint'
  | 'performance_sidtw'
  | 'stopPoint'
  | 'waitTime';

interface TabConfig {
  id: TabType;
  label: string;
}

// Separate Komponente für den eigentlichen Chart
interface DistributionChartsContentProps {
  stats: DashboardData['stats'];
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

function DistributionChartsContent({
  stats,
  activeTab,
  setActiveTab,
}: DistributionChartsContentProps) {
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
    { id: 'weight', label: 'Last' },
    { id: 'velocity', label: 'Geschwindigkeit' },
    { id: 'waypoint', label: 'Zielpunkte' },
    { id: 'performance_sidtw', label: 'Genauigkeit' },
    { id: 'stopPoint', label: 'Stopp-Punkte' },
    { id: 'waitTime', label: 'Wartezeit' },
  ];

  // Mapping von TabType zu Distribution
  const getDistribution = (tabId: TabType) => {
    switch (tabId) {
      case 'weight':
        return stats.weightDistribution;
      case 'velocity':
        return stats.velocityDistribution;
      case 'waypoint':
        return stats.waypointDistribution;
      case 'performance_sidtw':
        return stats.performanceSIDTWDistribution;
      case 'stopPoint':
        return stats.stopPointDistribution;
      case 'waitTime':
        return stats.waitTimeDistribution;
      default:
        return stats.weightDistribution;
    }
  };

  const activeDistribution = getDistribution(activeTab);
  const sortedData = [...activeDistribution.data].sort(
    (a, b) => a.bucket - b.bucket,
  );

  // X-Achsen Labels erstellen
  const xLabels = activeDistribution.meta.useRanges
    ? sortedData.map((d) =>
        getBucketRange(
          d.bucket,
          activeDistribution.meta.min!,
          activeDistribution.meta.max!,
          activeDistribution.meta.numBuckets!,
        ),
      )
    : sortedData.map((d) => d.bucket);

  return (
    <div className="rounded-2xl bg-white p-6 shadow">
      {/* Tab Navigation */}
      <div className="mb-6 flex flex-wrap gap-2 border-b">
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

      {/* Chart */}
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
            title: `${activeDistribution.meta.label} [${activeDistribution.meta.unit}]`,
            type: 'category',
          },
          yaxis: { title: 'Anzahl' },
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
          ],
        }}
      />
    </div>
  );
}

export function DistributionCharts() {
  const [stats, setStats] = useState<DashboardData['stats'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('weight');

  // Selbstständiges Laden der Daten
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await getDashboardData();
        setStats(result.stats);
      } catch (err) {
        setError('Fehler beim Laden der Verteilungsdaten');
        setStats(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  // Loading State
  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <Typography as="h3" className="mb-4">
          Datenverteilung
        </Typography>
        <div className="flex h-96 items-center justify-center">
          <div className="text-center">
            <Loader className="mx-auto mb-4 size-12 animate-spin text-blue-950" />
            <p className="text-sm text-gray-600">Lade Verteilungsdaten...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <Typography as="h3" className="mb-4">
          Datenverteilung
        </Typography>
        <div className="flex h-96 items-center justify-center">
          <div className="text-center text-red-600">
            <p className="mb-2 text-lg font-semibold">
              {error || 'Keine Daten verfügbar'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-md bg-blue-950 px-4 py-2 text-white hover:bg-blue-900"
            >
              Seite neu laden
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main Component (mit Daten)
  return (
    <DistributionChartsContent
      stats={stats}
      activeTab={activeTab}
      setActiveTab={setActiveTab}
    />
  );
}
