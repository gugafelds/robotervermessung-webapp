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
import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

type TrajectoryCardProps = {
  currentTrajectory: TrajectoryData;
};

export const TrajectoryInfo = ({ currentTrajectory }: TrajectoryCardProps) => {
  const { trajectoriesHeader, intersections, setIntersections } =
    useTrajectory();

  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
  );

  if (currentTrajectoryID === -1) {
    return (
      <span className="inline-flex flex-row justify-center p-10">
        <Typography as="h2">no trajectory found</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-7 " />
        </span>
      </span>
    );
  }
  const currentTrajectoryHeader = trajectoriesHeader[currentTrajectoryID];

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

  const headersHeader = Object.keys(currentTrajectoryHeader).filter(
    (key) => !key.includes('_'),
  );

  return (
    <div className="flex h-screen flex-col overflow-scroll bg-gray-50 p-4">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          trajectory info
        </span>
      </span>
      {headersHeader.map((header) => (
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
          if (intersections?.length > 0) {
            setIntersections([]);
            return;
          }
          const euclides = await applyEuclideanDistance(currentTrajectory);
          setIntersections(euclides.intersection);
        }}
      >
        apply euclidean distance
      </button>
    </div>
  );
};
