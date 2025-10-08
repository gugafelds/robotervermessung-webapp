/* eslint-disable react/button-has-type */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

import { getSIDTWvsParameters } from '@/src/actions/dashboard.service';
import { Typography } from '@/src/components/Typography';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type ParameterType =
  | 'velocity'
  | 'acceleration'
  | 'weight'
  | 'stop_point'
  | 'wait_time';

interface ParameterData {
  sidtw: number;
  velocity: number;
  acceleration: number;
  weight: number;
  stop_point: number;
  wait_time: number;
}

interface ParameterConfig {
  id: ParameterType;
  label: string;
  unit: string;
  xLabel: string;
  numBins: number;
}

interface BinnedData {
  binLabel: string;
  sidtwValues: number[];
  count: number;
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
      xLabel: 'Geschwindigkeitsbereich',
      numBins: 10,
    },
    {
      id: 'acceleration',
      label: 'Beschleunigung',
      unit: 'mm/s²',
      xLabel: 'Beschleunigungsbereich',
      numBins: 10,
    },
    {
      id: 'weight',
      label: 'Last',
      unit: 'kg',
      xLabel: 'Lastbereich',
      numBins: 6,
    },
    {
      id: 'stop_point',
      label: 'Stopp-Punkte',
      unit: '%',
      xLabel: 'Stopp-Punkte Bereich',
      numBins: 100,
    },
    {
      id: 'wait_time',
      label: 'Wartezeit',
      unit: 's',
      xLabel: 'Wartezeit Bereich',
      numBins: 6,
    },
  ];

  const activeConfig = parameters.find((p) => p.id === activeParam)!;

  // Binning-Funktion
  const createBins = (paramValues: number[], numBins: number): BinnedData[] => {
    const min = Math.min(...paramValues);
    const max = Math.max(...paramValues);
    const binWidth = (max - min) / numBins;

    const bins: BinnedData[] = [];

    for (let i = 0; i < numBins; i++) {
      const binMin = min + i * binWidth;
      const binMax = min + (i + 1) * binWidth;
      const binLabel = `${binMin.toFixed(1)}-${binMax.toFixed(1)}`;

      const sidtwInBin = data
        .filter((d) => {
          const val = d[activeParam];
          return i === numBins - 1
            ? val >= binMin && val <= binMax
            : val >= binMin && val < binMax;
        })
        .map((d) => d.sidtw);

      if (sidtwInBin.length > 0) {
        bins.push({
          binLabel,
          sidtwValues: sidtwInBin,
          count: sidtwInBin.length,
        });
      }
    }

    return bins;
  };

  const paramValues = data.map((d) => d[activeParam]);
  const binnedData = createBins(paramValues, activeConfig.numBins);

  // Berechne Statistiken für beste/schlechteste Bereiche
  const binMedians = binnedData.map((bin) => {
    const sorted = [...bin.sidtwValues].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  });

  const bestBinIndex = binMedians.indexOf(Math.min(...binMedians));
  const worstBinIndex = binMedians.indexOf(Math.max(...binMedians));

  return (
    <div className="rounded-2xl bg-white p-6 shadow">
      <Typography as="h3" className="mb-4">
        SIDTW-Verteilung nach Bewegungsparametern
      </Typography>

      <div className="mb-4 text-sm text-gray-600">
        <p>
          Box Plots zeigen die SIDTW-Verteilung für verschiedene
          Parameter-Bereiche. Eine Stichprobe von {data.length.toLocaleString()}{' '}
          repräsentativen Bahnen (Leica AT960).
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

      {/* Box Plot */}
      <Plot
        data={binnedData.map((bin, idx) => ({
          y: bin.sidtwValues,
          type: 'box',
          name: bin.binLabel,
          marker: {
            color:
              idx === bestBinIndex
                ? '#10b981'
                : idx === worstBinIndex
                  ? '#ef4444'
                  : '#003560',
          },
          boxmean: 'sd',
        }))}
        layout={{
          autosize: true,
          height: 500,
          margin: { t: 20, r: 20, l: 80, b: 120 },
          xaxis: {
            title: `${activeConfig.xLabel} [${activeConfig.unit}]`,
            tickangle: -45,
          },
          yaxis: {
            title: 'SIDTW [mm]',
          },
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
        <div className="rounded-lg bg-green-50 p-4">
          <p className="text-sm text-gray-600">
            Bester Bereich (niedrigste SIDTW)
          </p>
          <p className="text-2xl font-bold text-green-700">
            {binnedData[bestBinIndex]?.binLabel} {activeConfig.unit}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Median: {binMedians[bestBinIndex]?.toFixed(3)} mm
          </p>
        </div>
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-sm text-gray-600">Schlechtester Bereich</p>
          <p className="text-2xl font-bold text-red-700">
            {binnedData[worstBinIndex]?.binLabel} {activeConfig.unit}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Median: {binMedians[worstBinIndex]?.toFixed(3)} mm
          </p>
        </div>
      </div>

      {/* Interpretation */}
      <div className="mt-4 rounded-lg bg-blue-50 p-4">
        <p className="text-sm font-medium text-blue-900">💡 Interpretation:</p>
        <p className="mt-1 text-sm text-blue-800">
          <strong>Grün</strong> = Optimaler Bereich mit bester Genauigkeit •{' '}
          <strong>Rot</strong> = Vermeiden - höchste Abweichungen •{' '}
          <strong>Box</strong> = 50% der Daten (Q1-Q3) •{' '}
          <strong>Linie in Box</strong> = Median • <strong>Whiskers</strong> =
          Min/Max Bereich
        </p>
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
          SIDTW-Verteilung nach Bewegungsparametern
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
          SIDTW-Verteilung nach Bewegungsparametern
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
          SIDTW-Verteilung nach Bewegungsparametern
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
