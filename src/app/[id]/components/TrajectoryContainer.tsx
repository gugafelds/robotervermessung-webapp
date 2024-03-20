'use client';

import type { Data } from 'plotly.js';
import { useEffect } from 'react';

import { useApp } from '@/src/providers/app.provider';
import type { TrajectoryData, TrajectoryHeader } from '@/types/main';

import TrajectoryCard from './TrajectoryCard';
import TrajectoryPlot from './TrajectoryPlot';

type TrajectoryContainerProps = {
  realTrajectory: Data;
  idealTrajectory: Data;
  currentTrajectory: TrajectoryData;
  trajectoriesHeader: TrajectoryHeader[];
};

export const TrajectoryContainer = ({
  realTrajectory,
  idealTrajectory,
  currentTrajectory,
  trajectoriesHeader,
}: TrajectoryContainerProps) => {
  const { setCurrentTrajectory } = useApp();
  useEffect(() => {
    setCurrentTrajectory(currentTrajectory);
  }, [currentTrajectory, setCurrentTrajectory]);

  return (
    <main>
      <div style={{ display: 'flex' }}>
        <div style={{ flex: 1 }}>
          <TrajectoryPlot
            realTrajectory={realTrajectory}
            idealTrajectory={idealTrajectory}
          />
        </div>
        <div style={{ flex: 1, marginLeft: '20px' }}>
          <TrajectoryCard
            currentTrajectory={currentTrajectory}
            trajectoriesHeader={trajectoriesHeader}
          />
        </div>
      </div>
    </main>
  );
};
