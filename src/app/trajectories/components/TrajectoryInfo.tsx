'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';

import { TrajectoryOptions } from '@/src/app/trajectories/components/TrajectoryOptions/TrajectoryOptions';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryDTWJohnenMetrics,
  TrajectoryEuclideanMetrics,
  TrajectoryHeader,
} from '@/types/main';

export const TrajectoryInfo = () => {
  const {
    trajectoriesHeader,
    currentTrajectory,
    currentDtw,
    currentEuclidean,
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
      {Object.keys(currentTrajectoryHeader).map((header) => {
        let value = currentTrajectoryHeader[header as keyof TrajectoryHeader];
        if (typeof value === 'number') {
          value = value.toFixed(2);
        }
        return (
          <ul key={header}>
            <li className="px-6 text-lg font-bold text-primary">
              {`${header}:`}{' '}
              <span className="text-lg font-light text-primary">
                {`${value}`}
              </span>
            </li>
          </ul>
        );
      })}
      {currentEuclidean && Object.keys(currentEuclidean).length !== 0 ? (
        Object.keys(currentEuclidean)
          .filter((header) => !header.includes('trajectoryHeaderId'))
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('euclideanIntersections'))
          .filter((header) => !header.includes('metricType'))
          .map((header) => {
            let value =
              currentEuclidean[header as keyof TrajectoryEuclideanMetrics];
            let unit = '';
            if (typeof value === 'number') {
              value = value.toFixed(5);
              unit = 'm';
            }
            return (
              <ul key={header}>
                <li className="px-6 text-lg font-bold text-primary">
                  {`${header}:`}{' '}
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
      {currentDtw && Object.keys(currentDtw).length !== 0 ? (
        Object.keys(currentDtw)
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('trajectoryHeaderId'))
          .filter((header) => !header.includes('metricType'))
          .filter((header) => !header.includes('dtwJohnenX'))
          .filter((header) => !header.includes('dtwJohnenY'))
          .filter((header) => !header.includes('dtwAccDist'))
          .filter((header) => !header.includes('dtwPath'))
          .map((header) => {
            let value = currentDtw[header as keyof TrajectoryDTWJohnenMetrics];
            let unit = '';
            if (typeof value === 'number') {
              value = value.toFixed(5);
              unit = 'm';
            }
            return (
              <ul key={header}>
                <li className="px-6 text-lg font-bold text-primary">
                  {`${header}:`}{' '}
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
      <TrajectoryOptions />
    </div>
  );
};
