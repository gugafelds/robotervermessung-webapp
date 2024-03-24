'use client';

import { useApp } from '@/src/providers/app.provider';
import type { TrajectoryData } from '@/types/main';

import { TrajectoryPlot } from './TrajectoryPlot';
import TrajectorySidebar from './TrajectorySidebar';

type TrajectoryContainerProps = {
  currentTrajectory: TrajectoryData;
};

export function TrajectoryContainer({
  currentTrajectory,
}: TrajectoryContainerProps) {
  const { trajectoriesHeader } = useApp();

  if (!trajectoriesHeader) {
    return <div />;
  }

  return (
    <div className="flex space-x-32">
      <TrajectorySidebar
        currentTrajectory={currentTrajectory}
        trajectoriesHeader={trajectoriesHeader}
      />

      <TrajectoryPlot
        trajectoriesHeader={trajectoriesHeader}
        currentTrajectory={currentTrajectory}
      />
    </div>
  );
}
