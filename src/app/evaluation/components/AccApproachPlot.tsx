'use client';

import dynamic from 'next/dynamic';
import type { Config, Layout, PlotData } from 'plotly.js';
import React, { useMemo } from 'react';

import type { AccApproach, AccPosition } from '@/types/evaluation.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// same palette as the deviation plots; further colors for more segments
export const segmentColors = [
  '#003560',
  '#e63946',
  '#2a9d8f',
  '#f4a261',
  '#6a4c93',
];
const REST_SPEED = 5; // mm/s, as in evaluation.acc_position

export const plotConfig: Partial<Config> = {
  displaylogo: false,
  modeBarButtonsToRemove: [
    'toImage',
    'orbitRotation',
    'lasso2d',
    'zoomIn2d',
    'zoomOut2d',
    'autoScale2d',
    'pan2d',
    'select2d',
  ],
  responsive: true,
};

interface AccApproachPlotProps {
  selectedSegment: string;
  approach: AccApproach[];
  rows: AccPosition[]; // segment rows of the table
}

// Distance to the programmed target over time around the segment end: where the robot passes, where it stops (Δp)
// and which moment SIDTW at end looks at
export const AccApproachPlot: React.FC<AccApproachPlotProps> = ({
  selectedSegment,
  approach,
  rows,
}) => {
  const single = selectedSegment !== 'total';
  const shown = single
    ? approach.filter((a) => a.segmentID === selectedSegment)
    : approach;

  const plotData = useMemo((): Partial<PlotData>[] => {
    const traces: Partial<PlotData>[] = [];
    shown.forEach((a) => {
      const k = Number(a.segmentID.split('_')[1]) - 1;
      const color = segmentColors[k % segmentColors.length];
      const row = rows.find((r) => r.segmentID === a.segmentID);
      traces.push({
        type: 'scatter',
        mode: 'lines',
        name: `Segment ${k + 1}`,
        x: a.t,
        y: a.distance,
        line: { color, width: 2 },
        hovertemplate: `Segment ${k + 1}<br>Time: %{x:.3f} s<br>Distance: %{y:.3f} mm<extra></extra>`,
      });
      // samples at rest (measured speed < 5 mm/s): the ones averaged for Δp in rest mode
      const rest = a.t
        .map((t, i) => ({ t, y: a.distance[i], v: a.speed[i] }))
        .filter((s) => s.v != null && s.v < REST_SPEED);
      if (rest.length) {
        traces.push({
          type: 'scatter',
          mode: 'markers',
          name: `Rest (< ${REST_SPEED} mm/s)`,
          legendgroup: 'rest',
          showlegend: traces.every((tr) => tr.legendgroup !== 'rest'),
          x: rest.map((s) => s.t),
          y: rest.map((s) => s.y),
          marker: { color: '#2e7d32', size: 3 },
          hovertemplate:
            'Rest<br>Time: %{x:.3f} s<br>Distance: %{y:.3f} mm<extra></extra>',
        });
      }
      if (row) {
        // the table's point: middle of the rest phase, or the closest sample
        const iMin = a.distance.indexOf(Math.min(...a.distance));
        const restMid = rest.length
          ? rest.reduce((sum, s) => sum + s.t, 0) / rest.length
          : 0;
        traces.push({
          type: 'scatter',
          mode: 'markers',
          name: 'Δp (table)',
          legendgroup: 'dp',
          showlegend: traces.every((tr) => tr.legendgroup !== 'dp'),
          x: [row.posMode === 'rest' ? restMid : a.t[iMin]],
          y: [row.p],
          marker: {
            color,
            size: 10,
            symbol: 'diamond',
            line: { color: '#000', width: 1 },
          },
          hovertemplate: `Segment ${k + 1} (${row.posMode})<br>Δp: %{y:.3f} mm<extra></extra>`,
        });
      }
      if (a.sidtwT != null && a.sidtwDistance != null) {
        // measured point of the segment's last SIDTW pair: the moment 'SIDTW at end' refers to
        traces.push({
          type: 'scatter',
          mode: 'markers',
          name: 'SIDTW at end (pair)',
          legendgroup: 'sidtw',
          showlegend: traces.every((tr) => tr.legendgroup !== 'sidtw'),
          x: [a.sidtwT],
          y: [a.sidtwDistance],
          marker: {
            color: '#fff',
            size: 11,
            symbol: 'circle',
            line: { color, width: 2 },
          },
          hovertemplate: `Segment ${k + 1}: last SIDTW pair<br>Measured point to target: %{y:.3f} mm<br>SIDTW deviation: ${a.sidtwDeviation?.toFixed(3) ?? '-'} mm<extra></extra>`,
        });
      }
    });
    return traces;
  }, [shown, rows]);

  if (!shown.length) return null;

  // zoomed to the target region (the curves leave it while the robot is still far away)
  const m =
    2.5 *
    Math.max(
      ...shown.map((a) =>
        Math.max(
          rows.find((r) => r.segmentID === a.segmentID)?.p ?? 0,
          a.sidtwDistance ?? 0,
        ),
      ),
      0.1,
    );
  const layout: Partial<Layout> = {
    title: {
      text: single
        ? `Approach to target (Segment ${selectedSegment.split('_')[1]})`
        : 'Approach to target (Trajectory)',
    },
    font: { family: 'Helvetica' },
    xaxis: { title: { text: 'Time relative to segment end [s]' } },
    yaxis: {
      title: { text: 'Distance to target [mm]' },
      range: [0, m],
    },
    hovermode: 'closest',
    height: 450,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
  };

  return (
    <div className="w-full rounded-lg border border-gray-500 bg-white p-4">
      <Plot
        data={plotData}
        layout={layout}
        useResizeHandler
        config={plotConfig}
        style={{ width: '100%', height: '450px' }}
      />
    </div>
  );
};
