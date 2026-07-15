'use client';

import { ChevronDown, Loader } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import {
  getAvailableTags,
  getDashboardData,
  getMetricTimeline,
  getPerformers,
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

interface TimelinePoint { date: string; tag: string | null; avg_val: number; min_val: number; max_val: number; count: number }

export default function DashboardClient() {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [metric, setMetric] = useState<MetricType>('sidtw');
  const [basicData, setBasicData] = useState<DashboardData | null>(null);
  const [performersAll, setPerformersAll] = useState<{ bestPerformers: PerformerData[]; worstPerformers: PerformerData[] }>({ bestPerformers: [], worstPerformers: [] });
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const initialized = useRef(false);

  useEffect(() => {
    Promise.all([
      getAvailableTags(),
      getDashboardData(),
      getPerformers('sidtw', false),
      getMetricTimeline(),
    ]).then(([tags, data, tablePerformers, timeline]) => {
      setAvailableTags((tags as { tags: string[] }).tags);
      setBasicData(data as DashboardData);
      setPerformersAll(tablePerformers as typeof performersAll);
      setTimelineData((timeline as { timeline: TimelinePoint[] }).timeline ?? []);
      initialized.current = true;
    }).finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!initialized.current) return;
    const tagFilter = selectedTags.length > 0 ? selectedTags : undefined;
    getDashboardData(tagFilter).then((data) => setBasicData(data as DashboardData));
  }, [selectedTags]);

  const toggleTag = (t: string) => {
    setSelectedTags((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
    setDropdownOpen(false);
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

  const tagLabel = selectedTags.length === 0
    ? 'All tags'
    : selectedTags.length === 1
      ? selectedTags[0]
      : `${selectedTags.length} tags selected`;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="sticky top-0 flex h-screen w-56 shrink-0 flex-col gap-6 overflow-y-auto border-r border-gray-200 bg-white p-4">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">Tag</p>

          {/* Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setDropdownOpen((o) => !o)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              <span className="truncate">{tagLabel}</span>
              <ChevronDown className={`ml-1 size-4 shrink-0 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 z-50 mt-1 w-full rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                <button
                  type="button"
                  onClick={() => { setSelectedTags([]); setDropdownOpen(false); }}
                  className={`w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-gray-50 ${selectedTags.length === 0 ? 'font-semibold text-blue-950' : 'text-gray-700'}`}
                >
                  All tags
                </button>
                {availableTags.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleTag(t)}
                    className={`w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-gray-50 ${selectedTags.includes(t) ? 'font-semibold text-blue-950' : 'text-gray-700'}`}
                  >
                    {selectedTags.includes(t) ? '✓ ' : ''}{t}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Active tag chips */}
          {selectedTags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {selectedTags.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setSelectedTags((prev) => prev.filter((x) => x !== t))}
                  className="rounded-full bg-blue-950 px-2 py-0.5 text-xs text-white hover:bg-blue-700"
                  title="Remove"
                >
                  {t} ×
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">Metric</p>
          <div className="flex flex-col gap-1">
            {(Object.keys(METRICS) as MetricType[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMetric(m)}
                className={`rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                  metric === m
                    ? 'bg-blue-950 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {METRICS[m].label}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────────────── */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events,jsx-a11y/no-static-element-interactions */}
      <main
        className="flex-1 overflow-y-auto p-6"
        onClick={() => { if (dropdownOpen) setDropdownOpen(false); }}
      >
        <div className="mx-auto flex max-w-4xl flex-col gap-6">

          {/* KPI row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <DataCard componentName="Trajectories" value={basicData.trajsCount} />
            <DataCard componentName="Segments" value={basicData.segmentsCount} />
            <AccuracyCard medianSIDTW={basicData.medianSIDTW} meanSIDTW={basicData.meanSIDTW} />
          </div>

          <TagInfoCard selectedTags={selectedTags} />

          <DistributionCharts stats={basicData.stats} />

          <PerformersTable
            initialPerformers={performersAll}
            selectedTags={selectedTags}
            metric={metric}
          />

          <ParameterCorrelation
            selectedTags={selectedTags}
            metric={metric}
          />

          <AccuracyTimeline
            allTimeline={timelineData}
            selectedTags={selectedTags}
            metric={metric}
          />

          <WorkareaPlot selectedTags={selectedTags} />

        </div>
      </main>
    </div>
  );
}
