'use client';

import OptionsIcon from '@heroicons/react/24/outline/CogIcon';
import { CSVLink } from 'react-csv';

import { ApplyDTWButton } from '@/src/app/trajectories/components/TrajectoryOptions/ApplyDTWButton';
import { ApplyEuclideanButton } from '@/src/app/trajectories/components/TrajectoryOptions/ApplyEuclideanButton';
import { getCSVData } from '@/src/lib/csv-utils';
import { useTrajectory } from '@/src/providers/trajectory.provider';
import type {
  TrajectoryData,
  TrajectoryDTWJohnenMetrics,
  TrajectoryEuclideanMetrics,
} from '@/types/main';

type TrajectoryCardProps = {
  currentTrajectory: TrajectoryData;
  currentDTWJohnenMetrics: TrajectoryDTWJohnenMetrics;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
};

export const Spinner = () => {
  return (
    <svg
      width="24"
      height="24"
      stroke="#000"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g>
        <circle
          cx="12"
          cy="12"
          r="9.5"
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </g>
    </svg>
  );
};

export const TrajectoryOptions = ({
  currentTrajectory,
  currentEuclideanMetrics,
  currentDTWJohnenMetrics,
}: TrajectoryCardProps) => {
  const {
    euclideanDistances,
    setEuclidean,
    visibleEuclidean,
    showEuclideanPlot,
    visibleDTWJohnen,
    showDTWJohnenPlot,
  } = useTrajectory();

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
    <>
      <span className="mt-4 inline-flex">
        <OptionsIcon className="w-9" color="#003560" />
        <span className="mx-2  flex text-2xl font-semibold text-primary">
          options
        </span>
      </span>

      <div className="mt-2 rounded-3xl bg-stone-200 p-5">
        <ApplyEuclideanButton
          currentTrajectory={currentTrajectory}
          currentEuclideanMetrics={currentEuclideanMetrics}
          setEuclidean={setEuclidean}
          visibleEuclidean={visibleEuclidean}
          euclideanDistances={euclideanDistances}
          showEuclideanPlot={showEuclideanPlot}
        />

        <ApplyDTWButton
          currentDTWJohnenMetrics={currentDTWJohnenMetrics}
          euclideanDistances={euclideanDistances}
          setEuclidean={setEuclidean}
          currentTrajectory={currentTrajectory}
          visibleDTWJohnen={visibleDTWJohnen}
          showDTWJohnenPlot={showDTWJohnenPlot}
        />

        <CSVLink
          {...csvTrajectory}
          separator=","
          className="rounded-xl p-2 text-lg font-normal text-primary shadow-md transition-colors duration-200 ease-in betterhover:hover:bg-gray-200"
        >
          save to <span className="italic">.csv</span>
        </CSVLink>
      </div>
    </>
  );
};
