/* eslint-disable no-nested-ternary */

'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getInfluenceBinned } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import { METRICS, type MetricType } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Bin {
  label: string;
  median: number;
  q1: number;
  q3: number;
  wlo: number;
  whi: number;
  count: number;
}

type BinnedResult = Record<string, Bin[]>;

const PARAMS: { id: string; label: string }[] = [
  { id: 'velocity', label: 'Velocity' },
  { id: 'acceleration', label: 'Acceleration' },
  { id: 'weight', label: 'Payload' },
  { id: 'stop_point', label: 'Stop point' },
];

interface Props {
  selectedTags: string[];
  metric: MetricType;
}

export function ParameterCorrelation({ selectedTags, metric }: Props) {
  const [data, setData] = useState<BinnedResult>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const tags = selectedTags.length > 0 ? selectedTags : undefined;
    getInfluenceBinned(metric, tags).then((res) => {
      setData((res as BinnedResult) ?? {});
      setLoading(false);
    });
  }, [metric, selectedTags]);

  if (loading) {
    return (
      <div className="flex flex-col rounded-2xl border border-gray-500 bg-white p-4">
        <Typography as="h2" className="mb-3">
          Factors influencing accuracy
        </Typography>
        <div className="flex h-64 items-center justify-center text-sm text-gray-400">
          Loading…
        </div>
      </div>
    );
  }

  const metricLabel = METRICS[metric]?.label ?? metric;
  const subplots = PARAMS.filter((p) => (data[p.id] ?? []).length > 0);

  if (subplots.length === 0) {
    return (
      <div className="flex flex-col rounded-2xl border border-gray-500 bg-white p-4">
        <Typography as="h2" className="mb-3">
          Factors influencing accuracy
        </Typography>
        <div className="flex h-64 items-center justify-center text-sm text-gray-400">
          No data
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col rounded-2xl border border-gray-500 bg-white p-4">
      <Typography as="h2" className="mb-3">
        Factors influencing accuracy
      </Typography>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {subplots.map((p) => {
          const bins = data[p.id] ?? [];
          const medians = bins.map((b) => b.median);
          const minMed = Math.min(...medians);
          const maxMed = Math.max(...medians);
          // One trace per bin for per-box coloring
          const boxTraces = bins.map((b) => {
            const isMin = b.median === minMed;
            const isMax = b.median === maxMed;
            const fillcolor = isMin
              ? 'rgba(134,239,172,0.6)' // light green
              : isMax
                ? 'rgba(252,165,165,0.6)' // light red
                : 'rgba(147,197,253,0.35)';
            return {
              type: 'box',
              name: b.label,
              x: [b.label],
              lowerfence: [b.wlo],
              q1: [b.q1],
              median: [b.median],
              q3: [b.q3],
              upperfence: [b.whi],
              fillcolor,
              line: {
                color: isMin ? '#16a34a' : isMax ? '#dc2626' : '#1e3a5f',
                width: 1.5,
              },
              marker: {
                color: isMin ? '#16a34a' : isMax ? '#dc2626' : '#1e3a5f',
              },
              hovertemplate: `<b>${b.label}</b><br>Median: ${b.median.toFixed(3)}<br>Q1: ${b.q1.toFixed(3)}<br>Q3: ${b.q3.toFixed(3)}<br>n=${b.count}<extra></extra>`,
              showlegend: false,
            } as never;
          });

          return (
            <div key={p.id}>
              <p className="mb-1 text-center text-xs font-semibold text-gray-600">
                {p.label}
              </p>
              <Plot
                data={boxTraces}
                layout={{
                  height: 300,
                  margin: { t: 8, r: 8, l: 40, b: 60 },
                  yaxis: {
                    title: { text: metricLabel, font: { size: 8 } },
                    automargin: true,
                  },
                  xaxis: { type: 'category', tickangle: -25, automargin: true },
                  showlegend: false,
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                }}
                style={{ width: '100%' }}
                config={{
                  displaylogo: false,
                  displayModeBar: false,
                  responsive: true,
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
