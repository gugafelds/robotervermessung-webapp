'use client';

import { redirect } from 'next/navigation';

import { useTrajectory } from '@/src/providers/trajectory.provider';

export default function TrajectoriesPage() {
  const {
    trajectoriesHeader: [{ dataId }],
    
  } = useTrajectory();

  return redirect(`/trajectories/${dataId}`);
}
