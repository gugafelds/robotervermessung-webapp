'use client';

import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useState } from 'react';

import {
  checkTransformedDataExists,
  getTrajAccelActById,
  getTrajAccelCmdById,
  getTrajEventsById,
  getTrajInfoById,
  getTrajJointStatesById,
  getTrajOrientationCmdById,
  getTrajPoseActById,
  getTrajPoseTransById,
  getTrajPositionCmdById,
  getTrajVelActById,
  getTrajVelCmdById,
} from '@/src/actions/motion.service';
import { TrajectoryInfo } from '@/src/app/motion/components/TrajectoryInfo';
import { TrajectoryPlot } from '@/src/app/motion/components/TrajectoryPlot';
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
  accelCmd: boolean;
  positionCmd: boolean;
  orientationCmd: boolean;
  twistCmd: boolean;
  jointStates: boolean;
  events: boolean;
}

export function TrajectoryWrapper() {
  const params = useParams();
  const id = params?.id as string;
  const [isInfoLoaded, setIsInfoLoaded] = useState(false);
  const [loadingStates, setLoadingStates] = useState<DataLoadingState>({
    pose: false,
    twist: false,
    accel: false,
    accelCmd: false,
    positionCmd: false,
    orientationCmd: false,
    twistCmd: false,
    jointStates: false,
    events: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [isTransformed, setIsTransformed] = useState(false);

  const plotAvailability = {
    position:
      loadingStates.positionCmd && loadingStates.pose && loadingStates.events,
    orientation:
      loadingStates.pose &&
      loadingStates.orientationCmd &&
      loadingStates.events,
    twist: loadingStates.twist && loadingStates.twistCmd,
    acceleration: loadingStates.accel && loadingStates.accelCmd,
    joints: loadingStates.jointStates,
  };

  const {
    currentTrajInfo,
    setCurrentTrajInfo,
    setCurrentTrajPoseAct,
    setCurrentTrajPoseTrans,
    setCurrentTrajVelAct,
    setCurrentTrajAccelAct,
    setCurrentTrajAccelCmd,
    setCurrentTrajPositionCmd,
    setCurrentTrajOrientationCmd,
    setCurrentTrajVelCmd,
    setCurrentTrajJointStates,
    setCurrentTrajSetpoints,
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
        bahnInfo = await getTrajInfoById(id);
        cache.set(cacheKey, bahnInfo);
      }

      setCurrentTrajInfo(bahnInfo);
      setIsInfoLoaded(true);
    } catch (err) {
      setError('Trajinfo wurde nicht gefunden');
    }
  }, [id, setCurrentTrajInfo]);

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
              () => getTrajPoseTransById(id),
              setCurrentTrajPoseTrans,
              'pose_trans',
            ).then(() => updateLoadingState('pose', true))
          : fetchDataWithCache(
              () => getTrajPoseActById(id),
              setCurrentTrajPoseAct,
              'pose_ist',
            ).then(() => updateLoadingState('pose', true)),
        // Events werden auch sofort benötigt
        fetchDataWithCache(
          () => getTrajEventsById(id),
          setCurrentTrajSetpoints,
          'events',
        ).then(() => updateLoadingState('events', true)),
        fetchDataWithCache(
          () => getTrajPositionCmdById(id),
          setCurrentTrajPositionCmd,
          'position_soll',
        ).then(() => updateLoadingState('positionCmd', true)),
        fetchDataWithCache(
          () => getTrajOrientationCmdById(id),
          setCurrentTrajOrientationCmd,
          'orientation_soll',
        ).then(() => updateLoadingState('orientationCmd', true)),
      ];

      const mediumPriorityFetches = [
        fetchDataWithCache(
          () => getTrajJointStatesById(id),
          setCurrentTrajJointStates,
          'joint_states',
        ).then(() => updateLoadingState('jointStates', true)),
        fetchDataWithCache(
          () => getTrajVelActById(id),
          setCurrentTrajVelAct,
          'twist_ist',
        ).then(() => updateLoadingState('twist', true)),
        fetchDataWithCache(
          () => getTrajVelCmdById(id),
          setCurrentTrajVelCmd,
          'twist_soll',
        ).then(() => updateLoadingState('twistCmd', true)),
      ];

      const lowPriorityFetches = [
        fetchDataWithCache(
          () => getTrajAccelActById(id),
          setCurrentTrajAccelAct,
          'accel_ist',
        ).then(() => updateLoadingState('accel', true)),
        fetchDataWithCache(
          () => getTrajAccelCmdById(id),
          setCurrentTrajAccelCmd,
          'accel_soll',
        ).then(() => updateLoadingState('accelCmd', true)),
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
    setCurrentTrajPoseTrans,
    setCurrentTrajAccelCmd,
    setCurrentTrajPoseAct,
    setCurrentTrajSetpoints,
    setCurrentTrajPositionCmd,
    setCurrentTrajOrientationCmd,
    setCurrentTrajVelAct,
    setCurrentTrajAccelAct,
    setCurrentTrajVelCmd,
    setCurrentTrajJointStates,
  ]);

  useEffect(() => {
    if (currentTrajInfo?.trajID === id) {
      setIsInfoLoaded(true);
      return;
    }

    fetchInfoData();
  }, [id, fetchInfoData, currentTrajInfo]);

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
