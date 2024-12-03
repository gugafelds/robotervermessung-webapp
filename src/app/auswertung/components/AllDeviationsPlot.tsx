'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData, Shape } from 'plotly.js';
import React, { useState } from 'react';

import {
  getDFDDeviationById,
  getEADeviationById,
  getSIDTWDeviationById,
} from '@/src/actions/auswertung.service';
import { useAuswertung } from '@/src/providers/auswertung.provider';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface AllDeviationsPlotProps {
  hasDeviationData: boolean;
  bahnId: string;
}

export const AllDeviationsPlot: React.FC<AllDeviationsPlotProps> = ({
  hasDeviationData,
  bahnId,
}) => {
  const [showPlot, setShowPlot] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const {
    currentEuclideanDeviation,
    currentDiscreteFrechetDeviation,
    currentSIDTWDeviation,
    setCurrentEuclideanDeviation,
    setCurrentDiscreteFrechetDeviation,
    setCurrentSIDTWDeviation,
    auswertungInfo,
  } = useAuswertung();

  const loadDeviationData = async () => {
    if (!bahnId) return;

    setIsLoading(true);
    try {
      const [ea, dfd, sidtw] = await Promise.all([
        getEADeviationById(bahnId),
        getDFDDeviationById(bahnId),
        getSIDTWDeviationById(bahnId),
      ]);

      setCurrentEuclideanDeviation(ea);
      setCurrentDiscreteFrechetDeviation(dfd);
      setCurrentSIDTWDeviation(sidtw);
      setShowPlot(true);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error loading deviation data:', error);
    }
    setIsLoading(false);
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

  const createCombinedPlot = (): Partial<PlotData>[] => {
    const sortedEA = [...currentEuclideanDeviation].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );
    const sortedDFD = [...currentDiscreteFrechetDeviation].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );
    const sortedSIDTW = [...currentSIDTWDeviation].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );

    const timePointsEA = calculateTimePoints(sortedEA.length);
    const timePointsDFD = calculateTimePoints(sortedDFD.length);
    const timePointsSIDTW = calculateTimePoints(sortedSIDTW.length);

    // Finde Segmentübergänge
    const segmentTransitions: number[] = [];
    const segmentIds: string[] = [];
    // eslint-disable-next-line no-plusplus
    for (let i = 1; i < sortedEA.length; i++) {
      if (sortedEA[i].segmentID !== sortedEA[i - 1].segmentID) {
        segmentTransitions.push(timePointsEA[i]);
        segmentIds.push(sortedEA[i - 1].segmentID.split('_')[1]);
      }
    }
    // Füge das letzte Segment hinzu
    segmentIds.push(sortedEA[sortedEA.length - 1].segmentID.split('_')[1]);

    return [
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Euklidischer Abstand',
        x: timePointsEA,
        y: sortedEA.map((d) => d.EADistances),
        line: { color: '#003560', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>EA: %{y:.1f}mm<extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Diskrete Fréchet-Distanz',
        x: timePointsDFD,
        y: sortedDFD.map((d) => d.DFDDistances),
        line: { color: '#e63946', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>DFD: %{y:.1f}mm<extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'SIDTW',
        x: timePointsSIDTW,
        y: sortedSIDTW.map((d) => d.SIDTWDistances),
        line: { color: '#457b9d', width: 2 },
        hovertemplate: 'Zeit: %{x:.3f}s<br>SIDTW: %{y:.1f}mm<extra></extra>',
      },
    ];
  };

  if (!hasDeviationData) {
    return (
      // eslint-disable-next-line react/button-has-type
      <button disabled className="rounded bg-gray-300 px-4 py-2 text-gray-600">
        Keine Abweichungsdaten verfügbar
      </button>
    );
  }

  if (!showPlot) {
    return (
      // eslint-disable-next-line react/button-has-type
      <button
        onClick={loadDeviationData}
        disabled={isLoading}
        className="rounded bg-primary px-4 py-2 text-white hover:bg-primary/80 disabled:bg-gray-300 disabled:text-gray-600"
      >
        {isLoading ? 'Lade Daten...' : 'Abweichungen anzeigen'}
      </button>
    );
  }

  const evaluation = currentEuclideanDeviation[0]?.evaluation || '';
  const timePoints = calculateTimePoints(currentEuclideanDeviation.length);
  const segmentTransitions: number[] = [];

  // Finde Segmentübergänge für Shapes
  // eslint-disable-next-line no-plusplus
  for (let i = 1; i < currentEuclideanDeviation.length; i++) {
    if (
      currentEuclideanDeviation[i].segmentID !==
      currentEuclideanDeviation[i - 1].segmentID
    ) {
      segmentTransitions.push(timePoints[i]);
    }
  }

  const layout: Partial<Layout> = {
    title: `(${evaluation})`,
    font: { family: 'Helvetica' },
    xaxis: {
      title: 'Zeit (s)',
      tickformat: '.1f',
    },
    yaxis: {
      title: 'Abstand (mm)',
    },
    hovermode: 'x unified',
    height: 500,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.2,
    },
    shapes: [
      ...segmentTransitions.map((transition, index) => ({
        type: 'rect' as const,
        xref: 'x' as const,
        yref: 'paper' as const,
        x0: index === 0 ? 0 : segmentTransitions[index - 1],
        x1: transition,
        y0: 0,
        y1: 1,
        fillcolor:
          index % 2 === 0 ? 'rgba(240,240,240,0.5)' : 'rgba(255,255,255,0.5)',
        line: { width: 0 },
        layer: 'below' as const,
      })),
      {
        type: 'rect' as const,
        xref: 'x' as const,
        yref: 'paper' as const,
        x0: segmentTransitions[segmentTransitions.length - 1] || 0,
        x1: timePoints[timePoints.length - 1],
        y0: 0,
        y1: 1,
        fillcolor:
          segmentTransitions.length % 2 === 0
            ? 'rgba(240,240,240,0.5)'
            : 'rgba(255,255,255,0.5)',
        line: { width: 0 },
        layer: 'below' as const,
      },
      ...segmentTransitions.map((transition) => ({
        type: 'line' as const,
        xref: 'x' as const,
        yref: 'paper' as const,
        x0: transition,
        x1: transition,
        y0: 0,
        y1: 1,
        line: {
          color: 'rgba(150,150,150,0.3)',
          width: 1,
          dash: 'dot',
        },
        layer: 'below' as const,
      })),
    ] as Partial<Shape>[],
  };

  return (
    <div className="w-full">
      {!showPlot ? (
        // eslint-disable-next-line react/button-has-type
        <button
          onClick={() => setShowPlot(true)}
          className="rounded bg-primary px-4 py-2 text-white hover:bg-primary/80"
        >
          Abweichungen anzeigen
        </button>
      ) : (
        <Plot
          data={createCombinedPlot()}
          layout={layout}
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
