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
    currentTrajectory,
    currentDTW,
    currentDTWJohnen,
    currentEuclidean,
    currentDFD,
  } = useTrajectory();

  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
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
  const currentTrajectoryHeader = trajectoriesHeader[currentTrajectoryID];

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
              {`Roboter Modell:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.robotModel || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Trajektorie Typ:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.trajectoryType || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Aufnahmedatum:`}{' '}
              <span className="text-lg font-light text-primary">
                {isDateString(currentTrajectoryHeader.recordingDate)
                  ? formatDate(currentTrajectoryHeader.recordingDate)
                  : 'Keine'}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Echter Roboter:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.realRobot || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Bahnplanung:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${currentTrajectoryHeader.pathSolver || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Anzahl der Punkte (Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.numberPointsIst) || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Anzahl der Punkte (Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.numberPointsSoll) || 'Keine'}`}
              </span>
            </li>
            <li className="px-4 text-lg font-bold text-primary">
              {`Abtastrate (Ist):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.SampleFrequencyIst) || 'Keine'}`}
              </span>
            </li>
            <li className="mb-2 px-4 text-lg font-bold text-primary">
              {`Abtastrate (Soll):`}{' '}
              <span className="text-lg font-light text-primary">
                {`${formatNumber(currentTrajectoryHeader.SampleFrequencySoll) || 'Keine'}`}
              </span>
            </li>
          </ul>
        )}

      <hr className="m-2 border-t border-gray-300" />

      {currentEuclidean && Object.keys(currentEuclidean).length !== 0 ? (
        <ul className="mb-2">
          <li className="px-6 text-lg font-bold text-primary">
            Euklidischer Abstand
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Max.:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentEuclidean.euclideanMaxDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Ø:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentEuclidean.euclideanAverageDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
        </ul>
      ) : (
        <ul className="mb-4 px-6 text-lg font-light text-primary">
          Keine euklidischen Metriken für diese Trajektorie.
        </ul>
      )}

      <hr className="m-2 border-t border-gray-300" />

      {currentDTW && Object.keys(currentDTW).length !== 0 ? (
        <ul className="mb-2">
          <li className="px-6 text-lg font-bold text-primary">DTW</li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Max.:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDTW.dtwMaxDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Ø:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDTW.dtwAverageDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
        </ul>
      ) : (
        <ul className="mb-4 px-6 text-lg font-light text-primary">
          Keine DTW-Standardmetriken für diese Trajektorie.
        </ul>
      )}

      <hr className="m-2 border-t border-gray-300" />

      {currentDTWJohnen && Object.keys(currentDTWJohnen).length !== 0 ? (
        <ul className="mb-2">
          <li className="px-6 text-lg font-bold text-primary">DTW-Johnen</li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Max.:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDTWJohnen.dtwJohnenMaxDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Ø:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDTWJohnen.dtwJohnenAverageDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
        </ul>
      ) : (
        <ul className="mb-4 px-6 text-lg font-light text-primary">
          Keine DTW-Johnen-Metriken für diese Trajektorie.
        </ul>
      )}

      <hr className="m-2 border-t border-gray-300" />

      {currentDFD && Object.keys(currentDFD).length !== 0 ? (
        <ul className="mb-2">
          <li className="px-6 text-lg font-bold text-primary">
            Diskrete Fréchet-Distanz
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Max.:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDFD.dfdMaxDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
          <li className="px-6 text-lg font-semibold text-primary">
            {`Ø:`}{' '}
            <span className="text-lg font-light text-primary">
              {`${(currentDFD.dfdAverageDistance * 1000).toFixed(5)} mm`}
            </span>
          </li>
        </ul>
      ) : (
        <ul className="mb-4 px-6 text-lg font-light text-primary">
          Keine DFD-Metriken für diese Trajektorie.
        </ul>
      )}

      <hr className="m-2 border-t border-gray-300" />

      <TrajectoryOptions />
    </div>
  );
};
