'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React from 'react';

import { quaternionToEuler } from '@/src/lib/functions';
import type {
  BahnEvents,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPoseTrans,
} from '@/types/main';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface OrientationPlotProps {
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  currentBahnOrientationSoll: BahnOrientationSoll[];
  currentBahnEvents: BahnEvents[];
  isTransformed: boolean;
}

export const OrientationPlot: React.FC<OrientationPlotProps> = ({
  currentBahnPoseIst,
  currentBahnOrientationSoll,
  currentBahnPoseTrans,
  currentBahnEvents,
  isTransformed,
}) => {
  const createCombinedEulerAnglePlotData = (): {
    plotData: Partial<PlotData>[];
    maxTimeOrientation: number;
  } => {
    const currentPoseData = isTransformed
      ? currentBahnPoseTrans
      : currentBahnPoseIst;

    // Find the global start time
    const globalStartTime = Math.min(
      ...currentPoseData.map((bahn) => Number(bahn.timestamp)),
      ...currentBahnOrientationSoll.map((bahn) => Number(bahn.timestamp)),
      ...currentBahnEvents.map((bahn) => Number(bahn.timestamp)),
    );

    // Process Ist data
    const timestampsIst = currentPoseData.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });

    interface TransformedAngles {
      roll: number;
      pitch: number;
      yaw: number;
    }

    interface QuaternionAngles {
      angles: number[];
    }

    function isTransformedAngles(
      angles: TransformedAngles | QuaternionAngles,
    ): angles is TransformedAngles {
      return 'roll' in angles;
    }

    const eulerAnglesIst = isTransformed
      ? currentBahnPoseTrans.map(
          (bahn): TransformedAngles => ({
            roll: bahn.rollTrans,
            pitch: bahn.pitchTrans,
            yaw: bahn.yawTrans,
          }),
        )
      : currentBahnPoseIst.map(
          (bahn): QuaternionAngles => ({
            angles: quaternionToEuler(
              bahn.qxIst,
              bahn.qyIst,
              bahn.qzIst,
              bahn.qwIst,
            ),
          }),
        );

    // Process Soll data
    const timestampsSoll = currentBahnOrientationSoll.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });
    const eulerAnglesSoll = currentBahnOrientationSoll.map((bahn) =>
      quaternionToEuler(bahn.qxSoll, bahn.qySoll, bahn.qzSoll, bahn.qwSoll),
    );

    const eventEulerAngles = currentBahnEvents.map((event) => ({
      time: (Number(event.timestamp) - globalStartTime) / 1e9,
      angles: quaternionToEuler(
        event.qxReached,
        event.qyReached,
        event.qzReached,
        event.qwReached,
      ),
    }));

    const maxTimeOrientation = Math.max(...timestampsIst, ...timestampsSoll);

    const plotData: Partial<PlotData>[] = [
      // Roll (X-Rotation) - Blau-Töne wie X-Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Roll-Sollwinkel',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[0]),
        line: { color: 'blue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: isTransformed ? 'Roll-Transwinkel' : 'Roll-Istwinkel',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) =>
          isTransformedAngles(angles) ? angles.roll : angles.angles[0],
        ),
        line: { color: 'darkblue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Roll-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[0]),
        line: { color: 'lightblue', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Roll-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[0]),
        marker: { color: 'blue', size: 8, symbol: 'circle' },
      },

      // Pitch (Y-Rotation) - Grün-Töne wie Y-Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Pitch-Sollwinkel',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[1]),
        line: { color: 'green', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: isTransformed ? 'Pitch-Transwinkel' : 'Pitch-Istwinkel',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) =>
          isTransformedAngles(angles) ? angles.pitch : angles.angles[1],
        ),
        line: { color: 'darkgreen', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Pitch-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[1]),
        line: { color: 'lightgreen', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Pitch-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[1]),
        marker: { color: 'green', size: 8, symbol: 'circle' },
      },

      // Yaw (Z-Rotation) - Rot-Töne wie Z-Position
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Gier-Sollwinkel',
        x: timestampsSoll,
        y: eulerAnglesSoll.map((angles) => angles[2]),
        line: { color: 'red', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: isTransformed ? 'Gier-Transwinkel' : 'Gier-Istwinkel',
        x: timestampsIst,
        y: eulerAnglesIst.map((angles) =>
          isTransformedAngles(angles) ? angles.yaw : angles.angles[2],
        ),
        line: { color: 'darkred', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Gier-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[2]),
        line: { color: 'pink', width: 2, shape: 'hv' },
        showlegend: false,
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Gier-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[2]),
        marker: { color: 'red', size: 8, symbol: 'circle' },
      },
    ];
    return { plotData, maxTimeOrientation };
  };

  const { plotData: combinedEulerPlotData, maxTimeOrientation } =
    createCombinedEulerAnglePlotData();

  const combinedEulerLayout: Partial<Layout> = {
    title: 'Euler-Winkel',
    font: {
      family: 'Helvetica',
    },
    xaxis: {
      title: 's',
      tickformat: '.2f',
      range: [0, maxTimeOrientation],
    },
    yaxis: { title: '°' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'x unified',
  };

  return (
    <div className="w-full">
      <Plot
        data={combinedEulerPlotData}
        layout={combinedEulerLayout}
        useResizeHandler
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation'],
          responsive: true,
        }}
        style={{ width: '100%', height: '500px' }}
      />
    </div>
  );
};
