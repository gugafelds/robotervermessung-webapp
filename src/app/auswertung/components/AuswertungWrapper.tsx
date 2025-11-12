'use client';

import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useState } from 'react';

import {
  checkOrientationDataAvailability,
  checkPositionDataAvailability,
} from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';
import { DeviationsPlot } from '@/src/app/auswertung/components/DeviationsPlot';
import { MetrikenPanel } from '@/src/app/auswertung/components/MetrikenPanel';
import { TrajectoryInfo } from '@/src/app/bewegungsdaten/components/TrajectoryInfo';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export function AuswertungWrapper() {
  const [hasDeviationData, setHasDeviationData] = useState(false);
  const [hasOrientationData, setHasOrientationData] = useState(false);

  // Zentraler State für Segmentauswahl
  const [selectedSegment, setSelectedSegment] = useState<string>('total');

  const params = useParams();
  const id = params?.id as string;

  const { currentBahnInfo, setCurrentBahnInfo } = useTrajectory();

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
      const bahnInfo = await getBahnInfoById(id);
      setCurrentBahnInfo(bahnInfo);
    } catch (err) {
      /* empty */
    }
  }, [id, setCurrentBahnInfo]);

  useEffect(() => {
    if (currentBahnInfo?.bahnID === id) {
      return; // Bahn-Info bereits geladen
    }

    fetchInfoData();
  }, [id, fetchInfoData, currentBahnInfo]);

  return (
    <>
      <TrajectoryInfo />

      <div className="h-fullscreen w-full flex-row justify-items-stretch overflow-y-auto p-2">
        <MetrikenPanel
          bahnId={id}
          selectedSegment={selectedSegment}
          onSegmentChange={handleSegmentChange}
        />
        <DeviationsPlot
          hasDeviationData={hasDeviationData}
          hasOrientationData={hasOrientationData}
          bahnId={id}
          selectedSegment={selectedSegment}
        />
      </div>
    </>
  );
}
