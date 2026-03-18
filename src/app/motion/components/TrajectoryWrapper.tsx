'use client';

import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getTrajAccelActById,
  getTrajAccelCmdById,
  getTrajInfoById,
  getTrajJointStatesById,
  getTrajOrientationCmdById,
  getTrajPoseActById,
  getTrajPositionCmdById,
  getTrajSetpointsById,
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
  poseAct: boolean;
  velAct: boolean;
  accelAct: boolean;
  accelCmd: boolean;
  positionCmd: boolean;
  orientationCmd: boolean;
  velCmd: boolean;
  jointStates: boolean;
  setpoints: boolean;
}

export function TrajectoryWrapper() {
  const params = useParams();
  const id = params?.id as string;
  const [isInfoLoaded, setIsInfoLoaded] = useState(false);
  const [loadingStates, setLoadingStates] = useState<DataLoadingState>({
    poseAct: false,
    velAct: false,
    accelAct: false,
    accelCmd: false,
    positionCmd: false,
    orientationCmd: false,
    velCmd: false,
    jointStates: false,
    setpoints: false,
  });
  const [error, setError] = useState<string | null>(null);

  const plotAvailability = useMemo(
    () => ({
      position:
        loadingStates.positionCmd &&
        loadingStates.poseAct &&
        loadingStates.setpoints,
      orientation:
        loadingStates.poseAct &&
        loadingStates.orientationCmd &&
        loadingStates.setpoints,
      velocity: loadingStates.velAct && loadingStates.velCmd,
      acceleration: loadingStates.accelAct && loadingStates.accelCmd,
      joints: loadingStates.jointStates,
    }),
    [loadingStates],
  );

  const {
    currentTrajInfo,
    setCurrentTrajInfo,
    setCurrentTrajPoseAct,
    setCurrentTrajVelAct,
    setCurrentTrajAccelAct,
    setCurrentTrajAccelCmd,
    setCurrentTrajPositionCmd,
    setCurrentTrajOrientationCmd,
    setCurrentTrajVelCmd,
    setCurrentTrajJointStates,
    setCurrentTrajSetpoints,
  } = useTrajectory();

  const updateLoadingState = useCallback(
    (key: keyof DataLoadingState, value: boolean) => {
      setLoadingStates((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const fetchInfoData = useCallback(async () => {
    if (!id) return;

    try {
      const cacheKey = `info_${id}`;
      let trajInfo = cache.get(cacheKey);

      if (!trajInfo) {
        trajInfo = await getTrajInfoById(id);
        cache.set(cacheKey, trajInfo);
      }

      setCurrentTrajInfo(trajInfo);
      setIsInfoLoaded(true);
    } catch (err) {
      setError('Traj. info could not be loaded.');
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
      // Prioritätsgruppen für die Daten
      const highPriorityFetches = [
        // Pose Daten (höchste Priorität)
        fetchDataWithCache(
          () => getTrajPoseActById(id),
          setCurrentTrajPoseAct,
          'pose_act',
        ).then(() => updateLoadingState('poseAct', true)),
        // Events werden auch sofort benötigt
        fetchDataWithCache(
          () => getTrajSetpointsById(id),
          setCurrentTrajSetpoints,
          'setpoints',
        ).then(() => updateLoadingState('setpoints', true)),
        fetchDataWithCache(
          () => getTrajPositionCmdById(id),
          setCurrentTrajPositionCmd,
          'position_cmd',
        ).then(() => updateLoadingState('positionCmd', true)),
        fetchDataWithCache(
          () => getTrajOrientationCmdById(id),
          setCurrentTrajOrientationCmd,
          'orientation_cmd',
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
          'vel_act',
        ).then(() => updateLoadingState('velAct', true)),
        fetchDataWithCache(
          () => getTrajVelCmdById(id),
          setCurrentTrajVelCmd,
          'vel_cmd',
        ).then(() => updateLoadingState('velCmd', true)),
      ];

      const lowPriorityFetches = [
        fetchDataWithCache(
          () => getTrajAccelActById(id),
          setCurrentTrajAccelAct,
          'accel_act',
        ).then(() => updateLoadingState('accelAct', true)),
        fetchDataWithCache(
          () => getTrajAccelCmdById(id),
          setCurrentTrajAccelCmd,
          'accel_cmd',
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
    setCurrentTrajPoseAct,
    setCurrentTrajSetpoints,
    setCurrentTrajPositionCmd,
    setCurrentTrajOrientationCmd,
    setCurrentTrajJointStates,
    setCurrentTrajVelAct,
    setCurrentTrajVelCmd,
    setCurrentTrajAccelAct,
    setCurrentTrajAccelCmd,
    updateLoadingState,
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
      <TrajectoryPlot plotAvailability={plotAvailability} />
    </>
  );
}
