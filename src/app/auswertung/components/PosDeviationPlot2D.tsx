'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  EA: { line: '#003560' },
  DFD: { line: '#2a9d8f' },
  DTW: { line: '#774936' },
  SIDTW: { line: '#e63946' },
};

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface PosDeviationPlot2DProps {
  hasDeviationData: boolean;
  selectedSegment: string;
  metrics: {
    ea: MetricState;
    dfd: MetricState;
    sidtw: MetricState;
    dtw: MetricState;
  };
  currentEuclideanDeviation: any[];
  currentDiscreteFrechetDeviation: any[];
  currentSIDTWDeviation: any[];
  currentDTWDeviation: any[];
  currentBahnInfo: any;
}

export const PosDeviationPlot2D: React.FC<PosDeviationPlot2DProps> = ({
  hasDeviationData,
  selectedSegment,
  metrics,
  currentEuclideanDeviation,
  currentDiscreteFrechetDeviation,
  currentSIDTWDeviation,
  currentDTWDeviation,
  currentBahnInfo,
}) => {
  // Daten nach Segment filtern
  const filterDataBySegment = (data: any[]) => {
    if (!data?.length) return [];

    if (selectedSegment === 'total') {
      // Alte Struktur: nur Zeilen wo bahnID === segmentID
      // Neue Struktur: alle Zeilen der aktuellen Bahn
      const hasOldStructure = data.some((d) => d.bahnID === d.segmentID);

      if (hasOldStructure) {
        return data.filter((d) => d.bahnID === d.segmentID);
      }
      // Alle Segmente der Bahn
      return data;
    }

    const segmentNum = selectedSegment.split('_')[1];
    return data.filter((d) => d.segmentID === `${d.bahnID}_${segmentNum}`);
  };

  // Zeitarray generieren basierend auf pointsOrder
  const getTimeArray = (
    data: any[],
    metricType: 'ea' | 'sidtw' | 'dtw' | 'dfd',
  ) => {
    if (!data.length) return [];

    if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
      return data.map((_, i) => i);
    }

    const startTime = new Date(currentBahnInfo.startTime).getTime();
    const endTime = new Date(currentBahnInfo.endTime).getTime();
    const duration = endTime - startTime;

    const allEAData = currentEuclideanDeviation || [];
    const totalPoints = Math.max(...allEAData.map((d) => d.pointsOrder));

    if (metricType === 'ea') {
      return data.map((d) => {
        return ((d.pointsOrder / totalPoints) * duration) / 1000;
      });
    }
    // QDTW: interpoliere zwischen min und max pointsOrder des Segments
    const filteredEA = filterDataBySegment(allEAData);

    const eaMinOrder = Math.min(...filteredEA.map((d) => d.pointsOrder));
    const eaMaxOrder = Math.max(...filteredEA.map((d) => d.pointsOrder));

    const startTimeSeg = ((eaMinOrder / totalPoints) * duration) / 1000;
    const endTimeSeg = ((eaMaxOrder / totalPoints) * duration) / 1000;

    return data.map((_, i) => {
      return (
        startTimeSeg + (i / (data.length - 1)) * (endTimeSeg - startTimeSeg)
      );
    });
  };

  // 2D Plot erstellen
  const create2DPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    if (metrics.ea.isLoaded && metrics.ea.visible) {
      const filteredData = filterDataBySegment(currentEuclideanDeviation);
      const sortedEA = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedEA, 'ea');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Euklidischer Abstand',
        x: timePoints,
        y: sortedEA.map((d) => d.EADistances),
        line: { color: methodColors.EA.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>EA: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.dfd.isLoaded && metrics.dfd.visible) {
      const filteredData = filterDataBySegment(currentDiscreteFrechetDeviation);
      const sortedDFD = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedDFD, 'dfd');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Diskrete Fréchet-Distanz',
        x: timePoints,
        y: sortedDFD.map((d) => d.DFDDistances),
        line: { color: methodColors.DFD.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>DFD: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.sidtw.isLoaded && metrics.sidtw.visible) {
      const filteredData = filterDataBySegment(currentSIDTWDeviation);
      const sortedSIDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedSIDTW, 'sidtw');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'SIDTW',
        x: timePoints,
        y: sortedSIDTW.map((d) => d.SIDTWDistances),
        line: { color: methodColors.SIDTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>SIDTW: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.dtw.isLoaded && metrics.dtw.visible) {
      const filteredData = filterDataBySegment(currentDTWDeviation);
      const sortedDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedDTW, 'dtw');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'DTW',
        x: timePoints,
        y: sortedDTW.map((d) => d.DTWDistances),
        line: { color: methodColors.DTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>DTW: %{y:.2f}mm<extra></extra>',
        uirevision: 'true',
      });
    }

    return plots;
  };

  // Layout für 2D Plot
  const get2DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? 'Position (Gesamtmessung)'
        : `Position (Segment ${selectedSegment.split('_')[1]})`,
    font: { family: 'Helvetica' },
    xaxis: { title: 'Zeit [s]' },
    yaxis: { title: 'Abweichung [mm]', rangemode: 'tozero' },
    hovermode: 'x unified',
    height: 600,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
  });

  const anyMetricVisible = Object.values(metrics).some(
    (m) => m.isLoaded && m.visible,
  );

  if (!hasDeviationData) {
    return null;
  }

  return (
    <div className="w-1/2">
      <div className="rounded-lg border border-gray-500 bg-white p-4">
        {anyMetricVisible ? (
          <Plot
            data={create2DPlot()}
            layout={get2DLayout()}
            useResizeHandler
            config={{
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
            }}
            style={{ width: '100%', height: '600px' }}
          />
        ) : (
          <div className="flex items-center justify-center text-gray-500">
            Keine Datenquelle ausgewählt
          </div>
        )}
      </div>
    </div>
  );
};
