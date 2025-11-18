/* eslint-disable jsx-a11y/label-has-associated-control,react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getWorkareaData } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';
import type { PerformerData } from '@/types/dashboard.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WorkareaPoint {
  x: number;
  y: number;
  z: number;
  sidtw: number;
}

interface WorkareaPlotProps {
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
}

// Separate Komponente für den eigentlichen Plot
function WorkareaPlotContent({
  data,
  bestPerformers = [],
  worstPerformers = [],
}: {
  data: WorkareaPoint[];
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
}) {
  const maxSidtw = Math.max(...data.map((p) => p.sidtw));
  const minSidtw = Math.min(...data.map((p) => p.sidtw));

  const [sidtwMin, setSidtwMin] = useState(minSidtw);
  const [sidtwMax, setSidtwMax] = useState(maxSidtw);
  const [showBest, setShowBest] = useState(false);
  const [showWorst, setShowWorst] = useState(false);

  useEffect(() => {
    setSidtwMin(minSidtw);
    setSidtwMax(maxSidtw);
  }, [minSidtw, maxSidtw]);

  const filteredData = data.filter(
    (p) => p.sidtw >= sidtwMin && p.sidtw <= sidtwMax,
  );

  // Arbeitsbereich-Würfel
  const workspaceBox = {
    x: [
      400,
      1900,
      1900,
      400,
      400,
      null,
      400,
      1900,
      1900,
      400,
      400,
      null,
      400,
      400,
      null,
      1900,
      1900,
      null,
      1900,
      1900,
      null,
      400,
      400,
    ],
    y: [
      -1100,
      -1100,
      1100,
      1100,
      -1100,
      null,
      -1100,
      -1100,
      1100,
      1100,
      -1100,
      null,
      -1100,
      -1100,
      null,
      -1100,
      -1100,
      null,
      1100,
      1100,
      null,
      1100,
      1100,
    ],
    z: [
      400,
      400,
      400,
      400,
      400,
      null,
      2000,
      2000,
      2000,
      2000,
      2000,
      null,
      400,
      2000,
      null,
      400,
      2000,
      null,
      400,
      2000,
      null,
      400,
      2000,
    ],
    mode: 'lines' as const,
    type: 'scatter3d' as const,
    line: { color: '#ff0000', width: 3 },
    hoverinfo: 'skip' as const,
    showlegend: false,
  };

  // Generiere Grün-Töne für Best Performers
  const greenColors = [
    '#00ff00', // Bright green
    '#00cc00', // Medium green
    '#00aa00', // Green
    '#008800', // Dark green
    '#006600', // Darker green
  ];

  // Generiere Rot-Töne für Worst Performers
  const redColors = [
    '#ff0000', // Bright red
    '#dd0000', // Medium red
    '#bb0000', // Red
    '#990000', // Dark red
    '#770000', // Darker red
  ];

  // Best Performers Trajektorien
  const bestTrajectories = showBest
    ? bestPerformers.map((performer, idx) => ({
        x: performer.trajectory.map((p) => p.x),
        y: performer.trajectory.map((p) => p.y),
        z: performer.trajectory.map((p) => p.z),
        mode: 'lines' as const,
        type: 'scatter3d' as const,
        name: `Best #${idx + 1} (ID: ${performer.bahn_id})`,
        line: {
          color: greenColors[idx % greenColors.length],
          width: 4,
        },
        hovertemplate:
          `<b>Best Performer #${idx + 1}</b><br>` +
          `Bahn-ID: ${performer.bahn_id}<br>` +
          `SIDTW: ${performer.sidtw_average_distance.toFixed(3)} mm<br>` +
          'X: %{x:.2f} mm<br>' +
          'Y: %{y:.2f} mm<br>' +
          'Z: %{z:.2f} mm' +
          '<extra></extra>',
      }))
    : [];

  // Worst Performers Trajektorien
  const worstTrajectories = showWorst
    ? worstPerformers.map((performer, idx) => ({
        x: performer.trajectory.map((p) => p.x),
        y: performer.trajectory.map((p) => p.y),
        z: performer.trajectory.map((p) => p.z),
        mode: 'lines' as const,
        type: 'scatter3d' as const,
        name: `Worst #${idx + 1} (ID: ${performer.bahn_id})`,
        line: {
          color: redColors[idx % redColors.length],
          width: 4,
        },
        hovertemplate:
          `<b>Worst Performer #${idx + 1}</b><br>` +
          `Bahn-ID: ${performer.bahn_id}<br>` +
          `SIDTW: ${performer.sidtw_average_distance.toFixed(3)} mm<br>` +
          'X: %{x:.2f} mm<br>' +
          'Y: %{y:.2f} mm<br>' +
          'Z: %{z:.2f} mm' +
          '<extra></extra>',
      }))
    : [];

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
      <Typography as="h2" className="mb-2">
        Arbeitsraum
      </Typography>
      {/* Toggle Buttons für Trajektorien */}
      <div className="mb-4 flex gap-4">
        <button
          onClick={() => setShowBest(!showBest)}
          className={`rounded-lg px-4 py-2 font-medium transition-colors ${
            showBest
              ? 'bg-green-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {showBest ? '✓' : ''} Best Performers
        </button>
        <button
          onClick={() => setShowWorst(!showWorst)}
          className={`rounded-lg px-4 py-2 font-medium transition-colors ${
            showWorst
              ? 'bg-red-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {showWorst ? '✓' : ''} Worst Performers
        </button>
      </div>

      {/* Range-Slider für SIDTW Threshold */}
      <div className="mb-4">
        <label className="mb-2 block text-sm font-medium text-gray-700">
          SIDTW Bereich: {sidtwMin.toFixed(3)} mm - {sidtwMax.toFixed(3)} mm
        </label>

        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600">
            Minimum: {sidtwMin.toFixed(3)} mm
          </label>
          <input
            type="range"
            min={minSidtw}
            max={maxSidtw}
            step={0.01}
            value={sidtwMin}
            onChange={(e) => {
              const newMin = parseFloat(e.target.value);
              if (newMin <= sidtwMax) {
                setSidtwMin(newMin);
              }
            }}
            className="w-full"
          />
        </div>

        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600">
            Maximum: {sidtwMax.toFixed(3)} mm
          </label>
          <input
            type="range"
            min={minSidtw}
            max={maxSidtw}
            step={0.01}
            value={sidtwMax}
            onChange={(e) => {
              const newMax = parseFloat(e.target.value);
              if (newMax >= sidtwMin) {
                setSidtwMax(newMax);
              }
            }}
            className="w-full"
          />
        </div>

        <div className="mt-1 flex justify-between text-xs text-gray-500">
          <span>{minSidtw.toFixed(3)} mm</span>
          <span>{maxSidtw.toFixed(3)} mm</span>
        </div>
        <p className="mt-2 text-sm text-gray-600">
          Zeige {filteredData.length.toLocaleString()} von{' '}
          {data.length.toLocaleString()} Punkten
        </p>
      </div>

      <Plot
        data={[
          // Datenpunkte
          {
            x: filteredData.map((p) => p.x),
            y: filteredData.map((p) => p.y),
            z: filteredData.map((p) => p.z),
            mode: 'markers',
            type: 'scatter3d',
            name: 'Messpunkte',
            marker: {
              size: 3,
              opacity: 0.5,
              color: filteredData.map((p) => p.sidtw),
              colorscale: 'Inferno',
              showscale: true,
              colorbar: {
                title: 'SIDTW [mm]',
              },
            },
            hovertemplate:
              '<b>Position</b><br>' +
              'X: %{x:.2f} mm<br>' +
              'Y: %{y:.2f} mm<br>' +
              'Z: %{z:.2f} mm<br>' +
              'SIDTW: %{marker.color:.3f} mm' +
              '<extra></extra>',
          },
          // Arbeitsbereich-Würfel
          workspaceBox,
          // Best Performer Trajektorien
          ...bestTrajectories,
          // Worst Performer Trajektorien
          ...worstTrajectories,
        ]}
        layout={{
          autosize: true,
          height: 550,
          scene: {
            xaxis: { title: 'X [mm]', range: [0, 2300] },
            yaxis: { title: 'Y [mm]', range: [-1300, 1300] },
            zaxis: { title: 'Z [mm]', range: [0, 2000] },
          },
          margin: { t: 10, r: 10, l: 10, b: 10 },
          uirevision: 'true',
          showlegend: true,
          legend: {
            x: 0,
            y: 1,
            bgcolor: 'rgba(255, 255, 255, 0.8)',
          },
        }}
        style={{ width: '100%' }}
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'zoom3d',
            'tableRotation',
            'pan3d',
            'resetCameraDefault3d',
          ],
          responsive: true,
        }}
      />
    </div>
  );
}

export function WorkareaPlot({
  bestPerformers,
  worstPerformers,
}: WorkareaPlotProps) {
  const [data, setData] = useState<WorkareaPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWorkareaData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await getWorkareaData();
        setData(result.points || []);
      } catch (err) {
        setError('Fehler beim Laden der Arbeitsraum-Daten');
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkareaData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
        <div className="flex h-96 items-center justify-center">
          <div className="text-center">
            <Loader className="mx-auto mb-4 size-12 animate-spin text-blue-950" />
            <p className="text-sm text-gray-600">Lade Arbeitsraum-Daten...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
        <div className="flex h-96 items-center justify-center">
          <div className="text-center text-red-600">
            <p className="mb-2 text-lg font-semibold">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-md bg-blue-950 px-4 py-2 text-white hover:bg-blue-900"
            >
              Seite neu laden
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-4">
        <Typography as="h3" className="mb-4">
          Arbeitsraum-Erkundung
        </Typography>
        <div className="flex h-96 items-center justify-center">
          <p className="text-gray-600">Keine Arbeitsraum-Daten verfügbar</p>
        </div>
      </div>
    );
  }

  return (
    <WorkareaPlotContent
      data={data}
      bestPerformers={bestPerformers}
      worstPerformers={worstPerformers}
    />
  );
}
