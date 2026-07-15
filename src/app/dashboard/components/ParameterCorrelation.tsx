/* eslint-disable react/button-has-type,no-nested-ternary */

'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';

import { getMetricInfluence } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import { METRICS, type MetricType } from '@/types/dashboard.types';


const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type ParameterType = 'velocity' | 'acceleration' | 'weight' | 'stop_point';

interface InfluencePoint {
  metric_value: number;
  velocity: number;
  acceleration: number;
  weight: number;
  stop_point: number;
  tag: string;
}

interface BinnedData {
  binLabel: string;
  values: number[];
}

const PARAMETERS: { id: ParameterType; label: string; unit: string; numBins?: number; useRanges: boolean }[] = [
  { id: 'velocity', label: 'Velocity', unit: 'mm/s', numBins: 6, useRanges: true },
  { id: 'acceleration', label: 'Acceleration', unit: 'mm/s²', numBins: 6, useRanges: true },
  { id: 'weight', label: 'Payload', unit: 'kg', useRanges: false },
  { id: 'stop_point', label: 'Stop point', unit: '%', useRanges: false },
];

function bin(data: InfluencePoint[], param: ParameterType, numBins: number): BinnedData[] {
  const vals = data.map((d) => d[param]);
  const min = Math.min(...vals), max = Math.max(...vals);
  const w = (max - min) / numBins;
  const bins: BinnedData[] = [];
  for (let i = 0; i < numBins; i++) {
    const lo = min + i * w, hi = min + (i + 1) * w;
    const inBin = data.filter((d) => i === numBins - 1 ? d[param] >= lo && d[param] <= hi : d[param] >= lo && d[param] < hi);
    if (inBin.length > 0) bins.push({ binLabel: `${lo.toFixed(1)}-${hi.toFixed(1)}`, values: inBin.map((d) => d.metric_value) });
  }
  return bins;
}

function exactGroups(data: InfluencePoint[], param: ParameterType): BinnedData[] {
  const unique = [...new Set(data.map((d) => d[param]))].sort((a, b) => a - b);
  return unique.map((v) => ({
    binLabel: v.toString(),
    values: data.filter((d) => d[param] === v).map((d) => d.metric_value),
  }));
}

interface Props {
  allData: InfluencePoint[];
  selectedTags: string[];
  metric: MetricType;
}

export function ParameterCorrelation({ allData, selectedTags, metric }: Props) {
  const [metricData, setMetricData] = useState<InfluencePoint[]>(allData);
  const [activeParam, setActiveParam] = useState<ParameterType>('velocity');
  const [isLoading, setIsLoading] = useState(false);

  // Re-fetch only when metric changes (allData already loaded for sidtw on mount)
  useEffect(() => {
    if (metric === 'sidtw') { setMetricData(allData); return; }
    setIsLoading(true);
    getMetricInfluence(metric)
      .then((r) => setMetricData((r as { data: InfluencePoint[] }).data ?? []))
      .finally(() => setIsLoading(false));
  }, [metric, allData]);

  // Client-side tag filter — instant
  const data = useMemo(
    () => selectedTags.length > 0 ? metricData.filter((d) => selectedTags.includes(d.tag)) : metricData,
    [metricData, selectedTags]
  );

  const paramConfig = PARAMETERS.find((p) => p.id === activeParam)!;
  const binnedData = data.length === 0 ? [] : paramConfig.useRanges
    ? bin(data, activeParam, paramConfig.numBins!)
    : exactGroups(data, activeParam);

  const medians = binnedData.map((b) => {
    const s = [...b.values].sort((a, c) => a - c);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
  });
  const bestIdx = medians.indexOf(Math.min(...medians));
  const worstIdx = medians.indexOf(Math.max(...medians));

  const { label: metricLabel, unit: metricUnit } = METRICS[metric];

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
      <Typography as="h2" className="mb-2">Factors influencing accuracy</Typography>

      <div className="mb-4 text-sm text-gray-600">
        <p>Box plots showing {metricLabel} distribution for different parameter ranges. Sample of {data.length.toLocaleString()} trajectories.</p>
      </div>

      <div className="mb-6 flex flex-wrap gap-2 border-b">
        {PARAMETERS.map((p) => (
          <button
            key={p.id}
            onClick={() => setActiveParam(p.id)}
            className={`px-4 py-2 font-medium transition-colors ${
              activeParam === p.id ? 'border-b-2 border-primary text-primary' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading || data.length === 0 ? (
        <div className="flex h-96 items-center justify-center text-gray-500">
          {isLoading ? 'Loading...' : 'No data available'}
        </div>
      ) : (
        <>
          <Plot
            data={binnedData.map((b, idx) => ({
              y: b.values,
              type: 'box' as const,
              name: b.binLabel,
              marker: { color: idx === bestIdx ? '#10b981' : idx === worstIdx ? '#ef4444' : '#003560' },
              boxmean: 'sd' as const,
            }))}
            layout={{
              autosize: true,
              height: 500,
              margin: { t: 20, r: 20, l: 80, b: 120 },
              xaxis: { title: { text: `${paramConfig.label} [${paramConfig.unit}]` }, type: 'category' },
              yaxis: { title: { text: `${metricLabel} [${metricUnit}]` } },
              showlegend: false,
            }}
            style={{ width: '100%' }}
            config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] }}
          />
          <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="text-sm text-gray-600">Data Points (Sample)</p>
              <p className="text-2xl font-bold text-blue-950">{data.length.toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-green-50 p-4">
              <p className="text-sm text-gray-600">Best Range</p>
              <p className="text-2xl font-bold text-green-700">{binnedData[bestIdx]?.binLabel} {paramConfig.unit}</p>
              <p className="mt-1 text-xs text-gray-500">Median: {medians[bestIdx]?.toFixed(3)} {metricUnit}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-4">
              <p className="text-sm text-gray-600">Worst Range</p>
              <p className="text-2xl font-bold text-red-700">{binnedData[worstIdx]?.binLabel} {paramConfig.unit}</p>
              <p className="mt-1 text-xs text-gray-500">Median: {medians[worstIdx]?.toFixed(3)} {metricUnit}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
