'use client';

import { redirect } from 'next/navigation';

import { useApp } from '@/src/providers/app.provider';

export default function TrajectoriesPage() {
  const { trajectoriesHeader } = useApp();

  return redirect(`/trajectories/${trajectoriesHeader[0].dataId}`);
}
