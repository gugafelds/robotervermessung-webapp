'use client';

import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useState } from 'react';

import {
  checkTransformedDataExists,
  getBahnAccelIstById,
  getBahnAccelSollById,
  getBahnEventsById,
  getBahnIMUById,
  getBahnInfoById,
  getBahnJointStatesById,
  getBahnOrientationSollById,
  getBahnPoseIstById,
  getBahnPoseTransById,
  getBahnPositionSollById,
  getBahnTwistIstById,
  getBahnTwistSollById,
} from '@/src/actions/bewegungsdaten.service';
import { TrajectoryInfo } from '@/src/app/bewegungsdaten/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/bewegungsdaten/components/TrajectoryPlot';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

const CACHE_DURATION = 1000 * 60 * 20;

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

const cache = new TimedCache();

interface DataLoadingState {
  pose: boolean;
  twist: boolean;
  accel: boolean;
  accelSoll: boolean;
  positionSoll: boolean;
  orientationSoll: boolean;
  twistSoll: boolean;
  jointStates: boolean;
  events: boolean;
  imu: boolean;
}

export function TrajectoryWrapper() {
  const params = useParams();
  const id = params?.id as string;
  const [isInfoLoaded, setIsInfoLoaded] = useState(false);
  const [loadingStates, setLoadingStates] = useState<DataLoadingState>({
    pose: false,
    twist: false,
    accel: false,
    accelSoll: false,
    positionSoll: false,
    orientationSoll: false,
    twistSoll: false,
    jointStates: false,
    events: false,
    imu: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [isTransformed, setIsTransformed] = useState(false);

  const plotAvailability = {
    position:
      loadingStates.positionSoll && loadingStates.pose && loadingStates.events,
    orientation:
      loadingStates.pose &&
      loadingStates.orientationSoll &&
      loadingStates.events,
    twist: loadingStates.twist && loadingStates.twistSoll,
    acceleration: loadingStates.accel && loadingStates.accelSoll,
    joints: loadingStates.jointStates,
  };

  const {
    currentBahnInfo,
    setCurrentBahnInfo,
    setCurrentBahnPoseIst,
    setCurrentBahnPoseTrans,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnAccelSoll,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnEvents,
    setCurrentBahnIMU,
  } = useTrajectory();

  const updateLoadingState = (key: keyof DataLoadingState, value: boolean) => {
    setLoadingStates((prev) => ({ ...prev, [key]: value }));
  };

  const fetchInfoData = useCallback(async () => {
    if (!id) return;

    try {
      const cacheKey = `info_${id}`;
      let bahnInfo = cache.get(cacheKey);

      if (!bahnInfo) {
        bahnInfo = await getBahnInfoById(id);
        cache.set(cacheKey, bahnInfo);
      }

      setCurrentBahnInfo(bahnInfo);
      setIsInfoLoaded(true);
    } catch (err) {
      setError('Bahninfo wurde nicht gefunden');
    }
  }, [id, setCurrentBahnInfo]);

  const fetchPlotData = useCallback(async () => {
    if (!id) return;

    const fetchDataWithCache = async <T,>(
      fetchFunction: () => Promise<T[]>,
      setter: (data: T[]) => void,
      cacheKey: string,
    ): Promise<void> => {
      const fullKey = `${cacheKey}_${id}`;

      // Versuch schnellen Cache-Zugriff
      const cachedData = cache.get(fullKey);
      if (cachedData) {
        setter(cachedData);
        return;
      }

      // Parallel: Daten holen und Cache setzen
      const data = await fetchFunction();
      setter(data);
      cache.set(fullKey, data);
    };

    try {
      const useTrans = await checkTransformedDataExists(id);
      setIsTransformed(useTrans);

      // Prioritätsgruppen für die Daten
      const highPriorityFetches = [
        // Pose Daten (höchste Priorität)
        useTrans
          ? fetchDataWithCache(
              () => getBahnPoseTransById(id),
              setCurrentBahnPoseTrans,
              'pose_trans',
            ).then(() => updateLoadingState('pose', true))
          : fetchDataWithCache(
              () => getBahnPoseIstById(id),
              setCurrentBahnPoseIst,
              'pose_ist',
            ).then(() => updateLoadingState('pose', true)),
        // Events werden auch sofort benötigt
        fetchDataWithCache(
          () => getBahnEventsById(id),
          setCurrentBahnEvents,
          'events',
        ).then(() => updateLoadingState('events', true)),
        fetchDataWithCache(
          () => getBahnPositionSollById(id),
          setCurrentBahnPositionSoll,
          'position_soll',
        ).then(() => updateLoadingState('positionSoll', true)),
        fetchDataWithCache(
          () => getBahnOrientationSollById(id),
          setCurrentBahnOrientationSoll,
          'orientation_soll',
        ).then(() => updateLoadingState('orientationSoll', true)),
      ];

      const mediumPriorityFetches = [
        fetchDataWithCache(
          () => getBahnJointStatesById(id),
          setCurrentBahnJointStates,
          'joint_states',
        ).then(() => updateLoadingState('jointStates', true)),
        fetchDataWithCache(
          () => getBahnTwistIstById(id),
          setCurrentBahnTwistIst,
          'twist_ist',
        ).then(() => updateLoadingState('twist', true)),
        fetchDataWithCache(
          () => getBahnTwistSollById(id),
          setCurrentBahnTwistSoll,
          'twist_soll',
        ).then(() => updateLoadingState('twistSoll', true)),
      ];

      const lowPriorityFetches = [
        fetchDataWithCache(
          () => getBahnAccelIstById(id),
          setCurrentBahnAccelIst,
          'accel_ist',
        ).then(() => updateLoadingState('accel', true)),
        fetchDataWithCache(
          () => getBahnAccelSollById(id),
          setCurrentBahnAccelSoll,
          'accel_soll',
        ).then(() => updateLoadingState('accelSoll', true)),

        fetchDataWithCache(
          () => getBahnIMUById(id),
          setCurrentBahnIMU,
          'imu',
        ).then(() => updateLoadingState('imu', true)),
      ];

      // Ausführung in Prioritätsgruppen
      await Promise.all(highPriorityFetches);
      await Promise.all(mediumPriorityFetches);
      await Promise.all(lowPriorityFetches);
    } catch (err) {
      setError('Plotdaten konnten nicht abgerufen werden');
    }
  }, [
    id,
    setCurrentBahnPoseTrans,
    setCurrentBahnAccelSoll,
    setCurrentBahnPoseIst,
    setCurrentBahnEvents,
    setCurrentBahnPositionSoll,
    setCurrentBahnOrientationSoll,
    setCurrentBahnTwistIst,
    setCurrentBahnAccelIst,
    setCurrentBahnTwistSoll,
    setCurrentBahnJointStates,
    setCurrentBahnIMU,
  ]);

  useEffect(() => {
    if (currentBahnInfo?.bahnID === id) {
      setIsInfoLoaded(true);
      return;
    }

    fetchInfoData();
  }, [id, fetchInfoData, currentBahnInfo]);

  useEffect(() => {
    if (!isInfoLoaded) {
      return;
    }

    fetchPlotData();
  }, [isInfoLoaded, fetchPlotData]);

  return error ? (
    <div className="flex h-fullscreen w-full flex-wrap justify-center overflow-scroll p-4">
      <div className="my-10 flex h-fit flex-col items-center justify-center rounded-xl bg-gray-200 p-2 shadow-sm">
        <Typography as="h5">Fehler: {error}</Typography>
      </div>
    </div>
  ) : (
    <>
      <TrajectoryInfo />
      <TrajectoryPlot
        isTransformed={isTransformed}
        plotAvailability={plotAvailability}
      />
    </>
  );
}
