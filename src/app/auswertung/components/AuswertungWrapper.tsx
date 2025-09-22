'use client';

import { Loader } from 'lucide-react';
import { useParams } from 'next/navigation';
import React, { useCallback, useEffect, useState } from 'react';

import { checkPositionDataAvailability } from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';
import { DeviationsPlot } from '@/src/app/auswertung/components/DeviationsPlot';
import { MetrikenPanel } from '@/src/app/auswertung/components/MetrikenPanel';
import { TrajectoryInfo } from '@/src/app/bewegungsdaten/components/TrajectoryInfo';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export function AuswertungWrapper() {
  const [hasDeviationData, setHasDeviationData] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

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

    setIsLoading(true);
    try {
      // Lade Bahn-Info direkt für diese ID
      // Prüfe, ob Abweichungsdaten verfügbar sind
      const hasData = await checkPositionDataAvailability(id);
      setHasDeviationData(hasData);
    } catch (error) {
      console.error('Fehler beim Laden der Bahndaten:', error);
    } finally {
      setIsLoading(false);
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

  if (isLoading) {
    return (
      <div className="flex h-fullscreen w-full flex-wrap justify-center overflow-scroll p-4">
        <div className="my-10 flex size-fit flex-col items-center justify-center rounded-xl bg-gray-200 p-2 shadow-sm">
          <div className="animate-spin">
            <Loader className="mx-auto w-10" color="#003560" />
          </div>
          <Typography as="h5">Es lädt...</Typography>
        </div>
      </div>
    );
  }

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
          bahnId={id}
          selectedSegment={selectedSegment}
          onSegmentChange={handleSegmentChange}
        />
      </div>
    </>
  );
}
