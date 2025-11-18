// TrajectoryInfo.tsx - Mit kontextabhängigem Button

'use client';

import { ChartBarIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';

import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

interface InfoRowProps {
  label: string;
  value: React.ReactNode;
  singleColumn?: boolean;
}

const InfoRow: React.FC<InfoRowProps> = ({
  label,
  value,
  singleColumn = false,
}) => (
  <div
    className={`border-b border-gray-200 py-2 text-base ${
      singleColumn ? 'flex flex-col' : 'flex justify-between'
    }`}
  >
    <span className="font-medium">{singleColumn ? `${label}:` : label}</span>
    <span
      className={`font-semibold text-primary ${singleColumn ? 'mt-1' : ''}`}
    >
      {value}
    </span>
  </div>
);

interface InfoSectionProps {
  title: string;
  children: React.ReactNode;
}

interface TrajectoryInfoProps {}

const InfoSection: React.FC<InfoSectionProps> = ({ title, children }) => (
  <div className="mb-5 rounded-lg border border-l-4 border-primary bg-white p-4">
    <h3 className="mb-4 text-xl font-bold text-primary">{title}</h3>
    {children}
  </div>
);

export const TrajectoryInfo: React.FC<TrajectoryInfoProps> = () => {
  const { currentBahnInfo } = useTrajectory();
  const pathname = usePathname();

  // Prüfe, ob wir uns auf der Auswertungsseite befinden
  const isOnAuswertungPage = pathname.includes('/auswertung');

  if (currentBahnInfo === null) {
    return (
      <span className="flex h-full min-w-80 flex-row justify-center border-r border-gray-500 bg-gray-50 p-4 lg:h-fullscreen lg:overflow-scroll">
        <Typography as="h5">Keine Bahn gefunden</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-6 text-primary" />
        </span>
      </span>
    );
  }

  return (
    <div className="flex h-full min-w-80 flex-col border-r border-gray-500 bg-gray-50 p-4 lg:h-fullscreen lg:overflow-scroll">
      {currentBahnInfo && Object.keys(currentBahnInfo).length !== 0 && (
        <>
          {/* Bahn-ID und Dateiname prominent anzeigen */}
          <div className="rounded-xl p-4 text-primary ">
            <div className="text-sm font-medium">Bahn-ID</div>
            <div className="text-2xl font-bold">
              {currentBahnInfo.bahnID || '-'}
            </div>
            <div className="pt-2">
              <div className="text-sm font-medium">Datei</div>
              <div className="text-xl font-semibold">
                {currentBahnInfo.recordFilename || '-'}
              </div>
            </div>

            {/* Kontextabhängiger Button */}
            <div className="my-2 flex w-fit rounded-lg bg-primary px-4 py-1 font-medium text-white transition duration-300 ease-in-out hover:bg-gray-800">
              {currentBahnInfo && (
                <Link
                  href={
                    isOnAuswertungPage
                      ? `/bewegungsdaten/${currentBahnInfo.bahnID}`
                      : `/auswertung/${currentBahnInfo.bahnID}`
                  }
                  className="flex items-center"
                >
                  {isOnAuswertungPage ? (
                    <>
                      <DocumentTextIcon className="mr-2 size-5" />
                      <span>Bewegungsdaten</span>
                    </>
                  ) : (
                    <>
                      <ChartBarIcon className="mr-2 size-5" />
                      <span>Auswertung</span>
                    </>
                  )}
                </Link>
              )}
            </div>
          </div>

          <InfoSection title="Allgemein">
            <InfoRow
              label="Roboter"
              value={currentBahnInfo.robotModel || '-'}
            />
            <InfoRow
              label="Start"
              value={
                currentBahnInfo.startTime
                  ? formatDate(currentBahnInfo.startTime)
                  : '-'
              }
            />
            <InfoRow
              label="Ende"
              value={
                currentBahnInfo.endTime
                  ? formatDate(currentBahnInfo.endTime)
                  : '-'
              }
            />
            <InfoRow
              label="Bahndauer"
              value={
                currentBahnInfo.startTime && currentBahnInfo.endTime
                  ? `${((new Date(currentBahnInfo.endTime).getTime() - new Date(currentBahnInfo.startTime).getTime()) / 1000).toFixed(1)} s`
                  : 'n. a.'
              }
            />
            <InfoRow
              label="Quelle-Ist"
              value={currentBahnInfo.sourceDataIst || '-'}
            />
            <InfoRow
              label="Quelle-Soll"
              value={currentBahnInfo.sourceDataSoll || '-'}
            />
            <InfoRow
              label="Last"
              value={`${formatNumber(currentBahnInfo.weight) || '-'} kg`}
            />
            <InfoRow
              label="Stop-Point"
              value={`${formatNumber(currentBahnInfo.stopPoint) || '-'} %`}
            />
            <InfoRow
              label="Verweilzeit"
              value={`${formatNumber(currentBahnInfo.waitTime) || '-'} s`}
            />
            <InfoRow
              label="Geschwindigkeit"
              value={`${formatNumber(currentBahnInfo.settedVelocity) || '-'} mm/s`}
            />
          </InfoSection>

          <InfoSection title="Punkteanzahl">
            {/* IST Daten Gruppe */}
            <div className="mb-2 border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Ist-Daten:
              </div>
              <InfoRow
                label="Pose"
                value={formatNumber(currentBahnInfo.numberPointsPoseIst) || '-'}
              />
              <InfoRow
                label="Geschwindigkeit"
                value={
                  formatNumber(currentBahnInfo.numberPointsTwistIst) || '-'
                }
              />
              <InfoRow
                label="Beschleunigung"
                value={
                  formatNumber(currentBahnInfo.numberPointsAccelIst) || '-'
                }
              />
            </div>

            {/* SOLL Daten Gruppe */}
            <div className="border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Soll-Daten:
              </div>
              <InfoRow
                label="Position"
                value={formatNumber(currentBahnInfo.numberPointsPosSoll) || '-'}
              />
              <InfoRow
                label="Orientierung"
                value={
                  formatNumber(currentBahnInfo.numberPointsOrientSoll) || '-'
                }
              />
              <InfoRow
                label="Geschwindigkeit"
                value={
                  formatNumber(currentBahnInfo.numberPointsTwistSoll) || '-'
                }
              />
              <InfoRow
                label="Beschleunigung"
                value={
                  formatNumber(currentBahnInfo.numberPointsAccelSoll) || '-'
                }
              />
              <InfoRow
                label="Gelenkzustände"
                value={
                  formatNumber(currentBahnInfo.numberPointsJointStates) || '-'
                }
              />
              <InfoRow
                label="Ereignisse"
                value={formatNumber(currentBahnInfo.numberPointsEvents) || '-'}
              />
            </div>
          </InfoSection>

          <InfoSection title="Abtastraten (Hz)">
            {/* IST Daten Gruppe */}
            <div className="mb-2 border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Ist-Daten:
              </div>
              <InfoRow
                label="Pose"
                value={formatNumber(currentBahnInfo.frequencyPoseIst) || '-'}
              />
              <InfoRow
                label="Geschwindigkeit"
                value={formatNumber(currentBahnInfo.frequencyTwistIst) || '-'}
              />
              <InfoRow
                label="Beschleunigung"
                value={formatNumber(currentBahnInfo.frequencyAccelIst) || '-'}
              />
            </div>

            {/* SOLL Daten Gruppe */}
            <div className="border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Soll-Daten:
              </div>
              <InfoRow
                label="Position"
                value={
                  formatNumber(currentBahnInfo.frequencyPositionSoll) || '-'
                }
              />
              <InfoRow
                label="Orientierung"
                value={
                  formatNumber(currentBahnInfo.frequencyOrientationSoll) || '-'
                }
              />
              <InfoRow
                label="Geschwindigkeit"
                value={formatNumber(currentBahnInfo.frequencyTwistSoll) || '-'}
              />
              <InfoRow
                label="Beschleunigung"
                value={formatNumber(currentBahnInfo.frequencyAccelSoll) || '-'}
              />
              <InfoRow
                label="Gelenkzustände"
                value={
                  formatNumber(currentBahnInfo.frequencyJointStates) || '-'
                }
              />
            </div>
          </InfoSection>
        </>
      )}
    </div>
  );
};
