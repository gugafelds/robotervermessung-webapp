'use client';

import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useMemo } from 'react';

import type { TrajJointStates } from '@/types/motion.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface JointStatesPlotProps {
  currentTrajJointStates: TrajJointStates[];
  sim?: TrajJointStates[];
}

export const JointStatesPlot: React.FC<JointStatesPlotProps> = React.memo(
  ({ currentTrajJointStates, sim }) => {
    const { plotData: jointStatesPlotData, maxTimeJoints } = useMemo((): {
      plotData: Partial<PlotData>[];
      maxTimeJoints: number;
    } => {
      const getGlobalStartTime = () => {
        let minTime = Number.MAX_VALUE;
        currentTrajJointStates.forEach((traj) => {
          minTime = Math.min(minTime, Number(traj.timestamp));
        });
        return minTime;
      };

      const globalStartTime = getGlobalStartTime();

      // Process data
      const timestamps = currentTrajJointStates.map((traj) => {
        const elapsedNanoseconds = Number(traj.timestamp) - globalStartTime;
        return elapsedNanoseconds / 1e9; // Convert to seconds
      });

      // Optimierte Berechnung von maxTimeJoints
      const getMaxTimeJoints = () => {
        let maxTime = 0;
        timestamps.forEach((time) => {
          maxTime = Math.max(maxTime, time);
        });
        return maxTime;
      };

      const timestampsSim = (sim ?? []).map(
        (traj) => (Number(traj.timestamp) - globalStartTime) / 1e9,
      );
      const computedMaxTimeJoints = Math.max(
        getMaxTimeJoints(),
        ...timestampsSim.slice(-1),
      );

      const plotData: Partial<PlotData>[] = [
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint1),
          line: { color: 'red', width: 3 },
          name: 'Joint 1',
        },
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint2),
          line: { color: 'blue', width: 3 },
          name: 'Joint 2',
        },
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint3),
          line: { color: 'green', width: 3 },
          name: 'Joint 3',
        },
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint4),
          line: { color: 'purple', width: 3 },
          name: 'Joint 4',
        },
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint5),
          line: { color: 'orange', width: 3 },
          name: 'Joint 5',
        },
        {
          type: 'scatter',
          mode: 'lines',
          x: timestamps,
          y: currentTrajJointStates.map((traj) => traj.joint6),
          line: { color: 'brown', width: 3 },
          name: 'Joint 6',
        },
      ];

      if (sim) {
        const colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown'];
        colors.forEach((color, i) => {
          plotData.push({
            type: 'scatter',
            mode: 'lines',
            x: timestampsSim,
            y: sim.map(
              (traj) =>
                traj[`joint${i + 1}` as keyof TrajJointStates] as number,
            ),
            line: { color, width: 2, dash: 'dash' },
            name: `Joint ${i + 1} (Sim)`,
          });
        });
      }

      return {
        plotData,
        maxTimeJoints: computedMaxTimeJoints,
      };
    }, [currentTrajJointStates, sim]);

    const jointStatesLayout: Partial<Layout> = {
      title: { text: 'Joint States' },
      font: {
        family: 'Helvetica',
      },
      xaxis: {
        title: { text: 's' },
        tickformat: '.2f',
        range: [0, maxTimeJoints],
      },
      yaxis: { title: { text: '°' } },
      legend: { orientation: 'h', y: -0.2 },
      hovermode: 'x unified',
      uirevision: 'true',
    };

    return (
      <div className="w-full">
        <Plot
          data={jointStatesPlotData}
          layout={jointStatesLayout}
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
            ],
            responsive: true,
          }}
          style={{ width: '100%', height: '500px' }}
        />
      </div>
    );
  },
);

JointStatesPlot.displayName = 'JointStatesPlot';
