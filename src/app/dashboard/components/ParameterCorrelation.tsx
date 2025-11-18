/* eslint-disable react/button-has-type,no-nested-ternary */

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
  numBins?: number;
  useRanges: boolean;
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
      numBins: 6,
      useRanges: true,
    },
    {
      id: 'acceleration',
      label: 'Beschleunigung',
      unit: 'mm/s²',
      xLabel: 'Beschleunigungsbereich',
      numBins: 6,
      useRanges: true,
    },
    {
      id: 'weight',
      label: 'Last',
      unit: 'kg',
      xLabel: 'Last',
      useRanges: false,
    },
    {
      id: 'stop_point',
      label: 'Stopp-Punkte',
      unit: '%',
      xLabel: 'Stopp-Punkte',
      useRanges: false,
    },
    {
      id: 'wait_time',
      label: 'Wartezeit',
      unit: 's',
      xLabel: 'Wartezeit',
      useRanges: false,
    },
  ];

  const activeConfig = parameters.find((p) => p.id === activeParam)!;

  // Neue Funktion für exakte Werte
  const createExactValueGroups = (paramValues: number[]): BinnedData[] => {
    const uniqueValues = [...new Set(paramValues)].sort((a, b) => a - b);

    return uniqueValues.map((value) => {
      const sidtwInGroup = data
        .filter((d) => d[activeParam] === value)
        .map((d) => d.sidtw);

      return {
        binLabel: value.toString(),
        sidtwValues: sidtwInGroup,
        count: sidtwInGroup.length,
      };
    });
  };

  // Binning-Funktion
  const createBins = (paramValues: number[], numBins: number): BinnedData[] => {
    const min = Math.min(...paramValues);
    const max = Math.max(...paramValues);
    const binWidth = (max - min) / numBins;

    const bins: BinnedData[] = [];

    for (let i = 0; i < numBins; i += 1) {
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
  const binnedData = activeConfig.useRanges
    ? createBins(paramValues, activeConfig.numBins!)
    : createExactValueGroups(paramValues);

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
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
      <Typography as="h2" className="mb-2">
        Einflussfaktoren auf Genauigkeit
      </Typography>
      <div className="mb-4 text-sm text-gray-600">
        <p>
          Box Plots zeigen die SIDTW-Verteilung für verschiedene
          Parameter-Bereiche. Eine Stichprobe von {data.length.toLocaleString()}{' '}
          repräsentativen Bahnen.
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
            type: 'category',
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
      <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-3">
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
            Median: {binMedians[bestBinIndex]?.toFixed(2)} mm
          </p>
        </div>
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-sm text-gray-600">Schlechtester Bereich</p>
          <p className="text-2xl font-bold text-red-700">
            {binnedData[worstBinIndex]?.binLabel} {activeConfig.unit}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Median: {binMedians[worstBinIndex]?.toFixed(2)} mm
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
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
        <Typography as="h2" className="mb-2">
          Einflussfaktoren auf Genauigkeit
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
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
        <Typography as="h2" className="mb-2">
          Einflussfaktoren auf Genauigkeit
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
      <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
        <Typography as="h2" className="mb-2">
          Einflussfaktoren auf Genauigkeit
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
