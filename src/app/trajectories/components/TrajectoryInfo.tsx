'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';

import { TrajectoryOptions } from '@/src/app/trajectories/components/TrajectoryOptions/TrajectoryOptions';
import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber, isDateString } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const TrajectoryInfo = () => {
  const {
    trajectoriesHeader,
    segmentsHeader,
    bahnInfo,
    bahnInfo: [{ bahnID }],
    currentTrajectory,
    currentDTW,
    currentDTWJohnen,
    currentEuclidean,
    currentDFD,
    currentLCSS,
  } = useTrajectory();

  const searchedIndex = bahnID;
  console.log(searchedIndex)
  const currentTrajectoryID = bahnInfo.findIndex(
    (item) => item.bahnID === searchedIndex,
  );

  if (currentTrajectoryID === -1) {
    return (
      <span className="flex flex-row justify-center p-10">
        <Typography as="h2">keine Trajektorie gefunden</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-7 " />
        </span>
      </span>
    );
  }

  const isSegment = searchedIndex.includes('_');
  const headerToUse = isSegment ? segmentsHeader : bahnInfo;

  const currentTrajectoryHeader = bahnInfo[currentTrajectoryID];

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

  return (
    <div className="flex h-full w-auto flex-col bg-gray-50 p-2 lg:h-fullscreen lg:w-3/12 lg:overflow-scroll">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          trajektorie info
        </span>
      </span>

      {currentTrajectoryHeader &&
        Object.keys(currentTrajectoryHeader).length !== 0 && (
          <ul>
            <li className="px-4 text-lg font-bold text-primary">
              {`Aufnahmedatei:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.recordFilename || 'n. a.'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Roboter:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.robotModel || 'n. a.'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Startzeitpunkt:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.startTime ? formatDate(currentTrajectoryHeader.startTime) : 'n. a.'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Endzeitpunkt:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.startTime ? formatDate(currentTrajectoryHeader.endTime): 'n. a.'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Anzahl der Ereignisse:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.numberPoints) || 'n. a.'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Pose Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyPoseIst) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Twist Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyTwistIst) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Accel Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyAccelIst) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Position Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyPositionSoll) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Rotation Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyOrientationSoll) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Twist Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyTwistSoll) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Joint States):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.frequencyJointStates) || 'n. a.'} Hz`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Datenquelle (Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.sourceDataIst || 'n. a.'}`}
              </span>
            </li>
            <li className="mb-2 px-4 text-lg font-bold text-primary">
              {`Datenquelle (Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.sourceDataSoll || 'n. a.'}`}
              </span>
            </li>
          </ul>
        )}

      <div className="grid grid-cols-2 gap-2">
        {metricGroups.map((metric) => (
          <div key={metric.title}>
            <hr className="m-2 border-t border-gray-300" />
            {metric.data && Object.keys(metric.data).length !== 0 ? (
              <ul className="mb-1">
                <li className="px-6 text-base font-bold text-primary">
                  {metric.title}
                </li>
                <li className="px-6 text-base font-semibold text-primary">
                  {`Max.:`}{' '}
                  <span className="text-base font-normal text-primary">
                    {`${(metric.data[metric.max] * 1000).toFixed(3)} mm`}
                  </span>
                </li>
                <li className="px-6 text-base font-semibold text-primary">
                  {`Ø:`}{' '}
                  <span className="text-base font-normal text-primary">
                    {`${(metric.data[metric.avg] * 1000).toFixed(3)} mm`}
                  </span>
                </li>
              </ul>
            ) : (
              <ul className="mb-4 px-6 text-base font-extralight text-primary">
                {metric.errorMsg}
              </ul>
            )}
          </div>
        ))}
      </div>

    
    </div>
  );
};
