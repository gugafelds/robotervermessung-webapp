'use client';

import { redirect } from 'next/navigation';

import { useTrajectory } from '@/src/providers/trajectory.provider';

export default function TrajectoriesPage() {
  const {
    bahnInfo: [{ bahnID }],
  } = useTrajectory();
  

  return redirect(`/trajectories/${bahnID}`);
}
