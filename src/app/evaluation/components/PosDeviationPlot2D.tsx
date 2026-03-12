'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  ED: { line: '#003560' },
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
    ED: MetricState;
    SIDTW: MetricState;
  };
  currentEuclideanDeviation: any[];
  currentSIDTWDeviation: any[];
  currentBahnInfo: any;
}

export const PosDeviationPlot2D: React.FC<PosDeviationPlot2DProps> = ({
  hasDeviationData,
  selectedSegment,
  metrics,
  currentEuclideanDeviation,
  currentSIDTWDeviation,
  currentBahnInfo,
}) => {
  // Daten nach Segment filtern
  const filterDataBySegment = (data: any[]) => {
    if (!data?.length) return [];

    if (selectedSegment === 'total') {
      // Alte Struktur: nur Zeilen wo trajID === segID
      // Neue Struktur: alle Zeilen der aktuellen Bahn
      const hasOldStructure = data.some((d) => d.trajID === d.segID);

      if (hasOldStructure) {
        return data.filter((d) => d.trajID === d.segID);
      }
      // Alle Segmente der Bahn
      return data;
    }

    const segmentNum = selectedSegment.split('_')[1];
    return data.filter((d) => d.segID === `${d.trajID}_${segmentNum}`);
  };

  // Zeitarray generieren basierend auf pointsOrder
  const getTimeArray = (
    data: any[],
    metricType: 'ED' | 'SIDTW',
  ) => {
    if (!data.length) return [];

    if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
      return data.map((_, i) => i);
    }

    const startTime = new Date(currentBahnInfo.startTime).getTime();
    const endTime = new Date(currentBahnInfo.endTime).getTime();
    const duration = endTime - startTime;

    const allEDData = currentEuclideanDeviation || [];
    const totalPoints = Math.max(...allEDData.map((d) => d.pointsOrder));

    if (metricType === 'ED') {
      return data.map((d) => {
        return ((d.pointsOrder / totalPoints) * duration) / 1000;
      });
    }
    // QDTW: interpoliere zwischen min und max pointsOrder des Segments
    const filteredED = filterDataBySegment(allEDData);

    const eaMinOrder = Math.min(...filteredED.map((d) => d.pointsOrder));
    const eaMaxOrder = Math.max(...filteredED.map((d) => d.pointsOrder));

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

    if (metrics.ED.isLoaded && metrics.ED.visible) {
      const filteredData = filterDataBySegment(currentEuclideanDeviation);
      const sortedED = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedED, 'ED');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Euclidean Distance',
        x: timePoints,
        y: sortedED.map((d) => d.EDDistances),
        line: { color: methodColors.ED.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>ED: %{y:.2f}mm<extra></extra>',
      });
    }


    if (metrics.SIDTW.isLoaded && metrics.SIDTW.visible) {
      const filteredData = filterDataBySegment(currentSIDTWDeviation);
      const sortedSIDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedSIDTW, 'SIDTW');

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
/*
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
    }*/

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
