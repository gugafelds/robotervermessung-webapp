'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';

import { getWorkareaByTag } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WorkareaPoint { x: number; y: number; z: number; sidtw: number; tag: string }
interface Bounds { x_min: number; x_max: number; y_min: number; y_max: number; z_min: number; z_max: number }

interface Props {
  selectedTags: string[];
}

function makeWorkspaceBox(b: Bounds) {
  const { x_min: x0, x_max: x1, y_min: y0, y_max: y1, z_min: z0, z_max: z1 } = b;
  return {
    x: [x0,x1,x1,x0,x0,null,x0,x1,x1,x0,x0,null,x0,x0,null,x1,x1,null,x1,x1,null,x0,x0],
    y: [y0,y0,y1,y1,y0,null,y0,y0,y1,y1,y0,null,y0,y0,null,y0,y0,null,y1,y1,null,y1,y1],
    z: [z0,z0,z0,z0,z0,null,z1,z1,z1,z1,z1,null,z0,z1,null,z0,z1,null,z0,z1,null,z0,z1],
    mode: 'lines' as const, type: 'scatter3d' as const,
    line: { color: '#3b82f6', width: 2 }, hoverinfo: 'skip' as const, showlegend: false,
    name: 'Workspace',
  };
}

export function WorkareaPlot({ selectedTags }: Props) {
  const [points, setPoints] = useState<WorkareaPoint[]>([]);
  const [bounds, setBounds] = useState<Bounds | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [loadedFor, setLoadedFor] = useState<string[]>([]);

  const handleLoad = async () => {
    if (selectedTags.length === 0) return;
    setLoading(true);
    const res = await getWorkareaByTag(selectedTags) as { points: WorkareaPoint[]; bounds: Bounds | null };
    setPoints(res.points ?? []);
    setBounds(res.bounds ?? null);
    setLoaded(true);
    setLoadedFor([...selectedTags]);
    setLoading(false);
  };

  const tagsChanged = loaded && JSON.stringify([...loadedFor].sort()) !== JSON.stringify([...selectedTags].sort());

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const traces: any[] = [];
  if (points.length > 0) {
    traces.push({
      x: points.map((p) => p.x),
      y: points.map((p) => p.y),
      z: points.map((p) => p.z),
      mode: 'markers', type: 'scatter3d', name: 'Setpoints',
      marker: {
        size: 4, opacity: 0.7,
        color: points.map((p) => p.sidtw),
        colorscale: 'Inferno', showscale: true,
        colorbar: { title: 'SIDTW [mm]', thickness: 14 },
      },
      hovertemplate: 'X: %{x:.1f}<br>Y: %{y:.1f}<br>Z: %{z:.1f}<br>SIDTW: %{marker.color:.3f} mm<extra></extra>',
    });
  }
  if (bounds) traces.push(makeWorkspaceBox(bounds));

  return (
    <div className="flex flex-col rounded-2xl border border-gray-200 bg-white p-4">
      <Typography as="h2" className="mb-3">Work area</Typography>

      <div className="mb-4 flex items-center gap-3">
        <button
          type="button"
          onClick={handleLoad}
          disabled={loading || selectedTags.length === 0}
          className="rounded-lg bg-blue-950 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? 'Loading…' : 'Load data'}
        </button>
        {selectedTags.length === 0 && (
          <span className="text-sm text-gray-400">Select a tag first</span>
        )}
        {tagsChanged && !loading && (
          <span className="text-sm text-amber-600">Tag selection changed — reload to update</span>
        )}
        {loaded && !tagsChanged && points.length > 0 && (
          <span className="text-sm text-gray-500">{points.length.toLocaleString()} setpoints</span>
        )}
      </div>

      {!loaded ? (
        <div className="flex h-96 items-center justify-center rounded-xl border border-dashed border-gray-300 text-sm text-gray-400">
          Select tag(s) and click &quot;Load data&quot;
        </div>
      ) : points.length === 0 ? (
        <div className="flex h-96 items-center justify-center text-sm text-gray-400">No data for selected tag(s)</div>
      ) : (
        <Plot
          data={traces}
          layout={{
            autosize: true, height: 560,
            scene: {
              xaxis: { title: { text: 'X [mm]' } },
              yaxis: { title: { text: 'Y [mm]' } },
              zaxis: { title: { text: 'Z [mm]' } },
            },
            margin: { t: 10, r: 10, l: 10, b: 10 },
            uirevision: loadedFor.join(','),
            showlegend: false,
          }}
          style={{ width: '100%' }}
          config={{ displaylogo: false, responsive: true }}
        />
      )}
    </div>
  );
}
