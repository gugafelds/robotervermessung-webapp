/* eslint-disable react/button-has-type */

'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData, PlotType } from 'plotly.js';
import React, { useState } from 'react';

import type { DFDInfo, EAInfo, SIDTWInfo } from '@/types/auswertung.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface CombinedAnalysisPlotProps {
  EAInfo: EAInfo[];
  DFDInfo: DFDInfo[];
  SIDTWInfo: SIDTWInfo[];
}

// Erweitere das Layout-Interface für die Box-Plot-spezifischen Properties
interface ExtendedLayout extends Partial<Layout> {
  boxgap?: number;
  boxgroupgap?: number;
  hoverinfo?: string;
}

export const AuswertungInfoPlot: React.FC<CombinedAnalysisPlotProps> = ({
  EAInfo,
  DFDInfo,
  SIDTWInfo,
}) => {
  const [windowStart, setWindowStart] = useState(0);
  const WINDOW_SIZE = 15;
  const STEP_SIZE = WINDOW_SIZE - 1; // Überlappung um 1 Element

  const handlePrevious = () =>
    setWindowStart(Math.max(0, windowStart - STEP_SIZE));

  const handleNext = () => {
    const maxLength = Math.max(EAInfo.length, DFDInfo.length, SIDTWInfo.length);
    setWindowStart(Math.min(windowStart + STEP_SIZE, maxLength - WINDOW_SIZE));
  };

  // Berechne globale Min und Max Werte - jetzt auf Component-Level
  const calculateGlobalMinMax = () => {
    const EAMaxDistances = EAInfo.map((d) => Math.max(d.EAMaxDistance || 0));
    const EAMinDistances = EAInfo.map((d) =>
      Math.min(d.EAMinDistance || Infinity),
    );
    const DFDMaxDistances = DFDInfo.map((d) => Math.max(d.DFDMaxDistance || 0));
    const DFDMinDistances = DFDInfo.map((d) =>
      Math.min(d.DFDMinDistance || Infinity),
    );
    const SIDTWMaxDistances = SIDTWInfo.map((d) =>
      Math.max(d.SIDTWMaxDistance || 0),
    );
    const SIDTWMinDistances = SIDTWInfo.map((d) =>
      Math.min(d.SIDTWMinDistance || Infinity),
    );

    const globalMax = Math.max(
      ...EAMaxDistances,
      ...DFDMaxDistances,
      ...SIDTWMaxDistances,
    );
    const globalMin = Math.min(
      ...EAMinDistances.filter((d) => d !== Infinity),
      ...DFDMinDistances.filter((d) => d !== Infinity),
      ...SIDTWMinDistances.filter((d) => d !== Infinity),
    );

    // Füge etwas Padding hinzu (10% des Bereichs)
    const range = globalMax - globalMin;
    const padding = range * 0.1;

    return {
      min: globalMin - padding,
      max: globalMax + padding,
    };
  };

  const { min: yMin, max: yMax } = calculateGlobalMinMax();

  const createPlotData = (): Partial<PlotData>[] => {
    const processData = (data: any[]) => {
      return [...data]
        .sort((a, b) => {
          const segmentA = parseInt(a.segmentID.split('_')[1], 10);
          const segmentB = parseInt(b.segmentID.split('_')[1], 10);
          return segmentA - segmentB;
        })
        .slice(windowStart, windowStart + WINDOW_SIZE);
    };

    // Funktion zur Erzeugung von transparenten Farben
    const getColorWithOpacity = (color: string, opacity: number) => {
      // Für unsere vordefinierten Farben wandeln wir sie in RGBA um
      const colorMap: any = {
        '#003560': `rgba(0, 53, 96, ${opacity})`, // Blau
        '#2a9d8f': `rgba(42, 157, 143, ${opacity})`, // Grün
        '#e63946': `rgba(230, 57, 70, ${opacity})`, // Rot
      };
      return colorMap[color] || color;
    };

    const createBoxTrace = (
      data: any[],
      methodPrefix: string,
      color: string,
      name: string,
    ) => {
      const methodNames = {
        EA: 'EA',
        DFD: 'DFD',
        SIDTW: 'SIDTW',
      };

      const segments = data.map((d) => ({
        segment: parseInt(d.segmentID.split('_')[1], 10),
        minDistance: d[`${methodPrefix}MinDistance`],
        maxDistance: d[`${methodPrefix}MaxDistance`],
        avgDistance: d[`${methodPrefix}AvgDistance`],
        stdPlus:
          d[`${methodPrefix}AvgDistance`] + d[`${methodPrefix}StdDeviation`],
        stdMinus:
          d[`${methodPrefix}AvgDistance`] - d[`${methodPrefix}StdDeviation`],
      }));

      // Erstelle den eigentlichen Box-Plot mit Opacity 0
      const boxTrace: any = {
        type: 'box' as PlotType,
        name,
        x: segments.map((s) => s.segment),
        q1: segments.map((s) => s.stdMinus),
        median: segments.map((s) => s.avgDistance),
        q3: segments.map((s) => s.stdPlus),
        lowerfence: segments.map((s) => s.minDistance),
        upperfence: segments.map((s) => s.maxDistance),
        marker: { color: 'rgba(0,0,0,0)' }, // Unsichtbarer Marker
        line: { color },
        fillcolor: getColorWithOpacity(color, 0.2),
        whiskerwidth: 0.8,
        hoverinfo: 'skip', // Deaktiviere den Standard-Hover
      };

      // Erstelle einen unsichtbaren Scatter-Plot für den benutzerdefinierten Hover
      const hoverTrace: Partial<PlotData> = {
        type: 'scatter' as PlotType,
        name,
        x: segments.map((s) => s.segment),
        y: segments.map((s) => s.avgDistance),
        mode: 'markers',
        marker: {
          color: 'rgba(0,0,0,0)',
          size: 20,
        },
        showlegend: false,
        hovertemplate:
          `${methodNames[methodPrefix as keyof typeof methodNames]}<br>` + // Fügt den Methodennamen hinzu
          'Segment: %{x}<br>' +
          'Max: %{customdata[0]:.2f}mm<br>' +
          'Durchschnitt + Std.: %{customdata[1]:.2f}mm<br>' +
          'Durchschnitt: %{y:.2f}mm<br>' +
          'Durchschnitt - Std.: %{customdata[2]:.2f}mm<br>' +
          'Min: %{customdata[3]:.2f}mm<extra></extra>',
        customdata: segments.map((s) => [
          s.maxDistance,
          s.stdPlus,
          s.stdMinus,
          s.minDistance,
        ]),
      };

      return [boxTrace, hoverTrace];
    };

    const eaData = processData(EAInfo);
    const dfdData = processData(DFDInfo);
    const sidtwData = processData(SIDTWInfo);

    // Flatten das Array, da createBoxTrace jetzt zwei Traces zurückgibt
    return [
      ...createBoxTrace(eaData, 'EA', '#003560', 'EA'),
      ...createBoxTrace(sidtwData, 'SIDTW', '#2a9d8f', 'SIDTW'),
      ...createBoxTrace(dfdData, 'DFD', '#e63946', 'DFD'),
    ];
  };

  const layout: ExtendedLayout = {
    title: '3D-Position (Soll vs. Ist)',
    font: { family: 'Helvetica' },
    xaxis: {
      title: 'Segment',
      tickformat: 'd',
      ticks: 'outside',
      dtick: 1,
      range: [windowStart + 0.5, windowStart + WINDOW_SIZE + 0.5],
    },
    yaxis: {
      title: 'Abweichung (mm)',
      zeroline: false,
      range: [yMin, yMax],
    },
    boxmode: 'group',
    boxgap: 0.2,
    boxgroupgap: 0.1,
    legend: {
      orientation: 'h',
      y: -0.2,
    },
    hovermode: 'x',
  };

  return (
    <div className="w-full">
      <Plot
        data={createPlotData()}
        layout={layout}
        useResizeHandler
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
          responsive: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
      <div className="mt-4 flex justify-center gap-4">
        <button
          onClick={handlePrevious}
          disabled={windowStart === 0}
          className="rounded bg-primary px-4 py-2 text-white disabled:opacity-50"
        >
          ← Zurück
        </button>
        <button
          onClick={handleNext}
          disabled={
            windowStart >=
            Math.max(EAInfo.length, DFDInfo.length, SIDTWInfo.length) -
              WINDOW_SIZE
          }
          className="rounded bg-primary px-4 py-2 text-white disabled:opacity-50"
        >
          Weiter →
        </button>
      </div>
    </div>
  );
};
