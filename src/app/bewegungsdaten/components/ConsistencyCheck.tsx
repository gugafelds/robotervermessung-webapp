'use client';

import React, { useEffect, useState } from 'react';

import type {
  BahnAccelIst,
  BahnEvents,
  BahnJointStates,
  BahnOrientationSoll,
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
  BahnTwistIst,
  BahnTwistSoll,
} from '@/types/bewegungsdaten.types';

interface ConsistencyCheckProps {
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  currentBahnTwistIst: BahnTwistIst[];
  currentBahnAccelIst: BahnAccelIst[];
  idealTrajectory: BahnPositionSoll[];
  currentBahnTwistSoll: BahnTwistSoll[];
  currentBahnOrientationSoll: BahnOrientationSoll[];
  currentBahnJointStates: BahnJointStates[];
  currentBahnEvents: BahnEvents[];
  isTransformed: boolean;
}

interface ConsistencyMetrics {
  dataPoints: number;
  avgInterval: number;
  stdDevInterval: number;
  maxGap: number;
  coefficientOfVariation: number;
  isTransformed: boolean;
}
export const ConsistencyCheck: React.FC<ConsistencyCheckProps> = ({
  currentBahnTwistIst,
  currentBahnTwistSoll,
  currentBahnPoseIst,
  idealTrajectory,
  currentBahnEvents,
  currentBahnOrientationSoll,
  currentBahnAccelIst,
  currentBahnJointStates,
  currentBahnPoseTrans,
  isTransformed,
}) => {
  const [metrics, setMetrics] = useState<Record<string, ConsistencyMetrics>>(
    {},
  );
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<{
    start: number;
    end: number;
  } | null>(null);

  useEffect(() => {
    const checkConsistency = () => {
      try {
        if (currentBahnEvents.length < 2) {
          throw new Error('Not enough events to define a range');
        }

        // Direkte Berechnung der Zeitbereiche
        let firstEventTime = Number.MAX_VALUE;
        let lastEventTime = Number.MIN_VALUE;

        currentBahnEvents.forEach((event) => {
          const timestamp = Number(event.timestamp);
          firstEventTime = Math.min(firstEventTime, timestamp);
          lastEventTime = Math.max(lastEventTime, timestamp);
        });

        setTimeRange({ start: firstEventTime, end: lastEventTime });

        const filterDataByTimeRange = <T extends { timestamp: string }>(
          data: T[],
        ): T[] => {
          return data.filter((item) => {
            const timestamp = Number(item.timestamp);
            return timestamp >= firstEventTime && timestamp <= lastEventTime;
          });
        };

        const dataArrays = {
          poseIst: isTransformed
            ? filterDataByTimeRange(currentBahnPoseTrans)
            : filterDataByTimeRange(currentBahnPoseIst),
          twistIst: filterDataByTimeRange(currentBahnTwistIst),
          accelIst: filterDataByTimeRange(currentBahnAccelIst),
          positionSoll: filterDataByTimeRange(idealTrajectory),
          orientationSoll: filterDataByTimeRange(currentBahnOrientationSoll),
          twistSoll: filterDataByTimeRange(currentBahnTwistSoll),
          jointStates: filterDataByTimeRange(currentBahnJointStates),
        };

        const newMetrics: Record<string, ConsistencyMetrics> = {};

        Object.entries(dataArrays).forEach(([key, data]) => {
          if (data.length > 1) {
            // Berechnung der Intervalle
            const intervals: number[] = [];
            // eslint-disable-next-line no-plusplus
            for (let i = 1; i < data.length; i++) {
              intervals.push(
                (Number(data[i].timestamp) - Number(data[i - 1].timestamp)) /
                  1e9,
              );
            }

            // Durchschnitt berechnen
            let sum = 0;
            intervals.forEach((interval) => {
              sum += interval;
            });
            const avgInterval = sum / intervals.length;

            // Standardabweichung berechnen
            let sumSquaredDiff = 0;
            intervals.forEach((interval) => {
              sumSquaredDiff += (interval - avgInterval) ** 2;
            });
            const stdDevInterval = Math.sqrt(sumSquaredDiff / intervals.length);

            // Maximum finden
            let maxGap = 0;
            intervals.forEach((interval) => {
              maxGap = Math.max(maxGap, interval);
            });

            const coefficientOfVariation = (stdDevInterval / avgInterval) * 100;

            newMetrics[key] = {
              dataPoints: data.length,
              avgInterval,
              stdDevInterval,
              maxGap,
              coefficientOfVariation,
              isTransformed,
            };
          } else {
            newMetrics[key] = {
              dataPoints: data.length,
              avgInterval: 0,
              stdDevInterval: 0,
              maxGap: 0,
              coefficientOfVariation: 0,
              isTransformed: false,
            };
          }
        });

        setMetrics(newMetrics);
        setError(null);
      } catch (e) {
        // eslint-disable-next-line @typescript-eslint/no-use-before-define
        setError(isError(e) ? e.message : 'An unknown error occurred');
      }
    };

    checkConsistency();
  }, [
    currentBahnTwistIst,
    currentBahnTwistSoll,
    currentBahnPoseIst,
    idealTrajectory,
    currentBahnEvents,
    currentBahnOrientationSoll,
    currentBahnAccelIst,
    currentBahnJointStates,
    currentBahnPoseTrans,
    isTransformed,
  ]);

  if (error) {
    return (
      <div className="mb-4 rounded-md border bg-red-100 p-4">
        <h2 className="mb-2 text-lg font-semibold">
          Fehler bei der Konsistenzprüfung
        </h2>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="mb-2 rounded-md border p-4">
      <h2 className="mb-2 text-lg font-semibold">Konsistenzmetriken</h2>
      {timeRange && (
        <p className="mb-2">
          Analyse durchgeführt für Daten zwischen{' '}
          {new Date(timeRange.start / 1e6).toISOString()} und{' '}
          {new Date(timeRange.end / 1e6).toISOString()}
        </p>
      )}
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            <th className="border border-gray-300 p-2">Datensatz</th>
            <th className="border border-gray-300 p-2">Datenpunkte</th>
            <th className="border border-gray-300 p-2">
              Durchschn. Intervall (s)
            </th>
            <th className="border border-gray-300 p-2">
              Standardabw. Intervall (s)
            </th>
            <th className="border border-gray-300 p-2">Max. Lücke (s)</th>
            <th className="border border-gray-300 p-2">
              Variationskoeffizient (%)
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(metrics).map(([key, metric]) => (
            <tr key={key}>
              <td className="border border-gray-300 p-2">{key}</td>
              <td className="border border-gray-300 p-2">
                {metric.dataPoints}
              </td>
              <td className="border border-gray-300 p-2">
                {metric.avgInterval.toFixed(4)}
              </td>
              <td className="border border-gray-300 p-2">
                {metric.stdDevInterval.toFixed(4)}
              </td>
              <td className="border border-gray-300 p-2">
                {metric.maxGap.toFixed(4)}
              </td>
              <td className="border border-gray-300 p-2">
                {metric.coefficientOfVariation.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function isError(error: unknown): error is Error {
  return error instanceof Error;
}
