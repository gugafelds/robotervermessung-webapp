'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';

import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const TrajectoryInfo = () => {
  const { currentBahnInfo } = useTrajectory();

  if (currentBahnInfo === null) {
    return (
      <span className="flex flex-row justify-center p-10">
        <Typography as="h2">keine Trajektorie gefunden</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-7 " />
        </span>
      </span>
    );
  }

  /*
  const metricGroups = [
    {
      title: 'Euklidischer Abst.',
      data: currentEuclidean,
      max: 'euclideanMaxDistance',
      avg: 'euclideanAverageDistance',
      errorMsg: 'Keine euklidischen Metriken.',
    },
    {
      title: 'DTW',
      data: currentDTW,
      max: 'dtwMaxDistance',
      avg: 'dtwAverageDistance',
      errorMsg: 'Keine DTW-Standardmetriken.',
    },
    {
      title: 'DTW-SI',
      data: currentDTWJohnen,
      max: 'dtwJohnenMaxDistance',
      avg: 'dtwJohnenAverageDistance',
      errorMsg: 'Keine DTW-Johnen-Metriken.',
    },
    {
      title: 'Diskr. Fréchet',
      data: currentDFD,
      max: 'dfdMaxDistance',
      avg: 'dfdAverageDistance',
      errorMsg: 'Keine DFD-Metriken.',
    },
    {
      title: 'LCSS',
      data: currentLCSS,
      max: 'lcssMaxDistance',
      avg: 'lcssAverageDistance',
      errorMsg: 'Keine LCSS-Metriken.',
    },
  ];
  */
  return (
    <div className="flex h-full w-auto flex-col bg-gray-50 p-2 lg:h-fullscreen lg:w-3/12 lg:overflow-scroll">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          bahn info
        </span>
      </span>

      {currentBahnInfo && Object.keys(currentBahnInfo).length !== 0 && (
        <ul>
          <li className="px-4 text-lg font-bold text-primary">
            {`Aufnahmedatei:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.recordFilename || 'n. a.'}`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Roboter:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.robotModel || 'n. a.'}`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Startzeitpunkt:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.startTime ? formatDate(currentBahnInfo.startTime) : 'n. a.'}`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Endzeitpunkt:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.startTime ? formatDate(currentBahnInfo.endTime) : 'n. a.'}`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Anzahl der Ereignisse:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.numberPoints) || 'n. a.'}`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Pose Ist):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyPoseIst) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Twist Ist):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyTwistIst) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Accel Ist):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyAccelIst) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Position Soll):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyPositionSoll) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Rotation Soll):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyOrientationSoll) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Twist Soll):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyTwistSoll) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Abtastrate (Joint States):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${formatNumber(currentBahnInfo.frequencyJointStates) || 'n. a.'} Hz`}
            </span>
          </li>
          <li className="px-4 text-lg font-bold text-primary">
            {`Datenquelle (Ist):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.sourceDataIst || 'n. a.'}`}
            </span>
          </li>
          <li className="mb-2 px-4 text-lg font-bold text-primary">
            {`Datenquelle (Soll):`}{' '}
            <span className="text-lg font-light text-primary">
              {`${currentBahnInfo.sourceDataSoll || 'n. a.'}`}
            </span>
          </li>
        </ul>
      )}
    </div>
  );
};
