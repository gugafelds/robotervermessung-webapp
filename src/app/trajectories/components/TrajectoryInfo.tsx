'use client';

import OptionsIcon from '@heroicons/react/24/outline/CogIcon';
import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';
import { CSVLink } from 'react-csv';

import { applyEuclideanDistance } from '@/src/actions/methods.service';
import { Typography } from '@/src/components/Typography';
import { getCSVData } from '@/src/lib/csv-utils';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryEuclideanMetrics,
  TrajectoryHeader,
} from '@/types/main';

type TrajectoryCardProps = {
  currentTrajectory: TrajectoryData;
};

export const TrajectoryInfo = ({ currentTrajectory }: TrajectoryCardProps) => {
  const {
    trajectoriesHeader,
    trajectoriesEuclideanMetrics,
    euclideanDistances,
    setEuclidean,
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
  const currentTrajectoryEuclideanMetrics = trajectoriesEuclideanMetrics.find(
    (tem) => tem.trajectoryHeaderId === searchedIndex,
  );

  const csvData = getCSVData(currentTrajectory);

  const headersData = Object.keys(csvData || {}).map((key: string) => ({
    label: key,
    key,
  }));

  const csvTrajectory = {
    data: csvData,
    header: headersData,
    filename: `trajectory_${currentTrajectory.trajectoryHeaderId.toString()}.csv`,
  };

  return (
    <div className="flex h-screen flex-col bg-gray-50 p-4">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          trajectory info
        </span>
      </span>
      {Object.keys(currentTrajectoryHeader).map((header) => (
        <ul key={header}>
          <li className="px-6 text-lg font-bold text-primary">
            {`${header}:`}{' '}
            <span className="text-lg font-light text-primary">
              {' '}
              {`${currentTrajectoryHeader[header as keyof TrajectoryHeader]}`}
            </span>
          </li>
        </ul>
      ))}
      {currentTrajectoryEuclideanMetrics &&
      Object.keys(currentTrajectoryEuclideanMetrics).length !== 0 ? (
        Object.keys(currentTrajectoryEuclideanMetrics)
          .filter((header) => !header.includes('_'))
          .map((header) => (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${header}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {' '}
                  {`${currentTrajectoryEuclideanMetrics[header as keyof TrajectoryEuclideanMetrics]}`}
                </span>
              </li>
            </ul>
          ))
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No euclidean metrics for this trajectory.
        </ul>
      )}
      <span className="inline-flex">
        <OptionsIcon className="w-9" color="#003560" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          options
        </span>
      </span>
      <CSVLink
        {...csvTrajectory}
        separator=","
        className="mx-2 w-fit rounded-xl px-6 py-4 text-xl font-normal
        text-primary shadow-md transition-colors duration-200
        ease-in betterhover:hover:bg-gray-200"
      >
        save to <span className="italic">.csv</span>
      </CSVLink>
      <button
        type="button"
        className="mx-2 mt-2 w-fit rounded-xl px-6 py-4 text-xl font-normal
        text-primary shadow-md transition-colors duration-200
        ease-in betterhover:hover:bg-gray-200"
        onClick={async () => {
          if (euclideanDistances?.length > 0) {
            setEuclidean([]);
            return;
          }
          const euclides = await applyEuclideanDistance(currentTrajectory);
          setEuclidean(euclides.intersection);
        }}
      >
        apply euclidean distance
      </button>
    </div>
  );
};
