'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useState } from 'react';

import type { DFDInfo, EAInfo, SIDTWInfo } from '@/types/auswertung.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface CombinedAnalysisPlotProps {
  eaAnalyses: EAInfo[];
  dfdAnalyses: DFDInfo[];
  sidtwAnalyses: SIDTWInfo[];
}

export const MetrikenPanelPlot: React.FC<CombinedAnalysisPlotProps> = ({
  eaAnalyses,
  dfdAnalyses,
  sidtwAnalyses,
}) => {
  // Konfiguration für das Segment-Fenster
  const [windowStart, setWindowStart] = useState(0);
  const WINDOW_SIZE = 15;

  // Navigationsfunktionen
  const handlePrevious = () =>
    setWindowStart(Math.max(0, windowStart - WINDOW_SIZE));
  const handleNext = () => {
    const maxLength = Math.max(
      eaAnalyses.length,
      dfdAnalyses.length,
      sidtwAnalyses.length,
    );
    setWindowStart(
      Math.min(windowStart + WINDOW_SIZE, maxLength - WINDOW_SIZE),
    );
  };

  const createPlotData = (): Partial<PlotData>[] => {
    // Datenverarbeitung mit Fenster-Filterung
    const processData = (data: any[]) => {
      const filtered = [...data]
        .filter((a) => a.bahnID !== a.segmentID)
        .sort((a, b) => {
          const segmentA = parseInt(a.segmentID.split('_')[1], 10);
          const segmentB = parseInt(b.segmentID.split('_')[1], 10);
          return segmentA - segmentB;
        });
      return filtered.slice(windowStart, windowStart + WINDOW_SIZE);
    };

    const eaData = processData(eaAnalyses);
    const dfdData = processData(dfdAnalyses);
    const sidtwData = processData(sidtwAnalyses);

    // Farbpaletten für jede Metrik
    const colors = {
      ea: {
        main: 'rgba(0, 53, 96, 0.7)',
        error: 'rgba(0, 53, 96, 1)',
      },
      dfd: {
        main: 'rgba(230, 57, 70, 0.7)',
        error: 'rgba(230, 57, 70, 1)',
      },
      sidtw: {
        main: 'rgba(42, 157, 143, 0.7)',
        error: 'rgba(42, 157, 143, 1)',
      },
    };

    const barWidth = 0.25;

    return [
      // EA Bars mit zwei Fehlerbalken
      {
        type: 'bar',
        name: 'EA Durchschnitt',
        x: eaData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: eaData.map((d) => d.EAAvgDistance),
        error_y: {
          type: 'data',
          array: eaData.map((d) => d.EAMaxDistance - d.EAAvgDistance),
          arrayminus: eaData.map((d) => d.EAAvgDistance - d.EAMinDistance),
          width: 5,
          color: colors.ea.error,
        },
        marker: {
          color: colors.ea.main,
        },
        width: barWidth,
        offset: -barWidth,
        legendgroup: 'ea',
      },
      {
        type: 'bar',
        name: 'EA Std. Abw.',
        x: eaData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: eaData.map((d) => d.EAAvgDistance),
        error_y: {
          type: 'data',
          array: eaData.map((d) => d.EAStdDeviation),
          arrayminus: eaData.map((d) => d.EAStdDeviation),
          width: 3,
          color: colors.ea.error,
          thickness: 3,
        },
        marker: {
          color: 'rgba(0,0,0,0)',
        },
        width: barWidth,
        offset: -barWidth,
        showlegend: false,
        legendgroup: 'ea',
      },

      // SIDTW Bars mit zwei Fehlerbalken
      {
        type: 'bar',
        name: 'SIDTW Durchschnitt',
        x: sidtwData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: sidtwData.map((d) => d.SIDTWAvgDistance),
        error_y: {
          type: 'data',
          array: sidtwData.map((d) => d.SIDTWMaxDistance - d.SIDTWAvgDistance),
          arrayminus: sidtwData.map(
            (d) => d.SIDTWAvgDistance - d.SIDTWMinDistance,
          ),
          width: 5,
          color: colors.sidtw.error,
        },
        marker: {
          color: colors.sidtw.main,
        },
        width: barWidth,
        offset: 0,
        legendgroup: 'sidtw',
      },
      {
        type: 'bar',
        name: 'SIDTW Std. Abw.',
        x: sidtwData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: sidtwData.map((d) => d.SIDTWAvgDistance),
        error_y: {
          type: 'data',
          array: sidtwData.map((d) => d.SIDTWStdDeviation),
          arrayminus: sidtwData.map((d) => d.SIDTWStdDeviation),
          width: 3,
          color: colors.sidtw.error,
          thickness: 3,
        },
        marker: {
          color: 'rgba(0,0,0,0)',
        },
        width: barWidth,
        offset: 0,
        showlegend: false,
        legendgroup: 'sidtw',
      },

      // DFD Bars mit zwei Fehlerbalken
      {
        type: 'bar',
        name: 'DFD Durchschnitt',
        x: dfdData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: dfdData.map((d) => d.DFDAvgDistance),
        error_y: {
          type: 'data',
          array: dfdData.map((d) => d.DFDMaxDistance - d.DFDAvgDistance),
          arrayminus: dfdData.map((d) => d.DFDAvgDistance - d.DFDMinDistance),
          width: 5,
          color: colors.dfd.error,
        },
        marker: {
          color: colors.dfd.main,
        },
        width: barWidth,
        offset: barWidth,
        legendgroup: 'dfd',
      },
      {
        type: 'bar',
        name: 'DFD Std. Abw.',
        x: dfdData.map((d) => parseInt(d.segmentID.split('_')[1], 10)),
        y: dfdData.map((d) => d.DFDAvgDistance),
        error_y: {
          type: 'data',
          array: dfdData.map((d) => d.DFDStdDeviation),
          arrayminus: dfdData.map((d) => d.DFDStdDeviation),
          width: 3,
          color: colors.dfd.error,
          thickness: 3,
        },
        marker: {
          color: 'rgba(0,0,0,0)',
        },
        width: barWidth,
        offset: barWidth,
        showlegend: false,
        legendgroup: 'dfd',
      },
    ];
  };

  const layout: Partial<Layout> = {
    title: `(${eaAnalyses[0]?.evaluation || ''})`,
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 'Segment',
      tickformat: 'd',
      ticks: 'outside',
      dtick: 1,
      // Sichtbarer Bereich wird auf das aktuelle Fenster beschränkt
      range: [windowStart - 0.5, windowStart + WINDOW_SIZE - 0.5],
    },
    yaxis: {
      title: 'Abweichung (mm)',
      zeroline: true,
    },
    legend: {
      orientation: 'h',
      y: -0.2,
    },
    barmode: 'group',
    hovermode: 'x unified',
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
        {/* eslint-disable-next-line react/button-has-type */}
        <button
          onClick={handlePrevious}
          disabled={windowStart === 0}
          className="rounded bg-primary px-4 py-2 text-white disabled:opacity-50"
        >
          ← Zurück
        </button>
        {/* eslint-disable-next-line react/button-has-type */}
        <button
          onClick={handleNext}
          disabled={
            windowStart >=
            Math.max(
              eaAnalyses.length,
              dfdAnalyses.length,
              sidtwAnalyses.length,
            ) -
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
