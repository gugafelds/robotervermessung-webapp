'use client';

import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';

import { TrajectoryOptions } from '@/src/app/trajectories/components/TrajectoryOptions/TrajectoryOptions';
import { Typography } from '@/src/components/Typography';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryDTWJohnenMetrics,
  TrajectoryEuclideanMetrics,
  TrajectoryHeader,
} from '@/types/main';

type TrajectoryCardProps = {
  currentTrajectory: TrajectoryData;
  currentDTWJohnenMetrics: TrajectoryDTWJohnenMetrics;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
};

export const TrajectoryInfo = ({
  currentTrajectory,
  currentEuclideanMetrics,
  currentDTWJohnenMetrics,
}: TrajectoryCardProps) => {
  const { trajectoriesHeader } = useTrajectory();

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
      {currentEuclideanMetrics &&
      Object.keys(currentEuclideanMetrics).length !== 0 ? (
        Object.keys(currentEuclideanMetrics)
          .filter((header) => !header.includes('trajectoryHeaderId'))
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('euclideanIntersections'))
          .filter((header) => !header.includes('metricType'))
          .map((header) => {
            let value =
              currentEuclideanMetrics[
                header as keyof TrajectoryEuclideanMetrics
              ];
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
      {currentDTWJohnenMetrics &&
      Object.keys(currentDTWJohnenMetrics).length !== 0 ? (
        Object.keys(currentDTWJohnenMetrics)
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('trajectoryHeaderId'))
          .filter((header) => !header.includes('metricType'))
          .filter((header) => !header.includes('dtwJohnenX'))
          .filter((header) => !header.includes('dtwJohnenY'))
          .filter((header) => !header.includes('dtwAccDist'))
          .filter((header) => !header.includes('dtwPath'))
          .map((header) => {
            let value =
              currentDTWJohnenMetrics[
                header as keyof TrajectoryDTWJohnenMetrics
              ];
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
      <TrajectoryOptions
        currentTrajectory={currentTrajectory}
        currentEuclideanMetrics={currentEuclideanMetrics}
        currentDTWJohnenMetrics={currentDTWJohnenMetrics}
      />
    </div>
  );
};
