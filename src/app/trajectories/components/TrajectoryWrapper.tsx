/* eslint-disable no-console */

'use client';

import { useParams } from 'next/navigation';
import PQueue from 'p-queue';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import {
  getBahnAccelIstById,
  getBahnEventsById,
  getBahnInfoById,
  getBahnJointStatesById,
  getBahnOrientationSollById,
  getBahnPoseIstById,
  getBahnPositionSollById,
  getBahnTwistIstById,
  getBahnTwistSollById,
} from '@/src/actions/bewegungsdaten.service';
import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

const ProgressBar = ({ value }: { value: number }) => (
  <div className="h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
    <div
      className="h-2.5 rounded-full bg-blue-600"
      style={{ width: `${value}%` }}
    />
  </div>
);

// Create a new queue with a concurrency of 3
const queue = new PQueue({ concurrency: 5 });

export function TrajectoryWrapper() {
  const params = useParams();
  const id = params?.id as string;
  const [isInfoLoaded, setIsInfoLoaded] = useState(false);
  const [isPlotDataLoaded, setIsPlotDataLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestInfoRequestId = useRef<string | null>(null);
  const latestPlotRequestId = useRef<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(0);

  const {
    setCurrentBahnInfo,
    setCurrentBahnPoseIst,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
  } = useTrajectory();

  const clearPlotData = useCallback(() => {
    setCurrentBahnPoseIst([]);
    setCurrentBahnTwistIst([]);
    setCurrentBahnAccelIst([]);
    setCurrentBahnPositionSoll([]);
    setCurrentBahnOrientationSoll([]);
    setCurrentBahnTwistSoll([]);
    setCurrentBahnJointStates([]);
    setCurrentBahnEvents([]);
    setIsPlotDataLoaded(false);
    setLoadingProgress(0);
  }, [
    setCurrentBahnPoseIst,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
  ]);

  const fetchInfoData = useCallback(
    async (signal: AbortSignal, requestId: string) => {
      if (!id) return;

      try {
        const bahnInfo = await getBahnInfoById(id);
        if (requestId === latestInfoRequestId.current) {
          setCurrentBahnInfo(bahnInfo);
          setIsInfoLoaded(true);
        }
        // eslint-disable-next-line @typescript-eslint/no-shadow
      } catch (error: any) {
        if (error.name === 'AbortError') {
          console.log('Info fetch aborted');
        } else {
          console.error('Error fetching Bahn info:', error);
          if (requestId === latestInfoRequestId.current) {
            setError('Failed to fetch Bahn info');
          }
        }
      }
    },
    [id, setCurrentBahnInfo],
  );

  const fetchPlotData = useCallback(
    async (signal: AbortSignal, requestId: string) => {
      if (!id) return;

      console.log('Fetching plot data');

      type SetterFunction<T> = (value: T) => void;

      interface FetchFunction<T> {
        func: (id: string) => Promise<T>;
        setter: SetterFunction<T>;
      }

      const fetchFunctions: FetchFunction<any>[] = [
        { func: getBahnPoseIstById, setter: setCurrentBahnPoseIst },
        { func: getBahnTwistIstById, setter: setCurrentBahnTwistIst },
        { func: getBahnAccelIstById, setter: setCurrentBahnAccelIst },
        { func: getBahnPositionSollById, setter: setCurrentBahnPositionSoll },
        {
          func: getBahnOrientationSollById,
          setter: setCurrentBahnOrientationSoll,
        },
        { func: getBahnTwistSollById, setter: setCurrentBahnTwistSoll },
        { func: getBahnJointStatesById, setter: setCurrentBahnJointStates },
        { func: getBahnEventsById, setter: setCurrentBahnEvents },
      ];

      const totalFunctions = fetchFunctions.length;
      let completedFunctions = 0;

      const updateProgress = () => {
        completedFunctions += 1;
        setLoadingProgress((completedFunctions / totalFunctions) * 100);
      };

      const fetchPromises = fetchFunctions.map(({ func, setter }) =>
        queue.add(() =>
          func(id)
            .then((data) => {
              if (
                requestId === latestPlotRequestId.current &&
                !signal.aborted
              ) {
                setter(data);
                updateProgress();
              }
            })
            .catch((fetchError) => {
              console.error(`Error fetching data: ${fetchError}`);
              updateProgress();
              return null;
            }),
        ),
      );

      try {
        await Promise.all(fetchPromises);
        if (requestId === latestPlotRequestId.current && !signal.aborted) {
          setIsPlotDataLoaded(true);
        }
      } catch (fetchError: any) {
        if (fetchError.name === 'AbortError') {
          console.log('Plot data fetch aborted');
        } else {
          console.error('Error fetching plot data:', fetchError);
          if (requestId === latestPlotRequestId.current) {
            setError('Failed to fetch some plot data');
          }
        }
      }
    },
    [
      id,
      setCurrentBahnPoseIst,
      setCurrentBahnTwistIst,
      setCurrentBahnAccelIst,
      setCurrentBahnPositionSoll,
      setCurrentBahnOrientationSoll,
      setCurrentBahnTwistSoll,
      setCurrentBahnJointStates,
      setCurrentBahnEvents,
    ],
  );

  useEffect(() => {
    console.log('Info effect running, id:', id);
    const abortController = new AbortController();
    const requestId = Date.now().toString();
    latestInfoRequestId.current = requestId;

    setIsInfoLoaded(false);
    setError(null);
    clearPlotData();
    fetchInfoData(abortController.signal, requestId);

    return () => {
      abortController.abort();
    };
  }, [id, fetchInfoData, clearPlotData]);

  useEffect(() => {
    console.log('Plot data effect running, isInfoLoaded:', isInfoLoaded);
    let abortController: AbortController | null = null;

    if (isInfoLoaded) {
      abortController = new AbortController();
      const requestId = Date.now().toString();
      latestPlotRequestId.current = requestId;

      setIsPlotDataLoaded(false);
      setError(null);
      clearPlotData();
      fetchPlotData(abortController.signal, requestId);
    }

    return () => {
      if (abortController) {
        abortController.abort();
      }
    };
  }, [isInfoLoaded, fetchPlotData, clearPlotData]);

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <>
      <TrajectoryInfo />
      {!isPlotDataLoaded ? (
        <div className="m-10 flex h-full flex-col justify-normal overflow-hidden align-middle">
          <Typography as="h2">plotdaten werden heruntergeladen...</Typography>
          <div className="mt-4 w-64">
            <ProgressBar value={loadingProgress} />
          </div>
          <Typography as="p" className="mt-2">
            {Math.round(loadingProgress)}%
          </Typography>
        </div>
      ) : (
        <TrajectoryPlot />
      )}
    </>
  );
}
