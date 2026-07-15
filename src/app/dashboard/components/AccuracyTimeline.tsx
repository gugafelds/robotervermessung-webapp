/* eslint-disable react/button-has-type */

'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';

import { getMetricTimeline } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import { METRICS, type MetricType } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TimelinePoint {
  date: string;
  tag: string | null;
  avg_val: number;
  min_val: number;
  max_val: number;
  count: number;
}

interface AggPoint {
  date: string;
  avg_val: number;
  min_val: number;
  max_val: number;
  count: number;
}

interface Props {
  allTimeline: TimelinePoint[];
  selectedTags: string[];
  metric: MetricType;
}

function aggregate(rows: TimelinePoint[], tags: string[]): AggPoint[] {
  const src = tags.length > 0 ? rows.filter((r) => r.tag !== null && tags.includes(r.tag)) : rows;
  const byDate = new Map<string, { wsum: number; count: number; min: number; max: number }>();
  for (const r of src) {
    const cur = byDate.get(r.date) ?? { wsum: 0, count: 0, min: Infinity, max: -Infinity };
    byDate.set(r.date, {
      wsum: cur.wsum + r.avg_val * r.count,
      count: cur.count + r.count,
      min: Math.min(cur.min, r.min_val),
      max: Math.max(cur.max, r.max_val),
    });
  }
  return [...byDate.entries()]
    .map(([date, { wsum, count, min, max }]) => ({ date, avg_val: wsum / count, min_val: min, max_val: max, count }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function AccuracyTimeline({ allTimeline, selectedTags, metric }: Props) {
  const [metricTimeline, setMetricTimeline] = useState<TimelinePoint[]>(allTimeline);
  const [isLoading, setIsLoading] = useState(false);

  // Re-fetch only when metric changes
  useEffect(() => {
    if (metric === 'sidtw') { setMetricTimeline(allTimeline); return; }
    setIsLoading(true);
    getMetricTimeline(metric)
      .then((r) => setMetricTimeline((r as { timeline: TimelinePoint[] }).timeline ?? []))
      .finally(() => setIsLoading(false));
  }, [metric, allTimeline]);

  // Client-side tag aggregation — instant
  const data = useMemo(() => aggregate(metricTimeline, selectedTags), [metricTimeline, selectedTags]);

  const { label, unit } = METRICS[metric];

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
      <Typography as="h2" className="mb-2">Accuracy Timeline</Typography>

      <div className="mb-4 text-sm text-gray-600">
        <p>Development of measurement accuracy ({label}) over time. An increase could indicate wear and tear or calibration problems.</p>
      </div>

      {isLoading || data.length === 0 ? (
        <div className="flex h-96 items-center justify-center text-gray-500">
          {isLoading ? 'Loading...' : 'No timeline data available'}
        </div>
      ) : (
        <>
          <Plot
            data={[
              {
                x: data.map((d) => d.date),
                y: data.map((d) => d.avg_val),
                type: 'scatter', mode: 'lines+markers', name: 'Average',
                line: { color: '#003560', width: 3 }, marker: { size: 6 },
                hovertemplate: `<b>Average ${label}</b><br>Date: %{x}<br>${label}: %{y:.3f} ${unit}<extra></extra>`,
              },
              {
                x: data.map((d) => d.date),
                y: data.map((d) => d.min_val),
                type: 'scatter', mode: 'lines', name: 'Minimum',
                line: { color: '#10b981', width: 2, dash: 'dash' },
                hovertemplate: `<b>Min ${label}</b><br>Date: %{x}<br>${label}: %{y:.3f} ${unit}<extra></extra>`,
              },
              {
                x: data.map((d) => d.date),
                y: data.map((d) => d.max_val),
                type: 'scatter', mode: 'lines', name: 'Maximum',
                line: { color: '#ef4444', width: 2, dash: 'dash' },
                hovertemplate: `<b>Max ${label}</b><br>Date: %{x}<br>${label}: %{y:.3f} ${unit}<extra></extra>`,
              },
            ]}
            layout={{
              autosize: true, height: 500,
              margin: { t: 20, r: 20, l: 80, b: 80 },
              xaxis: { title: { text: 'Recording date' }, type: 'date', tickformat: '%d.%m.%Y' },
              yaxis: { title: { text: `${label} [${unit}]` }, rangemode: 'tozero' },
              hovermode: 'x unified', showlegend: true,
              legend: { x: 0.8, y: 0.98, bgcolor: 'rgba(255,255,255,0.8)' },
            }}
            style={{ width: '100%' }}
            config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ['toImage', 'orbitRotation', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'pan2d'] }}
          />
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="text-sm text-gray-600">Overall Measurements</p>
              <p className="text-2xl font-bold text-blue-950">{data.reduce((s, d) => s + d.count, 0).toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-green-50 p-4">
              <p className="text-sm text-gray-600">Best Average</p>
              <p className="text-2xl font-bold text-green-700">{Math.min(...data.map((d) => d.avg_val)).toFixed(3)} {unit}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-4">
              <p className="text-sm text-gray-600">Worst Average</p>
              <p className="text-2xl font-bold text-red-700">{Math.max(...data.map((d) => d.avg_val)).toFixed(3)} {unit}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
