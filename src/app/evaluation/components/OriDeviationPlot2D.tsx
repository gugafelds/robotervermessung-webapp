'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  GD: { line: '#188b52ff' },
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
    GD: MetricState;
    QDTW: MetricState;
  };
  currentQDTWDeviation: any[];
  currentGDDeviation: any[];
  currentBahnInfo: any;
}

export const OriDeviationPlot2D: React.FC<OriDeviationPlot2DProps> = ({
  hasOrientationData,
  selectedSegment,
  metrics,
  currentQDTWDeviation,
  currentGDDeviation,
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
  const getTimeArray = (data: any[], metricType: 'GD' | 'QDTW') => {
    if (!data.length) return [];

    if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
      return data.map((_, i) => i);
    }

    const startTime = new Date(currentBahnInfo.startTime).getTime();
    const endTime = new Date(currentBahnInfo.endTime).getTime();
    const duration = endTime - startTime;

    const allGDData = currentGDDeviation || [];
    const totalPoints = Math.max(...allGDData.map((d) => d.pointsOrder));

    if (metricType === 'GD') {
      return data.map((d) => {
        return ((d.pointsOrder / totalPoints) * duration) / 1000;
      });
    }
    // QDTW: interpoliere zwischen min und max pointsOrder des Segments
    const filteredGD = filterDataBySegment(allGDData);

    const GDMinOrder = Math.min(...filteredGD.map((d) => d.pointsOrder));
    const GDMaxOrder = Math.max(...filteredGD.map((d) => d.pointsOrder));

    const startTimeSeg = ((GDMinOrder / totalPoints) * duration) / 1000;
    const endTimeSeg = ((GDMaxOrder / totalPoints) * duration) / 1000;

    return data.map((_, i) => {
      return (
        startTimeSeg + (i / (data.length - 1)) * (endTimeSeg - startTimeSeg)
      );
    });
  };

  // 2D Plot erstellen
  const create2DPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    if (metrics.GD.isLoaded && metrics.GD.visible) {
      const filteredData = filterDataBySegment(currentGDDeviation);
      const sortedGD = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedGD, 'GD');

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'GD',
        x: timePoints,
        y: sortedGD.map((d) => d.GDDistances),
        line: { color: methodColors.GD.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>GD: %{y:.2f}°<extra></extra>',
      });
    }

    if (metrics.QDTW.isLoaded && metrics.QDTW.visible) {
      const filteredData = filterDataBySegment(currentQDTWDeviation);
      const sortedQDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedQDTW, 'QDTW');

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
    title: {
      text:
        selectedSegment === 'total'
          ? 'Orientierung (Gesamtmessung)'
          : `Orientierung (Segment ${selectedSegment.split('_')[1]})`,
    },
    font: { family: 'Helvetica' },
    xaxis: { title: { text: 'Zeit [s]' } },
    yaxis: { title: { text: 'Abweichung [°]' }, rangemode: 'tozero' },
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
