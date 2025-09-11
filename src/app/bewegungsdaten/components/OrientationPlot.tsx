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
} from '@/types/bewegungsdaten.types';

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

    // Helper function to fix arrays of euler angles
    const fixGimbalLockBatch = (eulerAngles: number[][]): number[][] => {
      const eulerFixed = eulerAngles.map((row) => [...row]);

      for (let i = 0; i < 3; i += 1) {
        const angleColumn = eulerAngles.map((row) => row[i]);

        // Find discontinuities in the angle sequence
        const differences = [];
        // eslint-disable-next-line no-plusplus
        for (let j = 1; j < angleColumn.length; j++) {
          const diff = Math.abs(angleColumn[j] - angleColumn[j - 1]);
          if (diff > 180) {
            // Only consider large jumps
            differences.push(diff);
          }
        }

        // If we find significant jumps, they indicate potential gimbal lock
        if (differences.length > 0) {
          // Calculate the average jump size to determine threshold
          const avgJump =
            differences.reduce((a, b) => a + b, 0) / differences.length;
          const threshold = Math.min(avgJump / 2, 30); // Cap at 30 degrees to prevent over-correction

          // Apply correction with dynamic threshold
          angleColumn.forEach((angle, idx) => {
            if (Math.abs(Math.abs(angle) - 180) < threshold && angle < 0) {
              eulerFixed[idx][i] = angle + 360;
            }
          });
        }
      }

      return eulerFixed;
    };

    // Find the global start time
    const getGlobalStartTime = () => {
      let minTime = Number.MAX_VALUE;

      currentPoseData.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      currentBahnOrientationSoll.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      currentBahnEvents.forEach((bahn) => {
        minTime = Math.min(minTime, Number(bahn.timestamp));
      });

      return minTime;
    };

    const globalStartTime = getGlobalStartTime();

    // Process Ist data
    const timestampsIst = currentPoseData.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });

    const eulerAnglesIst = fixGimbalLockBatch(
      isTransformed
        ? currentBahnPoseTrans.map((bahn) =>
            quaternionToEuler(
              bahn.qxTrans,
              bahn.qyTrans,
              bahn.qzTrans,
              bahn.qwTrans,
            ),
          )
        : currentBahnPoseIst.map((bahn) =>
            quaternionToEuler(bahn.qxIst, bahn.qyIst, bahn.qzIst, bahn.qwIst),
          ),
    );

    // Process Soll data
    const timestampsSoll = currentBahnOrientationSoll.map((bahn) => {
      const elapsedNanoseconds = Number(bahn.timestamp) - globalStartTime;
      return elapsedNanoseconds / 1e9; // Convert to seconds
    });
    // Then modify where you process the SOLL data:
    const eulerAnglesSoll = fixGimbalLockBatch(
      currentBahnOrientationSoll.map((bahn) =>
        quaternionToEuler(bahn.qxSoll, bahn.qySoll, bahn.qzSoll, bahn.qwSoll),
      ),
    );

    const processedEulerAngles = fixGimbalLockBatch(
      currentBahnEvents.map((event) =>
        quaternionToEuler(
          event.qxReached,
          event.qyReached,
          event.qzReached,
          event.qwReached,
        ),
      ),
    );

    const eventEulerAngles = currentBahnEvents.map((event, index) => ({
      time: (Number(event.timestamp) - globalStartTime) / 1e9,
      angles: processedEulerAngles[index],
    }));

    const getMaxTimeOrientation = () => {
      let maxTime = 0;

      timestampsIst.forEach((time) => {
        maxTime = Math.max(maxTime, time);
      });

      timestampsSoll.forEach((time) => {
        maxTime = Math.max(maxTime, time);
      });

      return maxTime;
    };

    const maxTimeOrientation = getMaxTimeOrientation();

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
        y: eulerAnglesIst.map((angles) => angles[0]),
        line: { color: 'darkblue', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Roll-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[0]),
        marker: { color: 'blue', size: 12, symbol: 'circle' },
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
        y: eulerAnglesIst.map((angles) => angles[1]),
        line: { color: 'darkgreen', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Pitch-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[1]),
        marker: { color: 'green', size: 12, symbol: 'circle' },
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
        y: eulerAnglesIst.map((angles) => angles[2]),
        line: { color: 'darkred', width: 2 },
      },
      {
        type: 'scatter',
        mode: 'markers',
        name: 'Gier-Zielpunkte',
        x: eventEulerAngles.map((e) => e.time),
        y: eventEulerAngles.map((e) => e.angles[2]),
        marker: { color: 'red', size: 12, symbol: 'circle' },
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
        style={{ width: '100%', height: '500px' }}
      />
    </div>
  );
};
