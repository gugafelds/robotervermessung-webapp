'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useMemo } from 'react';

import { hasSupport, quaternionToEuler } from '@/src/lib/functions';
import type {
  TrajOrientationCmd,
  TrajPoseAct,
  TrajSetpoints,
} from '@/types/motion.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface OrientationPlotProps {
  currentTrajPoseAct: TrajPoseAct[];
  currentTrajOrientationCmd: TrajOrientationCmd[];
  currentTrajSetpoints: TrajSetpoints[];
  sim?: TrajOrientationCmd[];
  simSetpoints?: TrajSetpoints[];
}

export const OrientationPlot: React.FC<OrientationPlotProps> = React.memo(
  ({
    currentTrajPoseAct,
    currentTrajOrientationCmd,
    currentTrajSetpoints,
    sim,
    simSetpoints,
  }) => {
    const { plotData: combinedEulerPlotData, maxTimeOrientation } =
      useMemo((): {
        plotData: Partial<PlotData>[];
        maxTimeOrientation: number;
      } => {
        const currentPoseData = currentTrajPoseAct;

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

          currentPoseData.forEach((traj) => {
            minTime = Math.min(minTime, Number(traj.timestamp));
          });

          currentTrajOrientationCmd.forEach((traj) => {
            minTime = Math.min(minTime, Number(traj.timestamp));
          });

          currentTrajSetpoints.forEach((traj) => {
            minTime = Math.min(minTime, Number(traj.timestamp));
          });

          return minTime;
        };

        const globalStartTime = getGlobalStartTime();

        // Process Ist data
        const timestampsIst = currentPoseData.map((traj) => {
          const elapsedNanoseconds = Number(traj.timestamp) - globalStartTime;
          return elapsedNanoseconds / 1e9; // Convert to seconds
        });

        const eulerAnglesAct = fixGimbalLockBatch(
          currentTrajPoseAct.map((traj) =>
            quaternionToEuler(traj.qxAct, traj.qyAct, traj.qzAct, traj.qwAct),
          ),
        );

        // Process Soll data
        const timestampsSoll = currentTrajOrientationCmd.map((traj) => {
          const elapsedNanoseconds = Number(traj.timestamp) - globalStartTime;
          return elapsedNanoseconds / 1e9; // Convert to seconds
        });
        // Then modify where you process the SOLL data:
        const eulerAnglesSoll = fixGimbalLockBatch(
          currentTrajOrientationCmd.map((traj) =>
            quaternionToEuler(traj.qxCmd, traj.qyCmd, traj.qzCmd, traj.qwCmd),
          ),
        );

        const processedEulerAngles = fixGimbalLockBatch(
          currentTrajSetpoints.map((event) =>
            quaternionToEuler(
              event.qxReached,
              event.qyReached,
              event.qzReached,
              event.qwReached,
            ),
          ),
        );

        const withSupport = currentTrajSetpoints.filter(hasSupport);
        const processedSupportEulerAngles = fixGimbalLockBatch(
          withSupport.map((event) =>
            quaternionToEuler(
              event.qxSupport,
              event.qySupport,
              event.qzSupport,
              event.qwSupport,
            ),
          ),
        );

        const eventEulerAngles = currentTrajSetpoints.map((event, index) => ({
          time: (Number(event.timestamp) - globalStartTime) / 1e9,
          angles: processedEulerAngles[index],
        }));

        const supportEulerAngles = withSupport.map((event, index) => ({
          time: (Number(event.timestampSupport) - globalStartTime) / 1e9,
          angles: processedSupportEulerAngles[index],
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

        const timestampsSim = (sim ?? []).map(
          (traj) => (Number(traj.timestamp) - globalStartTime) / 1e9,
        );
        const eulerAnglesSim = fixGimbalLockBatch(
          (sim ?? []).map((traj) =>
            quaternionToEuler(traj.qxCmd, traj.qyCmd, traj.qzCmd, traj.qwCmd),
          ),
        );
        const computedMaxTimeOrientation = Math.max(
          getMaxTimeOrientation(),
          ...timestampsSim.slice(-1),
        );

        const plotData: Partial<PlotData>[] = [
          // Roll (X-Rotation) - Blau-Töne wie X-Position
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Roll (C)',
            x: timestampsSoll,
            y: eulerAnglesSoll.map((angles) => angles[0]),
            line: { color: 'blue', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Roll (M)',
            x: timestampsIst,
            y: eulerAnglesAct.map((angles) => angles[0]),
            line: { color: 'darkblue', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Roll (S)',
            x: eventEulerAngles.map((e) => e.time),
            y: eventEulerAngles.map((e) => e.angles[0]),
            marker: { color: 'blue', size: 12, symbol: 'circle' },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Roll (SP)',
            x: supportEulerAngles.map((e) => e.time),
            y: supportEulerAngles.map((e) => e.angles[0]),
            marker: { color: 'blue', size: 8, symbol: 'square' },
          },

          // Pitch (Y-Rotation) - Grün-Töne wie Y-Position
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Pitch (C)',
            x: timestampsSoll,
            y: eulerAnglesSoll.map((angles) => angles[1]),
            line: { color: 'green', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Pitch (M)',
            x: timestampsIst,
            y: eulerAnglesAct.map((angles) => angles[1]),
            line: { color: 'darkgreen', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Pitch (S)',
            x: eventEulerAngles.map((e) => e.time),
            y: eventEulerAngles.map((e) => e.angles[1]),
            marker: { color: 'green', size: 12, symbol: 'circle' },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Pitch (SP)',
            x: supportEulerAngles.map((e) => e.time),
            y: supportEulerAngles.map((e) => e.angles[1]),
            marker: { color: 'green', size: 8, symbol: 'square' },
          },

          // Yaw (Z-Rotation) - Rot-Töne wie Z-Position
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Yaw (C)',
            x: timestampsSoll,
            y: eulerAnglesSoll.map((angles) => angles[2]),
            line: { color: 'red', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Yaw (M)',
            x: timestampsIst,
            y: eulerAnglesAct.map((angles) => angles[2]),
            line: { color: 'darkred', width: 2 },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Yaw (S)',
            x: eventEulerAngles.map((e) => e.time),
            y: eventEulerAngles.map((e) => e.angles[2]),
            marker: { color: 'red', size: 12, symbol: 'circle' },
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Yaw (SP)',
            x: supportEulerAngles.map((e) => e.time),
            y: supportEulerAngles.map((e) => e.angles[2]),
            marker: { color: 'red', size: 8, symbol: 'square' },
          },
        ];
        if (sim) {
          (
            [
              ['Roll', 'blue'],
              ['Pitch', 'green'],
              ['Yaw', 'red'],
            ] as const
          ).forEach(([name, color], i) => {
            plotData.push({
              type: 'scatter',
              mode: 'lines',
              name: `${name} (Sim)`,
              x: timestampsSim,
              y: eulerAnglesSim.map((angles) => angles[i]),
              line: { color, width: 2, dash: 'dash' },
            });
          });

          const toEuler = (
            rows: TrajSetpoints[],
            kind: 'Reached' | 'Support',
          ) =>
            fixGimbalLockBatch(
              rows.map((e) =>
                quaternionToEuler(
                  e[`qx${kind}`],
                  e[`qy${kind}`],
                  e[`qz${kind}`],
                  e[`qw${kind}`],
                ),
              ),
            );
          const sps = simSetpoints ?? [];
          const reachedEuler = toEuler(sps, 'Reached');
          const simSupport = sps.filter(hasSupport);
          const supportEuler = toEuler(simSupport, 'Support');
          (
            [
              ['Roll', 'blue'],
              ['Pitch', 'green'],
              ['Yaw', 'red'],
            ] as const
          ).forEach(([name, color], i) => {
            plotData.push(
              {
                type: 'scatter',
                mode: 'markers',
                name: `${name} (Sim S)`,
                x: sps.map(
                  (e) => (Number(e.timestamp) - globalStartTime) / 1e9,
                ),
                y: reachedEuler.map((angles) => angles[i]),
                marker: {
                  color,
                  size: 12,
                  symbol: 'circle-open',
                  line: { width: 2 },
                },
              },
              {
                type: 'scatter',
                mode: 'markers',
                name: `${name} (Sim SP)`,
                x: simSupport.map(
                  (e) => (Number(e.timestampSupport) - globalStartTime) / 1e9,
                ),
                y: supportEuler.map((angles) => angles[i]),
                marker: {
                  color,
                  size: 8,
                  symbol: 'square-open',
                  line: { width: 2 },
                },
              },
            );
          });
        }
        return { plotData, maxTimeOrientation: computedMaxTimeOrientation };
      }, [
        currentTrajPoseAct,
        currentTrajOrientationCmd,
        currentTrajSetpoints,
        sim,
        simSetpoints,
      ]);

    const combinedEulerLayout: Partial<Layout> = {
      title: { text: 'Euler-Winkel' },
      font: {
        family: 'Helvetica',
      },
      xaxis: {
        title: { text: 's' },
        tickformat: '.2f',
        range: [0, maxTimeOrientation],
      },
      yaxis: { title: { text: '°' } },
      legend: { orientation: 'h', y: -0.2 },
      hovermode: 'x unified',
      uirevision: 'true',
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
  },
);

OrientationPlot.displayName = 'OrientationPlot';
