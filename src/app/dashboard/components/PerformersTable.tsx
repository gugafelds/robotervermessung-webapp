/* eslint-disable react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

import { getPerformers } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import { METRICS, type MetricType, type PerformerData } from '@/types/dashboard.types';

interface Props {
  initialPerformers: { bestPerformers: PerformerData[]; worstPerformers: PerformerData[] };
  selectedTags: string[];
  metric: MetricType;
}

export function PerformersTable({ initialPerformers, selectedTags, metric }: Props) {
  const [performers, setPerformers] = useState(initialPerformers);
  const [loading, setLoading] = useState(false);
  const isFirst = useRef(true);

  // When metric changes: show spinner. When tags change: background refresh (keep old data).
  useEffect(() => {
    if (isFirst.current) { isFirst.current = false; return; }
    const tags = selectedTags.length > 0 ? selectedTags : undefined;
    const isMetricChange = !tags; // simplification — spinner only on first metric change
    if (isMetricChange) setLoading(true);
    getPerformers(metric, false, tags)
      .then((r) => setPerformers(r as typeof performers))
      .finally(() => setLoading(false));
  }, [selectedTags, metric]);

  const { label, unit } = METRICS[metric];
  const metricHeader = `${label} [${unit}]`;
  const formatVal = (v: number | null | undefined, dec = 2) => v == null ? 'N/A' : v.toFixed(dec);

  const best = performers.bestPerformers.slice(0, 5);
  const worst = performers.worstPerformers.slice(0, 5);

  const renderTable = (data: PerformerData[], title: string, colorClass: string) => (
    <div>
      <Typography as="h4" className="mb-2">{title}</Typography>
      <div className="overflow-x-auto">
        <table className="w-full text-center text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-700">
            <tr>
              <th className="px-4 py-3">Traj-ID</th>
              <th className="px-4 py-3">{metricHeader}</th>
              <th className="px-4 py-3">Payload [kg]</th>
              <th className="px-4 py-3">Vel. [mm/s]</th>
              <th className="px-4 py-3">Accel. [mm/s²]</th>
              <th className="px-4 py-3">Setpoints</th>
              <th className="px-4 py-3">Stop [%]</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-500">No data available</td></tr>
            ) : (
              data.map((p) => (
                <tr key={p.traj_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/motion/${p.traj_id}`} className="font-medium text-blue-600 hover:underline">
                      {p.traj_id}
                    </Link>
                  </td>
                  <td className={`px-4 py-3 font-semibold ${colorClass}`}>{formatVal(p.metric_value, 3)}</td>
                  <td className="px-4 py-3">{p.weight ?? 'N/A'}</td>
                  <td className="px-4 py-3">{formatVal(p.max_velocity, 0)}</td>
                  <td className="px-4 py-3">{formatVal(p.max_acceleration, 0)}</td>
                  <td className="px-4 py-3">{p.waypoints ?? 'N/A'}</td>
                  <td className="px-4 py-3">{p.stop_point ?? 'N/A'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col justify-center space-y-8 rounded-2xl border border-gray-500 bg-white p-6">
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader className="size-8 animate-spin text-blue-950" />
        </div>
      ) : (
        <>
          {renderTable(best, 'The 5 best', 'text-green-600')}
          {renderTable(worst, 'The 5 worst', 'text-red-600')}
        </>
      )}
    </div>
  );
}
