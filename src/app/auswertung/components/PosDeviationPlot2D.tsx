'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  EA: { line: '#003560' },
  DFD: { line: '#e63946' },
  DTW: { line: '#774936' },
  SIDTW: { line: '#2a9d8f' },
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

    return data.filter((d) => {
      if (selectedSegment === 'total') {
        return d.bahnID === d.segmentID;
      }
      const segmentNum = selectedSegment.split('_')[1];
      return d.segmentID === `${d.bahnID}_${segmentNum}`;
    });
  };

  // Zeitarray generieren
  const getTimeArray = (data: any[]) => {
    if (!data.length) return [];

    if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
      return data.map((_, i) => i);
    }

    const startTime = new Date(currentBahnInfo.startTime).getTime();
    const endTime = new Date(currentBahnInfo.endTime).getTime();
    const duration = endTime - startTime;
    const points = data.length;

    return Array(points)
      .fill(0)
      .map((_, i) => {
        const timeProgress = (i / (points - 1)) * duration;
        return timeProgress / 1000;
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
      const timePoints = getTimeArray(sortedEA);

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
      const timePoints = getTimeArray(sortedDFD);

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
      const timePoints = getTimeArray(sortedSIDTW);

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
      const timePoints = getTimeArray(sortedDTW);

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'DTW',
        x: timePoints,
        y: sortedDTW.map((d) => d.DTWDistances),
        line: { color: methodColors.DTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>DTW: %{y:.2f}mm<extra></extra>',
      });
    }

    return plots;
  };

  // Layout für 2D Plot
  const get2DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? '2D-Abweichungsplot (Gesamtmessung)'
        : `2D-Abweichungsplot (Segment ${selectedSegment.split('_')[1]})`,
    font: { family: 'Helvetica' },
    xaxis: { title: 'Zeit [s]' },
    yaxis: { title: 'Abweichung [mm]' },
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
      <div className="rounded-lg border bg-white p-4 shadow-sm">
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
