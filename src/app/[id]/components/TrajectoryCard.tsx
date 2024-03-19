'use client';

import React from 'react';
import type { Trajectory, AxisData } from '@/types/main';
import { Typography } from '@/src/components/Typography';


type TrajectoryCardProps = {
    currentTrajectory: AxisData;
    trajectories: Trajectory[];
  };
  
  export default function TrajectoryCard({
    currentTrajectory,
    trajectories
    
  }: TrajectoryCardProps) {
    const searchedIndex = currentTrajectory.trajectoryHeaderId
    const currentTrajectoryID = trajectories.findIndex(
      (item) => item.dataId === searchedIndex,
    );

    if (trajectories.length === 0 || currentTrajectoryID === -1) {
      return <Typography as="h1">Nenhuma trajetória encontrada.</Typography>;
    }
    
    const currentTrajectoryData = trajectories[currentTrajectoryID];
    
    const headers = Object.keys(currentTrajectoryData).filter(
      key => !key.includes('_')
    );



    return (
      <div className="p-5 bg-gray-200 mx-2 my-14 rounded-xl drop-shadow-md">
        <Typography as="h4" className="font-light text-lg text-primary">
          <div>
            <Typography as="h2" className="font-bold text-lg">trajectory info</Typography>
            {headers.map(header => (
              <ul key={header}>
                <li>
                  {`${header}: ${currentTrajectoryData[header as keyof Trajectory]}`}
                </li>
              </ul>
            ))}
          </div>
        </Typography>
      </div>
    );
  }