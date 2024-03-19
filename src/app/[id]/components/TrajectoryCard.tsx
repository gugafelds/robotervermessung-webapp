'use client';

import React from 'react';

import { Typography } from '@/src/components/Typography';
import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

type TrajectoryCardProps = {
  currentTrajectory: TrajectoryData;
  trajectoriesHeader: TrajectoryHeader[];
};

export default function TrajectoryCard({
  currentTrajectory,
  trajectoriesHeader,
}: TrajectoryCardProps) {
  const searchedIndex = currentTrajectory.trajectoryHeaderId;
  const currentTrajectoryID = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
  );

  if (trajectoriesHeader.length === 0 || currentTrajectoryID === -1) {
    return <Typography as="h1">no trajectory found</Typography>;
  }

  const currentTrajectoryData = trajectoriesHeader[currentTrajectoryID];

  const headers = Object.keys(currentTrajectoryData).filter(
    (key) => !key.includes('_'),
  );

  return (
    <div className="mx-2 my-14 rounded-xl bg-gray-200 p-5 drop-shadow-md">
      <Typography as="h4" className="text-lg font-light text-primary">
        <div>
          <Typography as="h2" className="text-lg font-bold">
            trajectory info
          </Typography>
          {headers.map((header) => (
            <ul key={header}>
              <li>
                {`${header}: ${currentTrajectoryData[header as keyof TrajectoryHeader]}`}
              </li>
            </ul>
          ))}
        </div>
      </Typography>
    </div>
  );
}
