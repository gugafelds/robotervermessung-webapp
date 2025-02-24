'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
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
    className={`border-b border-gray-100 py-2 text-base ${
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

interface TrajectoryInfoProps {
  isTransformed: boolean;
}

const InfoSection: React.FC<InfoSectionProps> = ({ title, children }) => (
  <div className="mb-5 rounded-lg border-l-4 border-primary bg-white p-5 shadow-md">
    <h3 className="mb-4 text-xl font-bold text-primary">{title}</h3>
    {children}
  </div>
);

export const TrajectoryInfo: React.FC<TrajectoryInfoProps> = ({
  isTransformed,
}) => {
  const { currentBahnInfo, currentBahnPoseTrans } = useTrajectory();

  const calibrationId = currentBahnPoseTrans?.[0]?.calibrationID;

  if (currentBahnInfo === null) {
    return (
      <span className="flex flex-row justify-center p-10">
        <Typography as="h2">keine Bahn gefunden</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-7 text-primary" />
        </span>
      </span>
    );
  }

  return (
    <div className="flex h-full w-auto flex-col bg-gray-50 p-4 lg:h-fullscreen lg:w-3/12 lg:overflow-scroll">
      <span className="inline-flex">
        <InfoIcon className="w-8 text-primary" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          Bahn Info
        </span>
      </span>

      {currentBahnInfo && Object.keys(currentBahnInfo).length !== 0 && (
        <>
          <InfoSection title="Allgemein">
            <InfoRow
              label="Datei"
              value={currentBahnInfo.recordFilename || 'n. a.'}
              singleColumn
            />
            <InfoRow
              label="Roboter"
              value={currentBahnInfo.robotModel || 'n. a.'}
              singleColumn
            />
            <InfoRow
              label="Startzeitpunkt"
              value={
                currentBahnInfo.startTime
                  ? formatDate(currentBahnInfo.startTime)
                  : 'n. a.'
              }
              singleColumn
            />
            <InfoRow
              label="Endzeitpunkt"
              value={
                currentBahnInfo.endTime
                  ? formatDate(currentBahnInfo.endTime)
                  : 'n. a.'
              }
              singleColumn
            />
            <InfoRow
              label="Datenquelle (Ist)"
              value={currentBahnInfo.sourceDataIst || 'n. a.'}
              singleColumn
            />
            <InfoRow
              label="Datenquelle (Soll)"
              value={currentBahnInfo.sourceDataSoll || 'n. a.'}
              singleColumn
            />
            <InfoRow
              label="Last am TCP"
              value={`${formatNumber(currentBahnInfo.weight) || 'n. a.'} kg`}
              singleColumn
            />
            <InfoRow
              label="Transformiert"
              value={isTransformed ? 'Ja' : 'Nein'}
              singleColumn
            />
            {isTransformed && calibrationId && (
              <InfoRow
                label="Kalibrierungsdatei-ID"
                value={calibrationId}
                singleColumn
              />
            )}
          </InfoSection>

          <InfoSection title="Punkteanzahl">
            <InfoRow
              label="Ereignisse"
              value={
                formatNumber(currentBahnInfo.numberPointsEvents) || 'n. a.'
              }
            />
            <InfoRow
              label="Pose Ist"
              value={
                formatNumber(currentBahnInfo.numberPointsPoseIst) || 'n. a.'
              }
            />
            <InfoRow
              label="Twist Ist"
              value={
                formatNumber(currentBahnInfo.numberPointsTwistIst) || 'n. a.'
              }
            />
            <InfoRow
              label="Accel Ist"
              value={
                formatNumber(currentBahnInfo.numberPointsAccelIst) || 'n. a.'
              }
            />
            <InfoRow
              label="Pos. Soll"
              value={
                formatNumber(currentBahnInfo.numberPointsPosSoll) || 'n. a.'
              }
            />
            <InfoRow
              label="Orient. Soll"
              value={
                formatNumber(currentBahnInfo.numberPointsOrientSoll) || 'n. a.'
              }
            />
            <InfoRow
              label="Twist Soll"
              value={
                formatNumber(currentBahnInfo.numberPointsTwistSoll) || 'n. a.'
              }
            />
            <InfoRow
              label="Joint States"
              value={
                formatNumber(currentBahnInfo.numberPointsJointStates) || 'n. a.'
              }
            />
            <InfoRow
              label="IMU"
              value={formatNumber(currentBahnInfo.numberPointsIMU) || 'n. a.'}
            />
          </InfoSection>

          <InfoSection title="Abtastraten">
            <InfoRow
              label="Pose Ist"
              value={`${formatNumber(currentBahnInfo.frequencyPoseIst) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Twist Ist"
              value={`${formatNumber(currentBahnInfo.frequencyTwistIst) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Accel Ist"
              value={`${formatNumber(currentBahnInfo.frequencyAccelIst) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Position Soll"
              value={`${formatNumber(currentBahnInfo.frequencyPositionSoll) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Orient. Soll"
              value={`${formatNumber(currentBahnInfo.frequencyOrientationSoll) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Twist Soll"
              value={`${formatNumber(currentBahnInfo.frequencyTwistSoll) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="Joint States"
              value={`${formatNumber(currentBahnInfo.frequencyJointStates) || 'n. a.'} Hz`}
            />
            <InfoRow
              label="IMU"
              value={`${formatNumber(currentBahnInfo.frequencyIMU) || 'n. a.'}Hz`}
            />
          </InfoSection>
        </>
      )}
    </div>
  );
};
