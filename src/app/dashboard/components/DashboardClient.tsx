/* eslint-disable jsx-a11y/no-noninteractive-element-interactions */
/* eslint-disable no-nested-ternary */

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
import {
  type DashboardData,
  METRICS,
  type MetricType,
  type PerformerData,
} from '@/types/dashboard.types';

interface TimelinePoint {
  date: string;
  tag: string | null;
  avg_val: number;
  min_val: number;
  max_val: number;
  count: number;
}

export default function DashboardClient() {
  // selectedTags = applied (drives data fetching)
  // pendingTags  = what's shown in the dropdown (not yet applied)
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [pendingTags, setPendingTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [metric, setMetric] = useState<MetricType>('sidtw');
  const [basicData, setBasicData] = useState<DashboardData | null>(null);
  const [performersAll, setPerformersAll] = useState<{
    bestPerformers: PerformerData[];
    worstPerformers: PerformerData[];
  }>({ bestPerformers: [], worstPerformers: [] });
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
    ])
      .then(([tags, data, tablePerformers, timeline]) => {
        setAvailableTags((tags as { tags: string[] }).tags);
        setBasicData(data as DashboardData);
        setPerformersAll(tablePerformers as typeof performersAll);
        setTimelineData(
          (timeline as { timeline: TimelinePoint[] }).timeline ?? [],
        );
        initialized.current = true;
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch KPI/distribution data when applied tags change
  useEffect(() => {
    if (!initialized.current) return;
    const tagFilter = selectedTags.length > 0 ? selectedTags : undefined;
    getDashboardData(tagFilter).then((data) =>
      setBasicData(data as DashboardData),
    );
  }, [selectedTags]);

  const togglePending = (t: string) => {
    setPendingTags((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  };

  const applyTags = () => {
    setSelectedTags([...pendingTags]);
    setDropdownOpen(false);
  };

  const removeAll = () => {
    setPendingTags([]);
    setSelectedTags([]);
    setDropdownOpen(false);
  };

  const hasPendingChanges =
    JSON.stringify([...pendingTags].sort()) !==
    JSON.stringify([...selectedTags].sort());

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

  const tagLabel =
    selectedTags.length === 0
      ? 'All tags'
      : selectedTags.length === 1
        ? selectedTags[0]
        : `${selectedTags.length} tags`;

  return (
    <div className="flex min-h-screen border-r border-gray-500 bg-gray-50">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="sticky top-0 flex h-screen w-72 flex-col gap-6 overflow-y-auto border-r border-gray-500 bg-white p-4">
        <div>
          <p className="mb-2 text-xs font-bold uppercase text-gray-800">Tag</p>

          <div className="relative">
            <button
              type="button"
              onClick={() => setDropdownOpen((o) => !o)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-500 bg-gray-50 px-3 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              <span className="truncate">{tagLabel}</span>
              <ChevronDown
                className={`ml-1 size-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 z-50 mt-1 w-full overflow-y-auto rounded-lg border border-gray-500 bg-white shadow-lg">
                {/* Tag list */}
                <div className="max-h-64 overflow-y-auto py-1">
                  <button
                    type="button"
                    onClick={() => setPendingTags([])}
                    className={`w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-gray-50 ${pendingTags.length === 0 ? 'font-semibold text-blue-950' : 'text-gray-700'}`}
                  >
                    All tags
                  </button>
                  {availableTags.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => togglePending(t)}
                      className={`w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-gray-50 ${pendingTags.includes(t) ? 'font-semibold text-blue-950' : 'text-gray-700'}`}
                    >
                      {pendingTags.includes(t) ? '✓ ' : ''}
                      {t}
                    </button>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-1 border-t border-gray-100 p-2">
                  <button
                    type="button"
                    onClick={removeAll}
                    className="flex-1 rounded-md border border-gray-200 px-2 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
                  >
                    Remove all
                  </button>
                  <button
                    type="button"
                    onClick={applyTags}
                    disabled={!hasPendingChanges}
                    className="flex-1 rounded-md bg-blue-950 px-2 py-1.5 text-xs font-medium text-white hover:bg-blue-800 disabled:opacity-40"
                  >
                    Apply
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Applied tag chips */}
          {selectedTags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {selectedTags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-blue-950 px-2 py-1 text-xs text-white"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="mb-2 text-xs font-bold uppercase text-gray-800">
            Metric
          </p>
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
        className="flex-1 overflow-y-auto p-10"
        onClick={() => {
          if (dropdownOpen) setDropdownOpen(false);
        }}
      >
        <div className="mx-auto flex max-w-4xl flex-col gap-8">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <DataCard
              componentName="Trajectories"
              value={basicData.trajsCount}
            />
            <DataCard
              componentName="Segments"
              value={basicData.segmentsCount}
            />
            <AccuracyCard
              medianSIDTW={basicData.medianSIDTW}
              meanSIDTW={basicData.meanSIDTW}
            />
          </div>

          <TagInfoCard selectedTags={selectedTags} />

          <DistributionCharts stats={basicData.stats} />

          <PerformersTable
            initialPerformers={performersAll}
            selectedTags={selectedTags}
            metric={metric}
          />

          <ParameterCorrelation selectedTags={selectedTags} metric={metric} />

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
