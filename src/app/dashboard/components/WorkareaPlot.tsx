/* eslint-disable jsx-a11y/label-has-associated-control,react/button-has-type */

'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';

import { Typography } from '@/src/components/Typography';
import type { PerformerData } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WorkareaPoint { x: number; y: number; z: number; sidtw: number; tag: string }

interface Props {
  allPoints: WorkareaPoint[];
  selectedTags: string[];
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
}

const GREEN = ['#00ff00', '#00cc00', '#00aa00', '#008800', '#006600'];
const RED   = ['#ff0000', '#dd0000', '#bb0000', '#990000', '#770000'];

const workspaceBox = {
  x: [400,1900,1900,400,400,null,400,1900,1900,400,400,null,400,400,null,1900,1900,null,1900,1900,null,400,400],
  y: [-1100,-1100,1100,1100,-1100,null,-1100,-1100,1100,1100,-1100,null,-1100,-1100,null,-1100,-1100,null,1100,1100,null,1100,1100],
  z: [400,400,400,400,400,null,2000,2000,2000,2000,2000,null,400,2000,null,400,2000,null,400,2000,null,400,2000],
  mode: 'lines' as const, type: 'scatter3d' as const,
  line: { color: '#ff0000', width: 3 }, hoverinfo: 'skip' as const, showlegend: false,
};

export function WorkareaPlot({ allPoints, selectedTags, bestPerformers = [], worstPerformers = [] }: Props) {
  const [showBest, setShowBest] = useState(false);
  const [showWorst, setShowWorst] = useState(false);
  const [sidtwMin, setSidtwMin] = useState(0);
  const [sidtwMax, setSidtwMax] = useState(2);

  // Client-side tag filter — instant, no re-fetch
  const tagFiltered = useMemo(
    () => selectedTags.length > 0 ? allPoints.filter((p) => selectedTags.includes(p.tag)) : allPoints,
    [allPoints, selectedTags]
  );

  const minVal = tagFiltered.length > 0 ? Math.min(...tagFiltered.map((p) => p.sidtw)) : 0;
  const maxVal = tagFiltered.length > 0 ? Math.max(...tagFiltered.map((p) => p.sidtw)) : 2;

  // Reset slider to full range when tag selection changes so we always show all available points
  useEffect(() => { setSidtwMin(minVal); setSidtwMax(maxVal); }, [minVal, maxVal]);

  const clampedMin = Math.max(sidtwMin, minVal);
  const clampedMax = Math.min(sidtwMax, maxVal);
  const filtered = tagFiltered.filter((p) => p.sidtw >= clampedMin && p.sidtw <= clampedMax);

  const bestTraces = showBest ? bestPerformers.map((p, i) => ({
    x: (p.trajectory ?? []).map((t) => t.x),
    y: (p.trajectory ?? []).map((t) => t.y),
    z: (p.trajectory ?? []).map((t) => t.z),
    mode: 'lines' as const, type: 'scatter3d' as const,
    name: `Best #${i + 1} (ID: ${p.traj_id})`,
    line: { color: GREEN[i % GREEN.length], width: 4 },
    hovertemplate: `<b>Best #${i + 1}</b><br>ID: ${p.traj_id}<br>SIDTW: ${p.metric_value?.toFixed(3) ?? '—'} mm<br>X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>`,
  })) : [];

  const worstTraces = showWorst ? worstPerformers.map((p, i) => ({
    x: (p.trajectory ?? []).map((t) => t.x),
    y: (p.trajectory ?? []).map((t) => t.y),
    z: (p.trajectory ?? []).map((t) => t.z),
    mode: 'lines' as const, type: 'scatter3d' as const,
    name: `Worst #${i + 1} (ID: ${p.traj_id})`,
    line: { color: RED[i % RED.length], width: 4 },
    hovertemplate: `<b>Worst #${i + 1}</b><br>ID: ${p.traj_id}<br>SIDTW: ${p.metric_value?.toFixed(3) ?? '—'} mm<br>X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>`,
  })) : [];

  if (allPoints.length === 0) {
    return (
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
        <Typography as="h2" className="mb-2">Work area</Typography>
        <div className="flex h-96 items-center justify-center text-gray-500">No workarea data available</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
      <Typography as="h2" className="mb-2">Work area</Typography>

      <div className="mb-4 flex gap-4">
        <button
          onClick={() => setShowBest(!showBest)}
          className={`rounded-lg px-4 py-2 font-medium transition-colors ${showBest ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
        >
          {showBest ? '✓ ' : ''}Best performers
        </button>
        <button
          onClick={() => setShowWorst(!showWorst)}
          className={`rounded-lg px-4 py-2 font-medium transition-colors ${showWorst ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
        >
          {showWorst ? '✓ ' : ''}Worst performers
        </button>
      </div>

      <div className="mb-4">
        <label className="mb-2 block text-sm font-medium text-gray-700">
          SIDTW Range: {clampedMin.toFixed(3)} mm – {clampedMax.toFixed(3)} mm
        </label>
        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600">Minimum: {clampedMin.toFixed(3)} mm</label>
          <input type="range" min={minVal} max={maxVal} step={0.01} value={clampedMin}
            onChange={(e) => { const v = parseFloat(e.target.value); if (v <= clampedMax) setSidtwMin(v); }}
            className="w-full" />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600">Maximum: {clampedMax.toFixed(3)} mm</label>
          <input type="range" min={minVal} max={maxVal} step={0.01} value={clampedMax}
            onChange={(e) => { const v = parseFloat(e.target.value); if (v >= clampedMin) setSidtwMax(v); }}
            className="w-full" />
        </div>
        <div className="mt-1 flex justify-between text-xs text-gray-500">
          <span>{minVal.toFixed(3)} mm</span><span>{maxVal.toFixed(3)} mm</span>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          Showing {filtered.length.toLocaleString()} of {tagFiltered.length.toLocaleString()} points
          {selectedTags.length > 0 && ` (${allPoints.length.toLocaleString()} total)`}
        </p>
      </div>

      <Plot
        data={[
          {
            x: filtered.map((p) => p.x),
            y: filtered.map((p) => p.y),
            z: filtered.map((p) => p.z),
            mode: 'markers', type: 'scatter3d', name: 'Measurement points',
            marker: { size: 3, opacity: 0.5, color: filtered.map((p) => p.sidtw), colorscale: 'Inferno', showscale: true, colorbar: { title: 'SIDTW [mm]' } },
            hovertemplate: '<b>Position</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm<br>Z: %{z:.2f} mm<br>SIDTW: %{marker.color:.3f} mm<extra></extra>',
          },
          workspaceBox,
          ...bestTraces,
          ...worstTraces,
        ]}
        layout={{
          autosize: true, height: 550,
          scene: {
            xaxis: { title: { text: 'X [mm]' }, range: [0, 2300] },
            yaxis: { title: { text: 'Y [mm]' }, range: [-1300, 1300] },
            zaxis: { title: { text: 'Z [mm]' }, range: [0, 2000] },
          },
          margin: { t: 10, r: 10, l: 10, b: 10 },
          uirevision: 'true', showlegend: true,
          legend: { x: 0, y: 1, bgcolor: 'rgba(255,255,255,0.8)' },
        }}
        style={{ width: '100%' }}
        config={{ displaylogo: false, modeBarButtonsToRemove: ['toImage', 'orbitRotation', 'zoom3d', 'tableRotation', 'pan3d', 'resetCameraDefault3d'], responsive: true }}
      />
    </div>
  );
}
