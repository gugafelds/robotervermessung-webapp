'use client';

import { useParams } from 'next/navigation';
import PQueue from 'p-queue';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import {
  checkTransformedDataExists,
  getBahnAccelIstById,
  getBahnEventsById,
  getBahnInfoById,
  getBahnJointStatesById,
  getBahnOrientationSollById,
  getBahnPoseIstById,
  getBahnPoseTransById,
  getBahnPositionSollById,
  getBahnTwistIstById,
  getBahnTwistSollById,
} from '@/src/actions/bewegungsdaten.service';
import { TrajectoryInfo } from '@/src/app/trajectories/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/trajectories/components/TrajectoryPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

const CHUNK_SIZE = 5000;
const BATCH_SIZE = 3;
const CACHE_DURATION = 1000 * 60 * 15;

interface CacheItem {
  data: any;
  timestamp: number;
}

class TimedCache {
  private cache = new Map<string, CacheItem>();

  set(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  get(key: string): any | null {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > CACHE_DURATION) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }
}

const ProgressBar = ({ value }: { value: number }) => (
  <div className="h-2.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
    <div
      className="h-2.5 rounded-full bg-blue-600"
      style={{ width: `${value}%` }}
    />
  </div>
);

const queue = new PQueue({
  concurrency: BATCH_SIZE,
  interval: 1000,
  intervalCap: 10,
  timeout: 60000,
});

const cache = new TimedCache();

const processInChunks = async <T,>(
  data: T[],
  processChunk: (chunk: T[]) => void,
  signal?: AbortSignal,
  chunkSize: number = CHUNK_SIZE,
): Promise<void> => {
  const chunks = [];
  for (let i = 0; i < data.length; i += chunkSize) {
    chunks.push(data.slice(i, i + chunkSize));
  }

  await Promise.all(
    chunks.map(async (chunk) => {
      if (signal?.aborted) {
        throw new Error('Processing aborted');
      }
      processChunk(chunk);
      return new Promise((resolve) => {
        setTimeout(resolve, 0);
      });
    }),
  );
};

export function TrajectoryWrapper() {
  const params = useParams();
  const id = params?.id as string;
  const [isInfoLoaded, setIsInfoLoaded] = useState(false);
  const [isPlotDataLoaded, setIsPlotDataLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [isTransformed, setIsTransformed] = useState(false);
  const latestInfoRequestId = useRef<string | null>(null);
  const latestPlotRequestId = useRef<string | null>(null);

  const {
    currentBahnInfo,
    setCurrentBahnInfo,
    setCurrentBahnPoseIst,
    setCurrentBahnPoseTrans,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
  } = useTrajectory();

  const fetchInfoData = useCallback(
    async (signal: AbortSignal, requestId: string) => {
      if (!id) return;

      try {
        const cacheKey = `info_${id}`;
        let bahnInfo = cache.get(cacheKey);

        if (!bahnInfo) {
          bahnInfo = await getBahnInfoById(id);
          cache.set(cacheKey, bahnInfo);
        }

        if (requestId === latestInfoRequestId.current && !signal.aborted) {
          setCurrentBahnInfo(bahnInfo);
          setIsInfoLoaded(true);
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (requestId === latestInfoRequestId.current) {
          setError('Failed to fetch Bahn info');
        }
      }
    },
    [id, setCurrentBahnInfo],
  );

  const fetchDataWithProgress = async <T,>(
    fetchFunction: () => Promise<T[]>,
    setter: (data: T[]) => void,
    signal: AbortSignal,
    cacheKey: string,
  ): Promise<T[]> => {
    const cachedData = cache.get(cacheKey);
    if (cachedData) {
      setter(cachedData);
      return cachedData;
    }

    const data = await fetchFunction();
    const processedData: T[] = [];

    await processInChunks(
      data,
      (chunk) => {
        processedData.push(...chunk);
        setter([...processedData]);
      },
      signal,
    );

    cache.set(cacheKey, processedData);
    return processedData;
  };

  type FetchFunction<T> = () => Promise<T[]>;

  const fetchPlotData = useCallback(
    async (signal: AbortSignal, requestId: string) => {
      if (!id) return;

      try {
        const useTrans = await checkTransformedDataExists(id);
        setIsTransformed(useTrans);

        type FetchConfig<T> = {
          func: FetchFunction<T>;
          setter: (data: T[]) => void;
          key: string;
          priority: number;
        };

        const fetchConfigs: FetchConfig<any>[] = [
          {
            func: () =>
              (useTrans
                ? getBahnPoseTransById(id)
                : getBahnPoseIstById(id)) as Promise<any>,
            setter: useTrans ? setCurrentBahnPoseTrans : setCurrentBahnPoseIst,
            key: useTrans ? 'pose_trans' : 'pose_ist',
            priority: 1,
          },
          {
            func: () => getBahnTwistIstById(id),
            setter: setCurrentBahnTwistIst,
            key: 'twist_ist',
            priority: 2,
          },
          {
            func: () => getBahnAccelIstById(id),
            setter: setCurrentBahnAccelIst,
            key: 'accel_ist',
            priority: 3,
          },
          {
            func: () => getBahnPositionSollById(id),
            setter: setCurrentBahnPositionSoll,
            key: 'position_soll',
            priority: 4,
          },
          {
            func: () => getBahnOrientationSollById(id),
            setter: setCurrentBahnOrientationSoll,
            key: 'orientation_soll',
            priority: 5,
          },
          {
            func: () => getBahnTwistSollById(id),
            setter: setCurrentBahnTwistSoll,
            key: 'twist_soll',
            priority: 6,
          },
          {
            func: () => getBahnJointStatesById(id),
            setter: setCurrentBahnJointStates,
            key: 'joint_states',
            priority: 7,
          },
          {
            func: () => getBahnEventsById(id),
            setter: setCurrentBahnEvents,
            key: 'events',
            priority: 8,
          },
        ];

        const totalConfigs = fetchConfigs.length;
        let completedCount = 0;

        await Promise.all(
          fetchConfigs.map(({ func, setter, key, priority }) =>
            queue.add(
              async () => {
                if (signal.aborted) return;

                try {
                  await fetchDataWithProgress(
                    func,
                    setter,
                    signal,
                    `${key}_${id}`,
                  );
                } finally {
                  completedCount += 1;
                  setLoadingProgress((completedCount / totalConfigs) * 100);
                }
              },
              { priority },
            ),
          ),
        );

        if (requestId === latestPlotRequestId.current && !signal.aborted) {
          setIsPlotDataLoaded(true);
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (requestId === latestPlotRequestId.current) {
          setError('Failed to fetch plot data');
        }
      }
    },
    [
      id,
      setCurrentBahnPoseIst,
      setCurrentBahnPoseTrans,
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
    const loadInfo = async () => {
      if (currentBahnInfo?.bahnID === id) {
        setIsInfoLoaded(true);
        return undefined;
      }

      const abortController = new AbortController();
      const requestId = Date.now().toString();
      latestInfoRequestId.current = requestId;

      setIsInfoLoaded(false);
      setError(null);
      await fetchInfoData(abortController.signal, requestId);
      return () => abortController.abort();
    };

    const cleanup = loadInfo();
    return () => {
      cleanup?.then((fn) => fn?.());
    };
  }, [id, fetchInfoData, currentBahnInfo]);

  useEffect(() => {
    const loadPlotData = async () => {
      if (!isInfoLoaded || isPlotDataLoaded) {
        return undefined;
      }

      const abortController = new AbortController();
      const requestId = Date.now().toString();
      latestPlotRequestId.current = requestId;

      setError(null);
      await fetchPlotData(abortController.signal, requestId);
      return () => abortController.abort();
    };

    const cleanup = loadPlotData();
    return () => {
      cleanup?.then((fn) => fn?.());
    };
  }, [isInfoLoaded, fetchPlotData, isPlotDataLoaded]);

  return error ? (
    <div>Error: {error}</div>
  ) : (
    <>
      <TrajectoryInfo isTransformed={isTransformed} />
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
        <TrajectoryPlot isTransformed={isTransformed} />
      )}
    </>
  );
}
