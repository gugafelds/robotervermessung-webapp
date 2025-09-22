/* eslint-disable no-nested-ternary */

'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  EA: {
    soll: '#003560',
    ist: '#0066b8',
    connection: 'rgba(0, 53, 96, 0.7)',
  },
  DFD: {
    soll: '#e63946',
    ist: '#ff6b6b',
    connection: 'rgba(230, 57, 70, 0.7)',
  },
  DTW: {
    soll: '#774936',
    ist: '#a47551',
    connection: 'rgba(119, 73, 54, 0.7)',
  },
  SIDTW: {
    soll: '#2a9d8f',
    ist: '#54ccc0',
    connection: 'rgba(42, 157, 143, 0.7)',
  },
};

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface PosDeviationPlot3DProps {
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
}

export const PosDeviationPlot3D: React.FC<PosDeviationPlot3DProps> = ({
  hasDeviationData,
  selectedSegment,
  metrics,
  currentEuclideanDeviation,
  currentDiscreteFrechetDeviation,
  currentSIDTWDeviation,
  currentDTWDeviation,
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

  // Helper für 3D Traces
  const addMethodTraces = (
    data: any[],
    methodName: 'EA' | 'DFD' | 'SIDTW' | 'DTW',
    colors: any,
  ): Partial<PlotData>[] => {
    const filteredData = filterDataBySegment(data);
    if (!filteredData.length) return [];

    const sortedData = [...filteredData].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );

    const traces: Partial<PlotData>[] = [];

    const prefix = methodName;
    const sollFields = {
      x: `${prefix}SollX`,
      y: `${prefix}SollY`,
      z: `${prefix}SollZ`,
    };
    const istFields = {
      x: `${prefix}IstX`,
      y: `${prefix}IstY`,
      z: `${prefix}IstZ`,
    };

    // Soll trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Soll`,
      x: sortedData.map((d) => d[sollFields.x]),
      y: sortedData.map((d) => d[sollFields.y]),
      z: sortedData.map((d) => d[sollFields.z]),
      line: { color: colors.soll, width: 3 },
      hovertemplate:
        'X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<br><extra></extra>',
    });

    // Ist trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Ist`,
      x: sortedData.map((d) => d[istFields.x]),
      y: sortedData.map((d) => d[istFields.y]),
      z: sortedData.map((d) => d[istFields.z]),
      line: { color: colors.ist, width: 4 },
      hovertemplate:
        'X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<br><extra></extra>',
    });

    // Verbindungslinien
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Abweichungen`,
      showlegend: true,
      x: sortedData.flatMap((point) => [
        point[sollFields.x],
        point[istFields.x],
        null,
      ]),
      y: sortedData.flatMap((point) => [
        point[sollFields.y],
        point[istFields.y],
        null,
      ]),
      z: sortedData.flatMap((point) => [
        point[sollFields.z],
        point[istFields.z],
        null,
      ]),
      line: {
        color: colors.connection,
        width: 2,
        dash: 'solid',
      },
      hovertemplate: `${methodName} Abweichung: %{text:.2f}mm<br><extra></extra>`,
      text: sortedData.flatMap((point) => [
        point[`${methodName}Distances`],
        point[`${methodName}Distances`],
        null,
      ]),
    });

    return traces;
  };

  // 3D Plot erstellen
  const create3DPlot = (): Partial<PlotData>[] => {
    let plotData: Partial<PlotData>[] = [];

    if (
      metrics.ea.isLoaded &&
      metrics.ea.visible &&
      currentEuclideanDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentEuclideanDeviation, 'EA', methodColors.EA),
      );
    }
    if (
      metrics.dfd.isLoaded &&
      metrics.dfd.visible &&
      currentDiscreteFrechetDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(
          currentDiscreteFrechetDeviation,
          'DFD',
          methodColors.DFD,
        ),
      );
    }
    if (
      metrics.sidtw.isLoaded &&
      metrics.sidtw.visible &&
      currentSIDTWDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentSIDTWDeviation, 'SIDTW', methodColors.SIDTW),
      );
    }
    if (
      metrics.dtw.isLoaded &&
      metrics.dtw.visible &&
      currentDTWDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentDTWDeviation, 'DTW', methodColors.DTW),
      );
    }

    const firstVisibleData =
      metrics.ea.isLoaded &&
      metrics.ea.visible &&
      currentEuclideanDeviation?.length
        ? currentEuclideanDeviation
        : metrics.dfd.isLoaded &&
            metrics.dfd.visible &&
            currentDiscreteFrechetDeviation?.length
          ? currentDiscreteFrechetDeviation
          : metrics.sidtw.isLoaded &&
              metrics.sidtw.visible &&
              currentSIDTWDeviation?.length
            ? currentSIDTWDeviation
            : metrics.dtw.isLoaded &&
                metrics.dtw.visible &&
                currentDTWDeviation?.length
              ? currentDTWDeviation
              : null;

    if (firstVisibleData) {
      const filteredData = filterDataBySegment(firstVisibleData);
      const sortedData = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );

      if (sortedData.length > 0) {
        const firstPoint = sortedData[0];
        const lastPoint = sortedData[sortedData.length - 1];

        // Ermittle das Feld-Präfix der ersten sichtbaren Metrik
        const methodPrefix =
          metrics.ea.isLoaded && metrics.ea.visible
            ? 'EA'
            : metrics.dfd.isLoaded && metrics.dfd.visible
              ? 'DFD'
              : metrics.sidtw.isLoaded && metrics.sidtw.visible
                ? 'SIDTW'
                : 'DTW';

        // Startpunkt (grün)
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: 'Startpunkt',
          x: [firstPoint[`${methodPrefix}IstX`]],
          y: [firstPoint[`${methodPrefix}IstY`]],
          z: [firstPoint[`${methodPrefix}IstZ`]],
          marker: {
            size: 4,
            color: 'green',
            symbol: 'diamond',
            opacity: 1,
            line: {
              color: 'darkgreen',
              width: 2,
            },
          },
          hovertemplate:
            'Startpunkt<br>X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<extra></extra>',
        });

        // Endpunkt (rot)
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: 'Endpunkt',
          x: [lastPoint[`${methodPrefix}IstX`]],
          y: [lastPoint[`${methodPrefix}IstY`]],
          z: [lastPoint[`${methodPrefix}IstZ`]],
          marker: {
            size: 4,
            color: 'red',
            symbol: 'circle',
            opacity: 1,
            line: {
              color: 'darkred',
              width: 2,
            },
          },
          hovertemplate:
            'Endpunkt<br>X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<extra></extra>',
        });
      }
    }

    return plotData;
  };

  // Layout für 3D Plot
  const get3DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? '3D-Abweichungsplot (Gesamtmessung)'
        : `3D-Abweichungsplot (Segment ${selectedSegment.split('_')[1]})`,
    autosize: true,
    height: 600,
    scene: {
      camera: {
        up: { x: 0, y: 0, z: 1 },
        center: { x: 0, y: 0, z: -0.1 },
        eye: { x: 1.15, y: 1, z: 1 },
      },
      aspectmode: 'cube',
      dragmode: 'orbit',
      xaxis: { title: 'X [mm]', showgrid: true, zeroline: true },
      yaxis: { title: 'Y [mm]', showgrid: true, zeroline: true },
      zaxis: { title: 'Z [mm]', showgrid: true, zeroline: true },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.15,
      x: 0.5,
      xanchor: 'center',
      bgcolor: 'rgba(255,255,255,0.8)',
    },
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
            data={create3DPlot()}
            layout={get3DLayout()}
            useResizeHandler
            config={{
              displaylogo: false,
              modeBarButtonsToRemove: [
                'toImage',
                'orbitRotation',
                'zoom3d',
                'tableRotation',
                'pan3d',
                'resetCameraDefault3d',
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
