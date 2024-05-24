'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';

import { TrajectoryOptions } from '@/src/app/trajectories/components/TrajectoryOptions/TrajectoryOptions';
import { Typography } from '@/src/components/Typography';
import {
  camelToWords,
  formatDate,
  formatNumber,
  getDataToBeDisplayed,
  isDateString,
} from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryDFDMetrics,
  TrajectoryDTWJohnenMetrics,
  TrajectoryDTWMetrics,
  TrajectoryEuclideanMetrics,
  TrajectoryHeader,
} from '@/types/main';

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
        <Typography as="h2">no trajectory found</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-7 " />
        </span>
      </span>
    );
  }
  const currentTrajectoryHeader = trajectoriesHeader[currentTrajectoryID];

  return (
    <div className="flex h-full w-auto flex-col bg-gray-50 p-4 lg:h-fullscreen lg:overflow-scroll">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          trajectory info
        </span>
      </span>

      {currentTrajectoryHeader &&
        Object.keys(currentTrajectoryHeader).length !== 0 &&
        getDataToBeDisplayed(currentTrajectoryHeader, [
          'robotModel',
          'trajectoryType',
          'recordingDate',
          'realRobot',
          'pathSolver',
          'numberPointsIst',
          'numberPointsSoll',
          'SampleFrequencyIst',
          'SampleFrequencySoll',
        ]).map((header) => {
          let value = currentTrajectoryHeader[header as keyof TrajectoryHeader];
          if (typeof value === 'number') {
            value = formatNumber(value);
          }
          if (isDateString(value)) {
            value = formatDate(value as string);
          }
          return (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${camelToWords(header)}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {`${value || 'None'}`}
                </span>
              </li>
            </ul>
          );
        })}

      {currentEuclidean && Object.keys(currentEuclidean).length !== 0 ? (
        getDataToBeDisplayed(currentEuclidean, [
          'euclideanMaxDistance',
          'euclideanAverageDistance',
        ]).map((header) => {
          let value =
            currentEuclidean[header as keyof TrajectoryEuclideanMetrics];
          let unit = '';
          if (typeof value === 'number') {
            value = (value * 1000).toFixed(5);
            unit = 'mm';
          }
          return (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${camelToWords(header)}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {`${value} ${unit}`}
                </span>
              </li>
            </ul>
          );
        })
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No euclidean metrics for this trajectory.
        </ul>
      )}

      {currentDTW && Object.keys(currentDTW).length !== 0 ? (
        getDataToBeDisplayed(currentDTW, [
          'dtwMaxDistance',
          'dtwAverageDistance',
        ]).map((header) => {
          let value = currentDTW[header as keyof TrajectoryDTWMetrics];
          let unit = '';
          if (typeof value === 'number') {
            value = (value * 1000).toFixed(5);
            unit = 'mm';
          }
          return (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${camelToWords(header)}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {`${value} ${unit}`}
                </span>
              </li>
            </ul>
          );
        })
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No DTW Standard metrics for this trajectory.
        </ul>
      )}

      {currentDTWJohnen && Object.keys(currentDTWJohnen).length !== 0 ? (
        getDataToBeDisplayed(currentDTWJohnen, [
          'dtwJohnenMaxDistance',
          'dtwJohnenAverageDistance',
        ]).map((header) => {
          let value =
            currentDTWJohnen[header as keyof TrajectoryDTWJohnenMetrics];
          let unit = '';
          if (typeof value === 'number') {
            value = (value * 1000).toFixed(5);
            unit = 'mm';
          }
          return (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${camelToWords(header)}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {`${value} ${unit}`}
                </span>
              </li>
            </ul>
          );
        })
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No DTW metrics for this trajectory.
        </ul>
      )}

      {currentDFD && Object.keys(currentDFD).length !== 0 ? (
        getDataToBeDisplayed(currentDFD, [
          'dfdMaxDistance',
          'dfdAverageDistance',
        ]).map((header) => {
          let value = currentDFD[header as keyof TrajectoryDFDMetrics];
          let unit = '';
          if (typeof value === 'number') {
            value = (value * 1000).toFixed(5);
            unit = 'mm';
          }
          return (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${camelToWords(header)}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {`${value} ${unit}`}
                </span>
              </li>
            </ul>
          );
        })
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No DFD metrics for this trajectory.
        </ul>
      )}

      <TrajectoryOptions />
    </div>
  );
};
