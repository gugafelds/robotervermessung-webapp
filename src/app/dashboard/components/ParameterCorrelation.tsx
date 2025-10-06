/* eslint-disable react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getSIDTWvsParameters } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type ParameterType = 'velocity' | 'acceleration' | 'weight';

interface ParameterData {
  sidtw: number;
  velocity: number;
  acceleration: number;
  weight: number;
}

interface ParameterConfig {
  id: ParameterType;
  label: string;
  unit: string;
  xLabel: string;
}

// Content Komponente ZUERST definiert
interface ParameterCorrelationContentProps {
  data: ParameterData[];
  activeParam: ParameterType;
  setActiveParam: (param: ParameterType) => void;
}

function ParameterCorrelationContent({
  data,
  activeParam,
  setActiveParam,
}: ParameterCorrelationContentProps) {
  const parameters: ParameterConfig[] = [
    {
      id: 'velocity',
      label: 'Geschwindigkeit',
      unit: 'mm/s',
      xLabel: 'Max. Geschwindigkeit (Twist Ist)',
    },
    {
      id: 'acceleration',
      label: 'Beschleunigung',
      unit: 'mm/s²',
      xLabel: 'Max. Beschleunigung (Accel Ist)',
    },
    {
      id: 'weight',
      label: 'Last',
      unit: 'kg',
      xLabel: 'Last',
    },
  ];

  const activeConfig = parameters.find((p) => p.id === activeParam)!;
  const xValues = data.map((d) => d[activeParam]);
  const yValues = data.map((d) => d.sidtw);

  // Berechne einfache Korrelation
  const calculateCorrelation = (x: number[], y: number[]) => {
    const n = x.length;
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((acc, xi, i) => acc + xi * y[i], 0);
    const sumX2 = x.reduce((acc, xi) => acc + xi * xi, 0);
    const sumY2 = y.reduce((acc, yi) => acc + yi * yi, 0);

    const numerator = n * sumXY - sumX * sumY;
    const denominator = Math.sqrt(
      (n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY),
    );

    return denominator === 0 ? 0 : numerator / denominator;
  };

  const correlation = calculateCorrelation(xValues, yValues);

  return (
    <div className="rounded-2xl bg-white p-6 shadow">
      <Typography as="h3" className="mb-4">
        SIDTW vs. Bewegungsparameter
      </Typography>

      <div className="mb-4 text-sm text-gray-600">
        <p>
          Diese Scatter-Plots zeigen den Zusammenhang zwischen SIDTW-Genauigkeit
          und Bewegungsparametern. Eine Stichprobe von{' '}
          {data.length.toLocaleString()} repräsentativen Bahnen (Leica AT960)
          wird analysiert.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 flex flex-wrap gap-2 border-b">
        {parameters.map((param) => (
          <button
            key={param.id}
            onClick={() => setActiveParam(param.id)}
            className={`px-4 py-2 font-medium transition-colors ${
              activeParam === param.id
                ? 'border-b-2 border-primary text-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {param.label}
          </button>
        ))}
      </div>

      {/* Scatter Plot */}
      <Plot
        data={[
          {
            x: xValues,
            y: yValues,
            type: 'scatter',
            mode: 'markers',
            name: 'Messungen',
            marker: {
              size: 6,
              color: yValues,
              colorscale: 'Viridis',
              showscale: true,
              colorbar: {
                title: 'SIDTW [mm]',
              },
              opacity: 0.6,
            },
            hovertemplate:
              `<b>${activeConfig.xLabel}</b><br>` +
              `${activeConfig.label}: %{x:.2f} ${activeConfig.unit}<br>` +
              'SIDTW: %{y:.3f} mm<br>' +
              '<extra></extra>',
          },
        ]}
        layout={{
          autosize: true,
          height: 500,
          margin: { t: 20, r: 20, l: 80, b: 80 },
          xaxis: {
            title: `${activeConfig.xLabel} [${activeConfig.unit}]`,
          },
          yaxis: {
            title: 'SIDTW [mm]',
          },
          hovermode: 'closest',
          showlegend: false,
        }}
        style={{ width: '100%' }}
        config={{
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        }}
      />

      {/* Statistiken */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg bg-blue-50 p-4">
          <p className="text-sm text-gray-600">Datenpunkte (Stichprobe)</p>
          <p className="text-2xl font-bold text-blue-950">
            {data.length.toLocaleString()}
          </p>
        </div>
        <div
          className={`rounded-lg p-4 ${
            Math.abs(correlation) > 0.5
              ? 'bg-orange-50'
              : Math.abs(correlation) > 0.3
                ? 'bg-yellow-50'
                : 'bg-green-50'
          }`}
        >
          <p className="text-sm text-gray-600">Korrelation</p>
          <p
            className={`text-2xl font-bold ${
              Math.abs(correlation) > 0.5
                ? 'text-orange-700'
                : Math.abs(correlation) > 0.3
                  ? 'text-yellow-700'
                  : 'text-green-700'
            }`}
          >
            {correlation.toFixed(3)}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {Math.abs(correlation) > 0.5
              ? 'Starker Zusammenhang'
              : Math.abs(correlation) > 0.3
                ? 'Mittlerer Zusammenhang'
                : 'Schwacher Zusammenhang'}
          </p>
        </div>
        <div className="rounded-lg bg-purple-50 p-4">
          <p className="text-sm text-gray-600">Durchschn. SIDTW</p>
          <p className="text-2xl font-bold text-purple-700">
            {(yValues.reduce((a, b) => a + b, 0) / yValues.length).toFixed(3)}{' '}
            mm
          </p>
        </div>
      </div>
    </div>
  );
}

// Haupt-Komponente DANACH definiert
export function ParameterCorrelation() {
  const [data, setData] = useState<ParameterData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeParam, setActiveParam] = useState<ParameterType>('velocity');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await getSIDTWvsParameters();
        setData(result.data || []);
      } catch (err) {
        console.error('Error loading parameter data:', err);
        setError('Fehler beim Laden der Parameter-Daten');
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Loading State
  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <Typography as="h3" className="mb-4">
          SIDTW vs. Bewegungsparameter
        </Typography>
        <div className="flex h-96 items-center justify-center">
          <div className="text-center">
            <Loader className="mx-auto mb-4 size-12 animate-spin text-blue-950" />
            <p className="text-sm text-gray-600">Lade Parameter-Daten...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow">
        <Typography as="h3" className="mb-4">
          SIDTW vs. Bewegungsparameter
        </Typography>
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
        <Typography as="h3" className="mb-4">
          SIDTW vs. Bewegungsparameter
        </Typography>
        <div className="flex h-96 items-center justify-center">
          <p className="text-gray-600">Keine Parameter-Daten verfügbar</p>
        </div>
      </div>
    );
  }

  return (
    <ParameterCorrelationContent
      data={data}
      activeParam={activeParam}
      setActiveParam={setActiveParam}
    />
  );
}
