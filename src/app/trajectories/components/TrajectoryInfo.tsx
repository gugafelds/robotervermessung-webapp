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
    <div className="flex h-full w-auto flex-col bg-gray-50 p-4 lg:h-fullscreen lg:overflow-scroll">
      <span className="inline-flex">
        <InfoIcon className="w-8" />
        <span className="mx-2 my-4 flex text-2xl font-semibold text-primary">
          trajectory info
        </span>
      </span>
      {Object.keys(currentTrajectoryHeader).map((header) => {
        let value = currentTrajectoryHeader[header as keyof TrajectoryHeader];
        // Verifica se o valor é numérico
        if (typeof value === 'number') {
          value = value.toFixed(2); // Formata o valor numérico para 4 casas decimais
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
      <span className="mt-4 inline-flex">
        <OptionsIcon className="w-9" color="#003560" />
        <span className="mx-2  flex text-2xl font-semibold text-primary">
          options
        </span>
      </span>

      <div
        className="mt-2 grid grid-rows-[50px_50px_50px] gap-3 rounded-3xl bg-stone-200 p-5
"
      >
        <div className="mt-3 text-lg font-bold text-primary">
          euclidean distance
        </div>
        <button
          type="button"
          className={`rounded-xl text-lg
    shadow-md
    ${
      currentEuclideanMetrics.trajectoryHeaderId
        ? 'bg-gray-300 font-extralight text-gray-400'
        : 'font-normal text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }`}
          onClick={async () => {
            if (euclideanDistances?.length > 0) {
              setEuclidean([]);
              return;
            }
            const euclides = await applyEuclideanDistance(currentTrajectory);
            setEuclidean(euclides.intersection);
          }}
          disabled={currentEuclideanMetrics.euclideanIntersections?.length > 0}
        >
          generate
        </button>

        <button
          type="button"
          className={`
       rounded-xl  text-lg  shadow-md
      ${visibleEuclidean ? 'bg-stone-300 font-bold' : ''}
      ${
        !currentEuclideanMetrics.trajectoryHeaderId
          ? 'bg-gray-300 font-extralight text-gray-400 '
          : 'text-primary  '
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

        <div className="mt-3 text-lg font-bold text-primary">dtw johnen</div>

        <button
          type="button"
          className={`rounded-xl px-2 text-lg 
    shadow-md
    ${
      currentDTWJohnenMetrics.trajectoryHeaderId
        ? 'bg-gray-300 font-extralight text-gray-400'
        : 'font-normal text-primary transition-colors duration-200 ease-in betterhover:hover:bg-gray-200'
    }`}
          onClick={async () => {
            if (euclideanDistances?.length > 0) {
              setEuclidean([]);
              return;
            }
            const dtwJohnen = await applyDTWJohnen(currentTrajectory);
            setEuclidean(dtwJohnen.intersection);
          }}
        >
          generate
        </button>

        <button
          type="button"
          className={`
     rounded-xl text-lg  shadow-md  
     ${visibleDTWJohnen ? 'bg-stone-300 font-bold' : ''}
     ${
       !currentDTWJohnenMetrics.trajectoryHeaderId
         ? 'bg-gray-300 font-extralight text-gray-400 '
         : 'text-primary  '
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
        <CSVLink
          {...csvTrajectory}
          separator=","
          className="col-start-3 content-center rounded-xl px-2 text-center text-lg font-normal      text-primary shadow-md transition-colors duration-200
        ease-in betterhover:hover:bg-gray-200"
        >
          save to <span className="italic">.csv</span>
        </CSVLink>
      </div>
    </div>
  );
};
