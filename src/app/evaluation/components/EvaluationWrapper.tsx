'use client';

import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useState } from 'react';

import {
  checkOrientationDataAvailability,
  checkPositionDataAvailability,
} from '@/src/actions/evaluation.service';
import { getTrajInfoById } from '@/src/actions/motion.service';
import { DeviationsPlot } from '@/src/app/evaluation/components/DeviationsPlot';
import { MetricsPanel } from '@/src/app/evaluation/components/MetricsPanel';
import { TrajectoryInfo } from '@/src/app/motion/components/TrajectoryInfo';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export function EvaluationWrapper() {
  const [hasDeviationData, setHasDeviationData] = useState(false);
  const [hasOrientationData, setHasOrientationData] = useState(false);

  // Zentraler State für Segmentauswahl
  const [selectedSegment, setSelectedSegment] = useState<string>('total');

  const params = useParams();
  const id = params?.id as string;

  console.log("params:", params);

  const { currentTrajInfo, setCurrentTrajInfo } = useTrajectory();

  // Handler für Segmentauswahl - WICHTIG: useCallback verwenden!
  const handleSegmentChange = useCallback((segment: string) => {
    setSelectedSegment(segment);
  }, []);

  const loadBahnDetails = useCallback(async () => {
    if (!id) return;

    try {
      // Lade Bahn-Info direkt für diese ID
      // Prüfe, ob Abweichungsdaten verfügbar sind
      const hasData = await checkPositionDataAvailability(id);
      setHasDeviationData(hasData);
      const hasOrientationDataCheck =
        await checkOrientationDataAvailability(id);
      setHasOrientationData(hasOrientationDataCheck);
    } catch (error) {
      /* empty */
    }
  }, [id]);

  // Lade beim ersten Rendern und wenn sich die Bahn-ID ändert
  useEffect(() => {
    loadBahnDetails();
    // Reset segment selection when changing trajectory
    setSelectedSegment('total');
  }, [loadBahnDetails]);

  // Lade Bahn-Info wenn sie noch nicht geladen ist
  const fetchInfoData = useCallback(async () => {
    if (!id) return;

    try {
      const trajInfo = await getTrajInfoById(id);
      setCurrentTrajInfo(trajInfo);
    } catch (err) {
      /* empty */
    }
  }, [id, setCurrentTrajInfo]);

  useEffect(() => {
    if (currentTrajInfo?.trajID === id) {
      return;
    }

    fetchInfoData();
  }, [id, fetchInfoData, currentTrajInfo]);

  return (
    <>
      <TrajectoryInfo />

      <div className="h-fullscreen w-full flex-row justify-items-stretch overflow-y-auto p-2">
        <MetricsPanel
          trajID={id}
          selectedSegment={selectedSegment}
          onSegmentChange={handleSegmentChange}
        />
        <DeviationsPlot
          hasDeviationData={hasDeviationData}
          hasOrientationData={hasOrientationData}
          trajID={id}
          selectedSegment={selectedSegment}
        />
      </div>
    </>
  );
}
