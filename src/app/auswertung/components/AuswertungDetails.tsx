/* eslint-disable no-console */

'use client';

import { InformationCircleIcon } from '@heroicons/react/24/outline';
import { Loader } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

import { checkPositionDataAvailability } from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';
import { DeviationsPlot } from '@/src/app/auswertung/components/DeviationsPlot';
import { MetrikenPanel } from '@/src/app/auswertung/components/MetrikenPanel';
import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber } from '@/src/lib/functions';
import type { BahnInfo } from '@/types/bewegungsdaten.types';

interface InfoGridItemProps {
  label: string;
  value: React.ReactNode;
}

const InfoGridItem: React.FC<InfoGridItemProps> = ({ label, value }) => (
  <div className="flex flex-col space-y-1">
    <span className="text-sm text-gray-500">{label}</span>
    <span className="font-medium text-gray-900">{value}</span>
  </div>
);

interface AuswertungDetailsProps {
  bahnId: string;
}

export const AuswertungDetails = ({ bahnId }: AuswertungDetailsProps) => {
  const [hasDeviationData, setHasDeviationData] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentBahn, setCurrentBahn] = useState<BahnInfo | null>(null);

  // Lade die Details-Daten für die ausgewählte Bahn
  const loadBahnDetails = useCallback(async () => {
    if (!bahnId) return;

    setIsLoading(true);
    try {
      // Lade Bahn-Info direkt für diese ID
      const foundBahn = await getBahnInfoById(bahnId);

      setCurrentBahn(foundBahn);

      // Prüfe, ob Abweichungsdaten verfügbar sind
      const hasData = await checkPositionDataAvailability(bahnId);
      setHasDeviationData(hasData);
    } catch (error) {
      console.error('Fehler beim Laden der Bahndaten:', error);
    } finally {
      setIsLoading(false);
    }
  }, [bahnId]);

  // Lade beim ersten Rendern und wenn sich die Bahn-ID ändert
  useEffect(() => {
    loadBahnDetails();
  }, [loadBahnDetails]);

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
  if (!currentBahn) {
    return (
      <div className="m-10 flex h-full flex-col justify-normal overflow-hidden rounded-md bg-gray-50 p-5 align-middle">
        <Typography as="h3">
          Fehler: Auswertungsdaten der Bahn nicht gefunden :(
        </Typography>
      </div>
    );
  }

  return (
    <div className="flex h-fullscreen w-full flex-col overflow-scroll p-6">
      {/* Extended Header Section */}
      <div className="mb-2 space-y-2 rounded-lg border bg-white p-6 shadow-sm">
        {/* Main Info */}
        <div className="border-b pb-4">
          <Typography as="h1" className="text-2xl font-bold text-primary">
            Bahn ID: {currentBahn.bahnID}
          </Typography>
          <Typography as="h2" className="text-xl text-gray-600">
            {currentBahn.recordFilename || 'Keine Datei'}
          </Typography>
          <Typography as="p" className="text-gray-500">
            {formatDate(currentBahn.recordingDate)}
          </Typography>
        </div>

        {/* Additional Info */}
        <div className="space-y-2">
          {/* Allgemeine Informationen */}
          <div>
            <div className="mb-1 flex items-center gap-2">
              <InformationCircleIcon className="size-5 text-primary" />
              <h3 className="font-semibold text-primary">
                Allgemeine Informationen
              </h3>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <InfoGridItem
                label="Roboter"
                value={currentBahn.robotModel || 'n. a.'}
              />
              <InfoGridItem
                label="Quelle-Ist"
                value={currentBahn.sourceDataIst || 'n. a.'}
              />
              <InfoGridItem
                label="Quelle-Soll"
                value={currentBahn.sourceDataSoll || 'n. a.'}
              />
              <InfoGridItem
                label="Bahndauer"
                value={
                  currentBahn.startTime && currentBahn.endTime
                    ? `${((new Date(currentBahn.endTime).getTime() - new Date(currentBahn.startTime).getTime()) / 1000).toFixed(1)}s`
                    : 'n. a.'
                }
              />
              <InfoGridItem
                label="Start"
                value={
                  currentBahn.startTime
                    ? formatDate(currentBahn.startTime)
                    : 'n. a.'
                }
              />
              <InfoGridItem
                label="Ende"
                value={
                  currentBahn.endTime
                    ? formatDate(currentBahn.endTime)
                    : 'n. a.'
                }
              />
              <InfoGridItem
                label="Last"
                value={`${formatNumber(currentBahn.weight) || '-'} kg`}
              />
            </div>
          </div>

          {/* Abtastraten */}
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h3 className="font-semibold text-primary">Abtastraten</h3>
            </div>

            {/* Ist-Daten Gruppe */}
            <div className="mb-4">
              <div className="mb-2 text-lg font-semibold text-gray-600">
                Ist-Daten:
              </div>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <InfoGridItem
                  label="Pose"
                  value={`${formatNumber(currentBahn.frequencyPoseIst) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Geschwindigkeit"
                  value={`${formatNumber(currentBahn.frequencyTwistIst) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Beschleunigung"
                  value={`${formatNumber(currentBahn.frequencyAccelIst) || '-'} Hz`}
                />
              </div>
            </div>

            {/* Soll-Daten Gruppe */}
            <div>
              <div className="mb-2 text-lg font-semibold text-gray-600">
                Soll-Daten:
              </div>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
                <InfoGridItem
                  label="Position"
                  value={`${formatNumber(currentBahn.frequencyPositionSoll) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Orientierung"
                  value={`${formatNumber(currentBahn.frequencyOrientationSoll) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Geschwindigkeit"
                  value={`${formatNumber(currentBahn.frequencyTwistSoll) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Beschleunigung"
                  value={`${formatNumber(currentBahn.frequencyAccelSoll) || '-'} Hz`}
                />
                <InfoGridItem
                  label="Gelenkzustände"
                  value={`${formatNumber(currentBahn.frequencyJointStates) || '-'} Hz`}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-6 rounded-lg border p-4">
        <MetrikenPanel bahnId={bahnId} />

        <Typography as="h3" className="mb-3 font-semibold">
          Position (Visualisierung)
        </Typography>
        <DeviationsPlot hasDeviationData={hasDeviationData} bahnId={bahnId} />
      </div>
    </div>
  );
};
