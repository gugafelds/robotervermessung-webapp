/* eslint-disable no-nested-ternary */

'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  ED: {
    cmd: '#003560',
    act: '#0066b8',
    connection: 'rgba(0, 53, 96, 0.7)',
  },
  SIDTW: {
    cmd: '#e63946',
    act: '#ff6b6b',
    connection: 'rgba(230, 57, 70, 0.7)',
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
    ED: MetricState;
    SIDTW: MetricState;
  };
  currentEDDeviation: any[];
  currentSIDTWDeviation: any[];
}

export const PosDeviationPlot3D: React.FC<PosDeviationPlot3DProps> = ({
  hasDeviationData,
  selectedSegment,
  metrics,
  currentEDDeviation,
  currentSIDTWDeviation,
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

  // Helper für 3D Traces
  const addMethodTraces = (
    data: any[],
    methodName: 'ED' | 'SIDTW',
    colors: any,
  ): Partial<PlotData>[] => {
    const filteredData = filterDataBySegment(data);
    if (!filteredData.length) return [];

    const sortedData = [...filteredData].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );

    const traces: Partial<PlotData>[] = [];

    const prefix = methodName;
    const cmdFields = {
      x: `${prefix}CmdX`,
      y: `${prefix}CmdY`,
      z: `${prefix}CmdZ`,
    };
    const actFields = {
      x: `${prefix}ActX`,
      y: `${prefix}ActY`,
      z: `${prefix}ActZ`,
    };

    // Soll trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} (C)`,
      x: sortedData.map((d) => d[cmdFields.x]),
      y: sortedData.map((d) => d[cmdFields.y]),
      z: sortedData.map((d) => d[cmdFields.z]),
      line: { color: colors.cmd, width: 3 },
      hovertemplate:
        'X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<br><extra></extra>',
    });

    // Ist trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} (M)`,
      x: sortedData.map((d) => d[actFields.x]),
      y: sortedData.map((d) => d[actFields.y]),
      z: sortedData.map((d) => d[actFields.z]),
      line: { color: colors.act, width: 4 },
      hovertemplate:
        'X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<br><extra></extra>',
    });

    // Verbindungslinien
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} deviation`,
      showlegend: true,
      x: sortedData.flatMap((point) => [
        point[cmdFields.x],
        point[actFields.x],
        null,
      ]),
      y: sortedData.flatMap((point) => [
        point[cmdFields.y],
        point[actFields.y],
        null,
      ]),
      z: sortedData.flatMap((point) => [
        point[cmdFields.z],
        point[actFields.z],
        null,
      ]),
      line: {
        color: colors.connection,
        width: 2,
        dash: 'solid',
      },
      hovertemplate: `${methodName} Deviation: %{text:.2f}mm<br><extra></extra>`,
      text: sortedData.flatMap((point) => [
        point[`${methodName} distances`],
        point[`${methodName} distances`],
        null,
      ]),
    });

    return traces;
  };

  // 3D Plot erstellen
  const create3DPlot = (): Partial<PlotData>[] => {
    let plotData: Partial<PlotData>[] = [];

    if (
      metrics.ED.isLoaded &&
      metrics.ED.visible &&
      currentEDDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentEDDeviation, 'ED', methodColors.ED),
      );
    }
    if (
      metrics.SIDTW.isLoaded &&
      metrics.SIDTW.visible &&
      currentSIDTWDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentSIDTWDeviation, 'SIDTW', methodColors.SIDTW),
      );
    }

    const firstVisibleData =
      metrics.ED.isLoaded && metrics.ED.visible && currentEDDeviation?.length
        ? currentEDDeviation
        : metrics.SIDTW.isLoaded &&
            metrics.SIDTW.visible &&
            currentSIDTWDeviation?.length
          ? currentSIDTWDeviation
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
          metrics.ED.isLoaded && metrics.ED.visible ? 'ED' : 'SIDTW';

        // Start (grün)
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: 'Start',
          x: [firstPoint[`${methodPrefix}ActX`]],
          y: [firstPoint[`${methodPrefix}ActY`]],
          z: [firstPoint[`${methodPrefix}ActZ`]],
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
            'Start<br>X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<extra></extra>',
        });

        // End (rot)
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: 'End',
          x: [lastPoint[`${methodPrefix}ActX`]],
          y: [lastPoint[`${methodPrefix}ActY`]],
          z: [lastPoint[`${methodPrefix}ActZ`]],
          uirevision: 'true',
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
            'End<br>X: %{x:.2f}mm<br>Y: %{y:.2f}mm<br>Z: %{z:.2f}mm<extra></extra>',
        });
      }
    }

    return plotData;
  };

  // Layout für 3D Plot
  const get3DLayout = (): Partial<Layout> => ({
    title: {
      text:
        selectedSegment === 'total'
          ? '3D-Deviation (Trajectory)'
          : `3D-Deviation (Segment ${selectedSegment.split('_')[1]})`,
    },
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
      xaxis: { title: { text: 'X [mm]' }, showgrid: true, zeroline: true },
      yaxis: { title: { text: 'Y [mm]' }, showgrid: true, zeroline: true },
      zaxis: { title: { text: 'Z [mm]' }, showgrid: true, zeroline: true },
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
      <div className="rounded-lg border border-gray-500 bg-white p-4">
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
            No metric selected
          </div>
        )}
      </div>
    </div>
  );
};
