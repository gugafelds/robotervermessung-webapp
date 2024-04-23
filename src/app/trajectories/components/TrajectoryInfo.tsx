'use client';

import OptionsIcon from '@heroicons/react/24/outline/CogIcon';
import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import InfoIcon from '@heroicons/react/24/outline/InformationCircleIcon';
import React from 'react';
import { CSVLink } from 'react-csv';

import {
  applyDTWJohnen,
  applyEuclideanDistance,
} from '@/src/actions/methods.service';
import { Typography } from '@/src/components/Typography';
import { getCSVData } from '@/src/lib/csv-utils';
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
  const {
    trajectoriesHeader,
    euclideanDistances,
    setEuclidean,
    visibleEuclidean,
    showEuclideanPlot,
    visibleDTWJohnen,
    showDTWJohnenPlot,
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
    <div className="flex h-auto flex-col bg-gray-50 p-4">
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
      {currentEuclideanMetrics &&
      Object.keys(currentEuclideanMetrics).length !== 0 ? (
        Object.keys(currentEuclideanMetrics)
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('euclideanIntersections'))
          .filter((header) => !header.includes('metricType'))
          .map((header) => (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${header}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {' '}
                  {`${currentEuclideanMetrics[header as keyof TrajectoryEuclideanMetrics]}`}
                </span>
              </li>
            </ul>
          ))
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No euclidean metrics for this trajectory.
        </ul>
      )}
      {currentDTWJohnenMetrics &&
      Object.keys(currentDTWJohnenMetrics).length !== 0 ? (
        Object.keys(currentDTWJohnenMetrics)
          .filter((header) => !header.includes('_id'))
          .filter((header) => !header.includes('metricType'))
          .filter((header) => !header.includes('dtwJohnenX'))
          .filter((header) => !header.includes('dtwJohnenY'))
          .filter((header) => !header.includes('dtwAccDist'))
          .filter((header) => !header.includes('dtwPath'))
          .map((header) => (
            <ul key={header}>
              <li className="px-6 text-lg font-bold text-primary">
                {`${header}:`}{' '}
                <span className="text-lg font-light text-primary">
                  {' '}
                  {`${currentDTWJohnenMetrics[header as keyof TrajectoryDTWJohnenMetrics]}`}
                </span>
              </li>
            </ul>
          ))
      ) : (
        <ul className="px-6 text-lg font-light text-primary">
          No DTW Johnen metrics for this trajectory.
        </ul>
      )}
      <span className="inline-flex">
        <OptionsIcon className="w-9" color="#003560" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          options
        </span>
      </span>
      <div className="mb-5 inline-flex">
        <span className="mx-5 mt-2 w-fit py-3 text-xl font-bold text-primary">
          euclidean distance:
        </span>
        <button
          type="button"
          className="mx-2 mt-2 w-fit rounded-xl px-6 text-xl font-normal
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
          calculate
        </button>
        <button
          type="button"
          className={`
    mx-1 mt-1 w-32 rounded-xl px-4 text-xl  shadow-md
    ${
      visibleEuclidean
        ? 'bg-gray-200 font-bold text-primary'
        : 'text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }
    ${
      !currentEuclideanMetrics.trajectoryHeaderId
        ? 'bg-gray-200 font-extralight text-gray-400'
        : 'text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }
  `}
          onClick={() => {
            showEuclideanPlot(!visibleEuclidean);
          }}
          disabled={
            !currentEuclideanMetrics ||
            !currentEuclideanMetrics.euclideanIntersections
          }
        >
          view 3D
        </button>
      </div>
      <div className="inline-flex">
        <span className="mx-5 mt-2 w-fit py-3 text-xl font-bold text-primary">
          dtw johnen:
        </span>
        <button
          type="button"
          className="mx-2 mt-2 w-fit rounded-xl px-6 text-xl font-normal
          text-primary shadow-md transition-colors duration-200
          ease-in betterhover:hover:bg-gray-200"
          onClick={async () => {
            if (euclideanDistances?.length > 0) {
              setEuclidean([]);
              return;
            }
            const dtwJohnen = await applyDTWJohnen(currentTrajectory);
            setEuclidean(dtwJohnen.intersection);
          }}
        >
          calculate
        </button>
        <button
          type="button"
          className={`
    mx-1 mt-1 w-32 rounded-xl px-4 text-xl  shadow-md
    ${
      visibleDTWJohnen
        ? 'bg-gray-200 font-bold text-primary'
        : 'text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }
    ${
      !currentDTWJohnenMetrics.trajectoryHeaderId
        ? 'bg-gray-200 font-extralight text-gray-400'
        : 'text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }
  `}
          onClick={() => {
            showDTWJohnenPlot(!visibleDTWJohnen);
          }}
          disabled={
            !currentDTWJohnenMetrics || !currentDTWJohnenMetrics.dtwPath
          }
        >
          view 3D
        </button>
      </div>
      <CSVLink
        {...csvTrajectory}
        separator=","
        className="mx-2 w-fit rounded-xl px-6 py-4 text-xl font-normal
        text-primary shadow-md transition-colors duration-200
        ease-in betterhover:hover:bg-gray-200"
      >
        save to <span className="italic">.csv</span>
      </CSVLink>
    </div>
  );
};
