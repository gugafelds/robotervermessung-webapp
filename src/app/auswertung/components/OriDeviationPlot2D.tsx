'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  QAD: { line: '#188b52ff' },
  QDTW: { line: '#e63946' },
};

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface OriDeviationPlot2DProps {
  hasOrientationData: boolean;
  selectedSegment: string;
  metrics: {
    qad: MetricState;
    qdtw: MetricState;
  };
  currentQDTWDeviation: any[];
  currentQADDeviation: any[];
  currentBahnInfo: any;
}

export const OriDeviationPlot2D: React.FC<OriDeviationPlot2DProps> = ({
  hasOrientationData,
  selectedSegment,
  metrics,
  currentQDTWDeviation,
  currentQADDeviation,
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
  const getTimeArray = (data: any[], metricType: 'qad' | 'qdtw') => {
    if (!data.length) return [];

    if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
      return data.map((_, i) => i);
    }

    const startTime = new Date(currentBahnInfo.startTime).getTime();
    const endTime = new Date(currentBahnInfo.endTime).getTime();
    const duration = endTime - startTime;

    const allQADData = currentQADDeviation || [];
    const totalPoints = Math.max(...allQADData.map((d) => d.pointsOrder));

    if (metricType === 'qad') {
      return data.map((d) => {
        return ((d.pointsOrder / totalPoints) * duration) / 1000;
      });
    }
    // QDTW: interpoliere zwischen min und max pointsOrder des Segments
    const filteredQAD = filterDataBySegment(allQADData);

    const qadMinOrder = Math.min(...filteredQAD.map((d) => d.pointsOrder));
    const qadMaxOrder = Math.max(...filteredQAD.map((d) => d.pointsOrder));

    const startTimeSeg = ((qadMinOrder / totalPoints) * duration) / 1000;
    const endTimeSeg = ((qadMaxOrder / totalPoints) * duration) / 1000;

    return data.map((_, i) => {
      return (
        startTimeSeg + (i / (data.length - 1)) * (endTimeSeg - startTimeSeg)
      );
    });
  };

  // 2D Plot erstellen
  const create2DPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    if (metrics.qad.isLoaded && metrics.qad.visible) {
      const filteredData = filterDataBySegment(currentQADDeviation);
      const sortedQAD = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedQAD, 'qad');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'QAD',
        x: timePoints,
        y: sortedQAD.map((d) => d.QADDistances),
        line: { color: methodColors.QAD.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>QAD: %{y:.2f}°<extra></extra>',
      });
    }

    if (metrics.qdtw.isLoaded && metrics.qdtw.visible) {
      const filteredData = filterDataBySegment(currentQDTWDeviation);
      const sortedQDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedQDTW, 'qdtw');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'QDTW',
        x: timePoints,
        y: sortedQDTW.map((d) => d.QDTWDistances),
        line: { color: methodColors.QDTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>QDTW: %{y:.2f}°<extra></extra>',
      });
    }

    return plots;
  };

  // Layout für 2D Plot
  const get2DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? 'Orientierung (Gesamtmessung)'
        : `Orientierung (Segment ${selectedSegment.split('_')[1]})`,
    font: { family: 'Helvetica' },
    xaxis: { title: 'Zeit [s]' },
    yaxis: { title: 'Abweichung [°]', rangemode: 'tozero' },
    hovermode: 'x unified',
    height: 600,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
  });

  const anyMetricVisible = Object.values(metrics).some(
    (m) => m.isLoaded && m.visible,
  );

  if (!hasOrientationData) {
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
