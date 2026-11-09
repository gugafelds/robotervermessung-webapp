/* eslint-disable no-nested-ternary */

'use client';

import { Loader, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import {
  getAvailableTags,
  getDashboardData,
  getMetricTimeline,
  getPerformers,
  getRobots,
  refreshDashboardCache,
} from '@/src/actions/dashboard.service';
import { AccuracyCard } from '@/src/app/dashboard/components/AccuracyCard';
import { AccuracyTimeline } from '@/src/app/dashboard/components/AccuracyTimeline';
import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { DistributionCharts } from '@/src/app/dashboard/components/DistributionCharts';
import { ParameterCorrelation } from '@/src/app/dashboard/components/ParameterCorrelation';
import { PerformersTable } from '@/src/app/dashboard/components/PerformersTable';
import { RobotTimeWeekly } from '@/src/app/dashboard/components/RobotTimeWeekly';
import { TagInfoCard } from '@/src/app/dashboard/components/TagInfoCard';
import { WorkareaPlot } from '@/src/app/dashboard/components/WorkareaPlot';
import SearchFilter from '@/src/components/SearchFilter';
import { displayName } from '@/src/lib/labels';
import {
  type DashboardData,
  METRICS,
  type MetricType,
  type PerformerData,
} from '@/types/dashboard.types';

interface TimelinePoint {
  date: string;
  tag: string | null;
  robot?: string | null;
  avg_val: number;
  min_val: number;
  max_val: number;
  count: number;
}

export default function DashboardClient() {
  // selectedTags = applied (drives data fetching)
  // pendingTags  = marked in the tag list (not yet applied)
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [pendingTags, setPendingTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState('');
  // robot_model code from motion.robot_info, 'all' = every robot
  const [robot, setRobot] = useState('all');
  const [robots, setRobots] = useState<string[]>([]);
  // tag -> robots it contains (for the work area without a chosen robot)
  const [tagRobots, setTagRobots] = useState<Record<string, string[]>>({});
  const [metric, setMetric] = useState<MetricType>('sidtw');
  const [basicData, setBasicData] = useState<DashboardData | null>(null);
  const [performersAll, setPerformersAll] = useState<{
    bestPerformers: PerformerData[];
    worstPerformers: PerformerData[];
  }>({ bestPerformers: [], worstPerformers: [] });
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const initialized = useRef(false);
  const robotParam = robot === 'all' ? undefined : robot;

  useEffect(() => {
    Promise.all([
      getAvailableTags(),
      getDashboardData(),
      getPerformers('sidtw', false),
      getMetricTimeline(),
      getRobots(),
    ])
      .then(([tags, data, tablePerformers, timeline, robotList]) => {
        setAvailableTags(tags.tags);
        setTagRobots(tags.robots ?? {});
        setRobots(robotList.robots.map((r) => r.robot_model));
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

  // Re-fetch KPI/distribution data when applied tags or the robot change (or on manual refresh)
  useEffect(() => {
    if (!initialized.current) return;
    const tags = selectedTags.length > 0 ? selectedTags : undefined;
    setRefreshing(true);
    getDashboardData(tags, robotParam)
      .then((data) => setBasicData(data as DashboardData))
      .finally(() => setRefreshing(false));
  }, [selectedTags, robotParam]);

  // Tag list of the chosen robot; marked / applied tags of other robots are dropped
  useEffect(() => {
    if (!initialized.current) return;
    getAvailableTags(robotParam).then(({ tags }) => {
      setAvailableTags(tags);
      setPendingTags((prev) => prev.filter((t) => tags.includes(t)));
      setSelectedTags((prev) => {
        const kept = prev.filter((t) => tags.includes(t));
        return kept.length === prev.length ? prev : kept;
      });
    });
  }, [robotParam]);

  const visibleTags = useMemo(() => {
    const q = tagFilter.trim().toLowerCase();
    return [...availableTags]
      .sort((a, b) => a.localeCompare(b))
      .filter((t) => !q || t.toLowerCase().includes(q));
  }, [availableTags, tagFilter]);

  // Work area needs one robot: the chosen one, or the only robot of the applied tags
  const workarea = useMemo((): { robot: string | null; hint: string } => {
    if (robot !== 'all') return { robot, hint: '' };
    if (selectedTags.length === 0)
      return {
        robot: null,
        hint: 'Select a robot, or tags of a single robot, to show the work area',
      };
    const rs = [...new Set(selectedTags.flatMap((t) => tagRobots[t] ?? []))];
    if (rs.length === 1) return { robot: rs[0], hint: '' };
    return {
      robot: null,
      hint: `The selected tags contain several robots (${rs.map(displayName).join(', ')}) — select one robot`,
    };
  }, [robot, selectedTags, tagRobots]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refreshDashboardCache();
    setSelectedTags((prev) => [...prev]);
  };

  const togglePending = (t: string) => {
    setPendingTags((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  };

  const applyTags = () => {
    setSelectedTags([...pendingTags]);
  };

  const removeAll = () => {
    setPendingTags([]);
    setSelectedTags([]);
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

  return (
    <div className="flex h-fullscreen w-full overflow-hidden bg-gray-50">
      {/* ── Tags (search + list, like the Motion sidebar) ─────────────────── */}
      <aside className="flex h-full w-72 shrink-0 flex-col border-r border-gray-500 bg-white px-4 py-2">
        <div className="flex items-center justify-between pl-1">
          <span className="mt-2 text-2xl font-semibold text-primary">Tags</span>
          <button
            type="button"
            onClick={() => {
              // eslint-disable-next-line no-void
              void handleRefresh();
            }}
            disabled={refreshing}
            title="Refresh data"
            className="mt-2 rounded-md p-1 text-gray-500 hover:bg-gray-200 disabled:opacity-40"
          >
            <RefreshCw
              className={`size-4 ${refreshing ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
        <SearchFilter
          onFilterChange={setTagFilter}
          placeholder="Filter tags..."
        />
        <div className="mt-3 flex gap-1">
          <button
            type="button"
            onClick={removeAll}
            disabled={pendingTags.length === 0 && selectedTags.length === 0}
            className="flex-1 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40"
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
        <div className="mt-2 pl-1 text-sm text-gray-600">
          {selectedTags.length === 0
            ? `All tags (${availableTags.length})`
            : `${selectedTags.length} of ${availableTags.length} tags applied`}
        </div>
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
          {visibleTags.length === 0 && (
            <div className="py-4 text-center text-sm text-gray-500">
              No tags found
            </div>
          )}
          {visibleTags.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => togglePending(t)}
              className={`mt-1 flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-left text-sm transition-colors duration-200 ${
                pendingTags.includes(t)
                  ? 'bg-gray-300 font-semibold text-primary'
                  : 'text-gray-700 hover:bg-gray-200'
              }`}
            >
              <span className="truncate">{t}</span>
              {selectedTags.includes(t) && (
                <span className="ml-2 rounded-full bg-blue-950 px-1.5 text-xs text-white">
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto p-10">
        <div className="mx-auto flex max-w-4xl flex-col gap-8">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DataCard
              componentName="Trajectories"
              value={basicData.trajsCount}
            />
            <DataCard
              componentName="Segments"
              value={basicData.segmentsCount}
            />
            <DataCard
              componentName="Robot time"
              value={basicData.robotTimeHours}
              unit="h"
              decimals={1}
              note={`on ${basicData.recordingDays} measurement days`}
            />
            <AccuracyCard
              medianSIDTW={basicData.medianSIDTW}
              meanSIDTW={basicData.meanSIDTW}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DataCard
              componentName="Measured poses"
              value={basicData.posePoints}
              note="laser tracker samples"
            />
            <DataCard
              componentName="Joint states"
              value={basicData.jointPoints}
              note="controller samples"
            />
            <DataCard
              componentName="Command poses"
              value={basicData.cmdPoints}
              note="controller samples"
            />
            <DataCard
              componentName="Database size"
              value={basicData.dbSizeBytes / 1e9}
              unit="GB"
              note="whole database"
            />
          </div>

          <TagInfoCard
            selectedTags={selectedTags}
            robot={workarea.robot ?? undefined}
          />

          <DistributionCharts stats={basicData.stats} />

          <PerformersTable
            initialPerformers={performersAll}
            selectedTags={selectedTags}
            metric={metric}
            robot={robotParam}
          />

          <ParameterCorrelation
            selectedTags={selectedTags}
            metric={metric}
            robot={robotParam}
          />

          <AccuracyTimeline
            allTimeline={timelineData}
            selectedTags={selectedTags}
            metric={metric}
            robot={robotParam}
          />

          <RobotTimeWeekly weekly={basicData.robotTimeWeekly ?? []} />

          <WorkareaPlot
            selectedTags={selectedTags}
            robot={workarea.robot}
            hint={workarea.hint}
          />
        </div>
      </main>

      {/* ── Robot + metric ───────────────────────────────────────────────── */}
      <aside className="flex h-full w-56 shrink-0 flex-col gap-6 overflow-y-auto border-l border-gray-500 bg-white p-4">
        <div>
          <p className="mb-2 text-xs font-bold uppercase text-gray-800">
            Robot
          </p>
          <div className="flex flex-col gap-1">
            {['all', ...robots].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRobot(r)}
                className={`rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                  robot === r
                    ? 'bg-blue-950 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {r === 'all' ? 'All' : displayName(r)}
              </button>
            ))}
          </div>
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
    </div>
  );
}
