/* eslint-disable react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getSIDTWTimeline } from '@/src/actions/dashboard.service';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TimelineDataPoint {
  date: string;
  avg_sidtw: number;
  min_sidtw: number;
  max_sidtw: number;
  count: number;
}

// Content Komponente
interface AccuracyTimelineContentProps {
  data: TimelineDataPoint[];
}

function AccuracyTimelineContent({ data }: AccuracyTimelineContentProps) {
  // Daten für den Plot vorbereiten
  const dates = data.map((d) => d.date);
  const avgValues = data.map((d) => d.avg_sidtw);
  const minValues = data.map((d) => d.min_sidtw);
  const maxValues = data.map((d) => d.max_sidtw);

  return (
    <div className="rounded-2xl bg-white p-6 shadow">
      <div className="mb-4 text-sm text-gray-600">
        <p>
          Dieser Plot zeigt die Entwicklung der Messgenauigkeit über die Zeit.
          Ein Anstieg könnte auf Verschleiß oder Kalibrierungsprobleme
          hinweisen.
        </p>
      </div>

      <Plot
        data={[
          // Durchschnittswerte (Hauptlinie)
          {
            x: dates,
            y: avgValues,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Durchschnitt',
            line: { color: '#003560', width: 3 },
            marker: { size: 6 },
            hovertemplate:
              '<b>Durchschnitt SIDTW</b><br>' +
              'Datum: %{x}<br>' +
              'SIDTW: %{y:.3f} mm<br>' +
              '<extra></extra>',
          },
          // Min-Werte (untere Grenze)
          {
            x: dates,
            y: minValues,
            type: 'scatter',
            mode: 'lines',
            name: 'Minimum',
            line: { color: '#10b981', width: 2, dash: 'dash' },
            hovertemplate:
              '<b>Minimum SIDTW</b><br>' +
              'Datum: %{x}<br>' +
              'SIDTW: %{y:.3f} mm<br>' +
              '<extra></extra>',
          },
          // Max-Werte (obere Grenze)
          {
            x: dates,
            y: maxValues,
            type: 'scatter',
            mode: 'lines',
            name: 'Maximum',
            line: { color: '#ef4444', width: 2, dash: 'dash' },
            hovertemplate:
              '<b>Maximum SIDTW</b><br>' +
              'Datum: %{x}<br>' +
              'SIDTW: %{y:.3f} mm<br>' +
              '<extra></extra>',
          },
        ]}
        layout={{
          autosize: true,
          height: 400,
          margin: { t: 20, r: 20, l: 80, b: 80 },
          xaxis: {
            title: 'Aufnahmedatum',
            type: 'date',
            tickformat: '%d.%m.%Y',
          },
          yaxis: {
            title: 'SIDTW [mm]',
            rangemode: 'tozero',
          },
          hovermode: 'x unified',
          showlegend: true,
          legend: {
            x: 0.8,
            y: 0.98,
            bgcolor: 'rgba(255,255,255,0.8)',
          },
        }}
        style={{ width: '100%' }}
        config={{
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'lasso2d',
            'zoomIn2d',
            'zoomOut2d',
            'autoScale2d',
            'pan2d',
          ],
        }}
      />

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg bg-blue-50 p-4">
          <p className="text-sm text-gray-600">Gesamtmessungen</p>
          <p className="text-2xl font-bold text-blue-950">
            {data.reduce((sum, d) => sum + d.count, 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg bg-green-50 p-4">
          <p className="text-sm text-gray-600">Bester Durchschnitt</p>
          <p className="text-2xl font-bold text-green-700">
            {Math.min(...avgValues).toFixed(3)} mm
          </p>
        </div>
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-sm text-gray-600">Schlechtester Durchschnitt</p>
          <p className="text-2xl font-bold text-red-700">
            {Math.max(...avgValues).toFixed(3)} mm
          </p>
        </div>
      </div>
    </div>
  );
}

// Haupt-Komponente mit Loading States
export function AccuracyTimeline() {
  const [data, setData] = useState<TimelineDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimelineData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await getSIDTWTimeline();
        setData(result.timeline || []);
      } catch (err) {
        setError('Fehler beim Laden der Zeitreihen-Daten');
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTimelineData();
  }, []);

  // Loading State
  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <div className="flex h-96 items-center justify-center">
          <div className="text-center">
            <Loader className="mx-auto mb-4 size-12 animate-spin text-blue-950" />
            <p className="text-sm text-gray-600">Lade Zeitreihen-Daten...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
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

  // Empty State
  if (data.length === 0) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <div className="flex h-96 items-center justify-center">
          <p className="text-gray-600">Keine Zeitreihen-Daten verfügbar</p>
        </div>
      </div>
    );
  }

  return <AccuracyTimelineContent data={data} />;
}
