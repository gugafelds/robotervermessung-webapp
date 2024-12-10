'use client';

import { InformationCircleIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { checkPositionDataAvailability } from '@/src/actions/auswertung.service';
import { AllDeviationsPlot } from '@/src/app/auswertung/components/AllDeviationsPlot';
import { MetrikenPanel } from '@/src/app/auswertung/components/MetrikenPanel';
import { MetrikenPanelPlot } from '@/src/app/auswertung/components/MetrikenPanelPlot';
import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber } from '@/src/lib/functions';
import { useAuswertung } from '@/src/providers/auswertung.provider';

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
  const { auswertungInfo } = useAuswertung();

  useEffect(() => {
    const checkData = async () => {
      const hasData = await checkPositionDataAvailability(bahnId);
      setHasDeviationData(hasData);
    };
    checkData();
  }, [bahnId]);

  const currentBahn = auswertungInfo.bahn_info.find(
    (bahn) => bahn.bahnID === bahnId,
  );

  const euclideanAnalyses =
    auswertungInfo.auswertung_info.info_euclidean.filter(
      (info) => info.bahnID === bahnId,
    );

  const dfdAnalyses = auswertungInfo.auswertung_info.info_dfd.filter(
    (info) => info.bahnID === bahnId,
  );

  const sidtwAnalyses = auswertungInfo.auswertung_info.info_sidtw.filter(
    (info) => info.bahnID === bahnId,
  );

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
            Aufnahmedatum: {formatDate(currentBahn.recordingDate)}
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
                label="Datenquelle (Ist)"
                value={currentBahn.sourceDataIst || 'n. a.'}
              />
              <InfoGridItem
                label="Datenquelle (Soll)"
                value={currentBahn.sourceDataSoll || 'n. a.'}
              />
              <InfoGridItem
                label="Bahndauer"
                value={
                  currentBahn.startTime && currentBahn.endTime
                    ? `${Math.round((new Date(currentBahn.endTime).getTime() - new Date(currentBahn.startTime).getTime()) / 1000)}s`
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
                label="Kalibrierungsdatei"
                value={currentBahn.calibrationRun ? 'Ja' : 'Nein'}
              />
            </div>
          </div>

          {/* Abtastraten */}
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h3 className="font-semibold text-primary">Abtastraten</h3>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <InfoGridItem
                label="Pose Ist"
                value={`${formatNumber(currentBahn.frequencyPoseIst) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Twist Ist"
                value={`${formatNumber(currentBahn.frequencyTwistIst) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Accel Ist"
                value={`${formatNumber(currentBahn.frequencyAccelIst) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Position Soll"
                value={`${formatNumber(currentBahn.frequencyPositionSoll) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Orientierung Soll"
                value={`${formatNumber(currentBahn.frequencyOrientationSoll) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Twist Soll"
                value={`${formatNumber(currentBahn.frequencyTwistSoll) || 'n. a.'} Hz`}
              />
              <InfoGridItem
                label="Joint States"
                value={`${formatNumber(currentBahn.frequencyJointStates) || 'n. a.'} Hz`}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mb-6 rounded-lg border p-4">
        <MetrikenPanel
          euclideanAnalyses={euclideanAnalyses}
          dfdAnalyses={dfdAnalyses}
          sidtwAnalyses={sidtwAnalyses}
        />

        {/* Analysis Plots */}
        {euclideanAnalyses.length > 0 ? (
          <MetrikenPanelPlot
            eaAnalyses={euclideanAnalyses}
            dfdAnalyses={dfdAnalyses}
            sidtwAnalyses={sidtwAnalyses}
          />
        ) : (
          <p className="text-gray-500">Keine Euclidean Analysen verfügbar</p>
        )}
      </div>

      <div className="mb-6 rounded-lg border p-4">
        <Typography as="h3" className="mb-3 font-semibold">
          Abweichungen nach aufgezeichneten Punkten
        </Typography>
        <AllDeviationsPlot
          hasDeviationData={hasDeviationData}
          bahnId={bahnId}
        />
      </div>
    </div>
  );
};
