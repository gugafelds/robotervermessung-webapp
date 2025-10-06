/* eslint-disable jsx-a11y/label-has-associated-control */

'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { Typography } from '@/src/components/Typography';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WorkareaPoint {
  x: number;
  y: number;
  z: number;
  sidtw: number;
}

interface WorkareaPlotProps {
  data: WorkareaPoint[];
}

export function WorkareaPlot({ data }: WorkareaPlotProps) {
  // Min/Max SIDTW für Slider berechnen
  const maxSidtw = Math.max(...data.map((p) => p.sidtw));
  const minSidtw = Math.min(...data.map((p) => p.sidtw));

  const [sidtwMin, setSidtwMin] = useState(minSidtw);
  const [sidtwMax, setSidtwMax] = useState(maxSidtw);

  // Initialisiere die Werte wenn die Daten sich ändern
  useEffect(() => {
    setSidtwMin(minSidtw);
    setSidtwMax(maxSidtw);
  }, [minSidtw, maxSidtw]);

  // Filtere Punkte basierend auf Min/Max Threshold
  const filteredData = data.filter(
    (p) => p.sidtw >= sidtwMin && p.sidtw <= sidtwMax,
  );

  // Arbeitsbereich-Würfel als Linien
  // Arbeitsbereich-Würfel als Linien
  const workspaceBox = {
    x: [
      // Untere Fläche
      400,
      1900,
      1900,
      400,
      400,
      null,
      // Obere Fläche
      400,
      1900,
      1900,
      400,
      400,
      null,
      // Vertikale Verbindungen
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
      // Untere Fläche
      -1100,
      -1100,
      1100,
      1100,
      -1100,
      null,
      // Obere Fläche
      -1100,
      -1100,
      1100,
      1100,
      -1100,
      null,
      // Vertikale Verbindungen
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
      // Untere Fläche
      400,
      400,
      400,
      400,
      400,
      null,
      // Obere Fläche
      2000,
      2000,
      2000,
      2000,
      2000,
      null,
      // Vertikale Verbindungen
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
    line: {
      color: '#ff0000',
      width: 3,
    },
    hoverinfo: 'skip' as const,
    showlegend: false,
  };

  return (
    <div className="rounded-2xl bg-white p-6 shadow">
      <Typography as="h3" className="mb-4">
        Arbeitsraum-Erkundung
      </Typography>

      {/* Range-Slider für SIDTW Threshold */}
      <div className="mb-4">
        <label className="mb-2 block text-sm font-medium text-gray-700">
          SIDTW Bereich: {sidtwMin.toFixed(3)} mm - {sidtwMax.toFixed(3)} mm
        </label>

        {/* Minimum Slider */}
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

        {/* Maximum Slider */}
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
          },
          // Arbeitsbereich-Würfel
          workspaceBox,
        ]}
        layout={{
          autosize: true,
          height: 600,
          scene: {
            xaxis: { title: 'X [mm]', range: [0, 2300] },
            yaxis: { title: 'Y [mm]', range: [-1300, 1300] },
            zaxis: { title: 'Z [mm]', range: [0, 2000] },
          },
          margin: { t: 10, r: 10, l: 10, b: 10 },
          uirevision: 'true',
        }}
        style={{ width: '100%' }}
        config={{ responsive: true }}
      />
    </div>
  );
}
