/* eslint-disable react/button-has-type */
/* eslint-disable no-console */

'use client';

import { Loader2 } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useState } from 'react';

import {
  getDFDPositionById,
  getEAPositionById,
  getSIDTWPositionById,
} from '@/src/actions/auswertung.service';
import { useAuswertung } from '@/src/providers/auswertung.provider';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
}

interface AllDeviationsPlotProps {
  hasDeviationData: boolean;
  bahnId: string;
}

export const AllDeviationsPlot: React.FC<AllDeviationsPlotProps> = ({
  hasDeviationData,
  bahnId,
}) => {
  const [metrics, setMetrics] = useState<{
    ea: MetricState;
    dfd: MetricState;
    sidtw: MetricState;
  }>({
    ea: { isLoaded: false, isLoading: false },
    dfd: { isLoaded: false, isLoading: false },
    sidtw: { isLoaded: false, isLoading: false },
  });

  const {
    currentEuclideanDeviation,
    currentDiscreteFrechetDeviation,
    currentSIDTWDeviation,
    setCurrentEuclideanDeviation,
    setCurrentDiscreteFrechetDeviation,
    setCurrentSIDTWDeviation,
    auswertungInfo,
  } = useAuswertung();

  const loadMetricData = async (metricType: 'ea' | 'dfd' | 'sidtw') => {
    if (!bahnId) return;

    setMetrics((prev) => ({
      ...prev,
      [metricType]: { ...prev[metricType], isLoading: true },
    }));

    try {
      let data;
      switch (metricType) {
        case 'ea':
          data = await getEAPositionById(bahnId);
          setCurrentEuclideanDeviation(data);
          break;
        case 'dfd':
          data = await getDFDPositionById(bahnId);
          setCurrentDiscreteFrechetDeviation(data);
          break;
        case 'sidtw':
          data = await getSIDTWPositionById(bahnId);
          setCurrentSIDTWDeviation(data);
          break;
        default: {
          const exhaustiveCheck: never = metricType;
          throw new Error(`Unhandled metric type: ${exhaustiveCheck}`);
        }
      }

      setMetrics((prev) => ({
        ...prev,
        [metricType]: { isLoaded: true, isLoading: false },
      }));
    } catch (error) {
      console.error(`Error loading ${metricType} data:`, error);
      setMetrics((prev) => ({
        ...prev,
        [metricType]: { ...prev[metricType], isLoading: false },
      }));
    }
  };

  const calculateTimePoints = (points: number) => {
    const bahnInfo = auswertungInfo.bahn_info.find(
      (info) => info.bahnID === currentEuclideanDeviation[0]?.bahnID,
    );

    if (!bahnInfo?.startTime || !bahnInfo?.endTime) {
      return Array(points)
        .fill(0)
        .map((_, i) => i);
    }

    const startTime = new Date(bahnInfo.startTime).getTime();
    const endTime = new Date(bahnInfo.endTime).getTime();
    const duration = endTime - startTime;

    return Array(points)
      .fill(0)
      .map((_, i) => {
        const timeProgress = (i / (points - 1)) * duration;
        return timeProgress / 1000;
      });
  };

  const getSegmentTransitions = () => {
    let data;
    let timePoints;

    // Verwende die erste verfügbare Metrik für die Segmentierung
    if (metrics.ea.isLoaded) {
      data = [...currentEuclideanDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
    } else if (metrics.dfd.isLoaded) {
      data = [...currentDiscreteFrechetDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
    } else if (metrics.sidtw.isLoaded) {
      data = [...currentSIDTWDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
    } else {
      return { timePoints: [], transitions: [] };
    }

    // eslint-disable-next-line prefer-const
    timePoints = calculateTimePoints(data.length);
    const transitions: number[] = [];

    // Finde Segmentübergänge
    // eslint-disable-next-line no-plusplus
    for (let i = 1; i < data.length; i++) {
      if (data[i].segmentID !== data[i - 1].segmentID) {
        transitions.push(timePoints[i]);
      }
    }

    return { timePoints, transitions };
  };

  const createCombinedPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    if (metrics.ea.isLoaded) {
      const sortedEA = [...currentEuclideanDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePointsEA = calculateTimePoints(sortedEA.length);
      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Euklidischer Abstand',
        x: timePointsEA,
        y: sortedEA.map((d) => d.EADistances),
        line: { color: '#003560', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>EA: %{y:.1f}mm<extra></extra>',
      });
    }

    if (metrics.dfd.isLoaded) {
      const sortedDFD = [...currentDiscreteFrechetDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePointsDFD = calculateTimePoints(sortedDFD.length);
      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Diskrete Fréchet-Distanz',
        x: timePointsDFD,
        y: sortedDFD.map((d) => d.DFDDistances),
        line: { color: '#e63946', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>DFD: %{y:.1f}mm<extra></extra>',
      });
    }

    if (metrics.sidtw.isLoaded) {
      const sortedSIDTW = [...currentSIDTWDeviation].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePointsSIDTW = calculateTimePoints(sortedSIDTW.length);
      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'SIDTW',
        x: timePointsSIDTW,
        y: sortedSIDTW.map((d) => d.SIDTWDistances),
        line: { color: '#457b9d', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>SIDTW: %{y:.1f}mm<extra></extra>',
      });
    }

    return plots;
  };

  const getLayoutWithShapes = (): Partial<Layout> => {
    const baseLayout: Partial<Layout> = {
      title: '3D-Position (Soll vs. Ist)',
      font: { family: 'Helvetica' },
      xaxis: {
        title: 'Zeit (s)',
        tickformat: '.1f',
      },
      yaxis: {
        title: 'Abweichung (mm)',
      },
      hovermode: 'x unified',
      height: 500,
      margin: { t: 40, b: 40, l: 60, r: 20 },
      showlegend: true,
      legend: {
        orientation: 'h',
        y: -0.2,
      },
    };

    const { timePoints, transitions } = getSegmentTransitions();

    // Wenn keine Daten geladen sind, geben wir das Basis-Layout zurück
    if (transitions.length === 0) {
      return baseLayout;
    }

    // Shapes für alternierende Hintergrundfärbung und Segmentlinien erstellen
    const shapes = [
      // Alternierende Rechtecke für Segmente
      ...transitions.map((transition, index) => ({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: index === 0 ? 0 : transitions[index - 1],
        x1: transition,
        y0: 0,
        y1: 1,
        fillcolor:
          index % 2 === 0 ? 'rgba(240,240,240,0.5)' : 'rgba(255,255,255,0.5)',
        line: { width: 0 },
        layer: 'below',
      })),
      // Letztes Segment
      {
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: transitions[transitions.length - 1] || 0,
        x1: timePoints[timePoints.length - 1],
        y0: 0,
        y1: 1,
        fillcolor:
          transitions.length % 2 === 0
            ? 'rgba(240,240,240,0.5)'
            : 'rgba(255,255,255,0.5)',
        line: { width: 0 },
        layer: 'below',
      },
      // Vertikale Linien an den Segmentgrenzen
      ...transitions.map((transition) => ({
        type: 'line',
        xref: 'x',
        yref: 'paper',
        x0: transition,
        x1: transition,
        y0: 0,
        y1: 1,
        line: {
          color: 'rgba(150,150,150,0.3)',
          width: 1,
          dash: 'dot',
        },
        layer: 'below',
      })),
    ] as Plotly.Shape[];

    return {
      ...baseLayout,
      shapes,
    };
  };

  const anyMetricLoaded = Object.values(metrics).some((m) => m.isLoaded);

  if (!hasDeviationData) {
    return (
      <button disabled className="rounded bg-gray-300 px-4 py-2 text-gray-600">
        Keine Abweichungsdaten verfügbar
      </button>
    );
  }

  const getButtonContent = (metric: MetricState, label: string) => {
    if (metric.isLoading) {
      return (
        <>
          <Loader2 className="size-4 animate-spin" />
          <span>Lädt {label}...</span>
        </>
      );
    }

    if (metric.isLoaded) {
      return `${label} geladen`;
    }

    return `${label} laden`;
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-wrap gap-4">
        {/* EA Control */}
        <button
          onClick={() => loadMetricData('ea')}
          disabled={metrics.ea.isLoaded || metrics.ea.isLoading}
          className="inline-flex items-center space-x-2 rounded bg-primary px-3 py-1 text-sm text-white hover:bg-primary/80 disabled:bg-gray-300 disabled:text-gray-600"
        >
          {getButtonContent(metrics.ea, 'EA')}
        </button>

        {/* DFD Control */}
        <button
          onClick={() => loadMetricData('dfd')}
          disabled={metrics.dfd.isLoaded || metrics.dfd.isLoading}
          className="inline-flex items-center space-x-2 rounded bg-primary px-3 py-1 text-sm text-white hover:bg-primary/80 disabled:bg-gray-300 disabled:text-gray-600"
        >
          {getButtonContent(metrics.dfd, 'DFD')}
        </button>

        {/* SIDTW Control */}
        <button
          onClick={() => loadMetricData('sidtw')}
          disabled={metrics.sidtw.isLoaded || metrics.sidtw.isLoading}
          className="inline-flex items-center space-x-2 rounded bg-primary px-3 py-1 text-sm text-white hover:bg-primary/80 disabled:bg-gray-300 disabled:text-gray-600"
        >
          {getButtonContent(metrics.sidtw, 'SIDTW')}
        </button>
      </div>

      {anyMetricLoaded && (
        <Plot
          data={createCombinedPlot()}
          layout={getLayoutWithShapes()}
          useResizeHandler
          config={{
            displaylogo: false,
            modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
            responsive: true,
          }}
          style={{ width: '100%', height: '500px' }}
        />
      )}
    </div>
  );
};
