'use client';

import { Loader } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import {
  getAvailableTags,
  getDashboardData,
  getMetricInfluence,
  getMetricTimeline,
  getPerformers,
  getWorkareaData,
} from '@/src/actions/dashboard.service';
import { AccuracyCard } from '@/src/app/dashboard/components/AccuracyCard';
import { AccuracyTimeline } from '@/src/app/dashboard/components/AccuracyTimeline';
import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { DistributionCharts } from '@/src/app/dashboard/components/DistributionCharts';
import { ParameterCorrelation } from '@/src/app/dashboard/components/ParameterCorrelation';
import { PerformersTable } from '@/src/app/dashboard/components/PerformersTable';
import { TagInfoCard } from '@/src/app/dashboard/components/TagInfoCard';
import { WorkareaPlot } from '@/src/app/dashboard/components/WorkareaPlot';
import { Typography } from '@/src/components/Typography';
import { METRICS, type DashboardData, type MetricType, type PerformerData } from '@/types/dashboard.types';

interface WorkareaPoint { x: number; y: number; z: number; sidtw: number; tag: string }
interface InfluencePoint { metric_value: number; velocity: number; acceleration: number; weight: number; stop_point: number; tag: string }
interface TimelinePoint { date: string; tag: string | null; avg_val: number; min_val: number; max_val: number; count: number }

export default function DashboardClient() {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [metric, setMetric] = useState<MetricType>('sidtw');
  const [basicData, setBasicData] = useState<DashboardData | null>(null);
  const [sidtwPerformers, setSidtwPerformers] = useState<{ bestPerformers: PerformerData[]; worstPerformers: PerformerData[] }>({ bestPerformers: [], worstPerformers: [] });
  const [workareaPoints, setWorkareaPoints] = useState<WorkareaPoint[]>([]);
  const [influenceData, setInfluenceData] = useState<InfluencePoint[]>([]);
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);
  const [performersAll, setPerformersAll] = useState<{ bestPerformers: PerformerData[]; worstPerformers: PerformerData[] }>({ bestPerformers: [], worstPerformers: [] });
  const [loading, setLoading] = useState(true);
  const initialized = useRef(false);

  // Load heavy data once on mount
  useEffect(() => {
    Promise.all([
      getAvailableTags(),
      getDashboardData(),
      getPerformers('sidtw', true),   // with trajectories for WorkareaPlot
      getPerformers('sidtw', false),  // 100 best/worst for PerformersTable
      getWorkareaData(),
      getMetricInfluence(),
      getMetricTimeline(),
    ]).then(([tags, data, trajPerformers, tablePerformers, workarea, influence, timeline]) => {
      setAvailableTags((tags as { tags: string[] }).tags);
      setBasicData(data as DashboardData);
      setSidtwPerformers(trajPerformers as typeof sidtwPerformers);
      setPerformersAll(tablePerformers as typeof performersAll);
      setWorkareaPoints((workarea as { points: WorkareaPoint[] }).points ?? []);
      setInfluenceData((influence as { data: InfluencePoint[] }).data ?? []);
      setTimelineData((timeline as { timeline: TimelinePoint[] }).timeline ?? []);
      initialized.current = true;
    }).finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // On tag change: only re-fetch KPI/distribution data silently (keep old values visible)
  useEffect(() => {
    if (!initialized.current) return;
    const tagFilter = selectedTags.length > 0 ? selectedTags : undefined;
    getDashboardData(tagFilter).then((data) => setBasicData(data as DashboardData));
  }, [selectedTags]);

  const toggleTag = (t: string) => {
    setSelectedTags((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader className="size-10 animate-spin text-blue-950" />
      </div>
    );
  }

  if (!basicData) {
    return <div className="p-6">Error: No data found</div>;
  }

  return (
    <div className="w-full space-y-4 p-4">
      {/* Global filters */}
      <div className="space-y-2 rounded-2xl border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-sm font-semibold text-gray-700">Tags:</span>
          <button
            type="button"
            onClick={() => setSelectedTags([])}
            className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
              selectedTags.length === 0
                ? 'bg-blue-950 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          {availableTags.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => toggleTag(t)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                selectedTags.includes(t)
                  ? 'bg-blue-950 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-sm font-semibold text-gray-700">Metrics:</span>
          {(Object.keys(METRICS) as MetricType[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMetric(m)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                metric === m
                  ? 'bg-blue-950 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {METRICS[m].label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-1 lg:grid-cols-2">
        <div>
          <Typography as="h2">Motion Data</Typography>
          <div className="my-2 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            <DataCard componentName="Trajectories overall" value={basicData.trajsCount} />
            <DataCard componentName="Segments overall" value={basicData.segmentsCount} />
            <AccuracyCard medianSIDTW={basicData.medianSIDTW} meanSIDTW={basicData.meanSIDTW} />
          </div>

          {/* Tag info cards — only visible when tags are selected */}
          <TagInfoCard selectedTags={selectedTags} />

          <DistributionCharts stats={basicData.stats} />
        </div>

        <PerformersTable
          initialPerformers={performersAll}
          selectedTags={selectedTags}
          metric={metric}
        />

        <ParameterCorrelation
          allData={influenceData}
          selectedTags={selectedTags}
          metric={metric}
        />

        <WorkareaPlot
          allPoints={workareaPoints}
          selectedTags={selectedTags}
          bestPerformers={sidtwPerformers.bestPerformers}
          worstPerformers={sidtwPerformers.worstPerformers}
        />

        <AccuracyTimeline
          allTimeline={timelineData}
          selectedTags={selectedTags}
          metric={metric}
        />
      </div>
    </div>
  );
}
