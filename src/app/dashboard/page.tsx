'use client';

import { Loader } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  getDashboardData,
  getWorkareaData,
} from '@/src/actions/dashboard.service';
import type { DashboardData } from '@/types/dashboard.types';

import DashboardClient from './components/DashboardClient';

interface WorkareaPoint {
  x: number;
  y: number;
  z: number;
  sidtw: number;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [workareaData, setWorkareaData] = useState<WorkareaPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [dashboardResult, workareaResult] = await Promise.all([
          getDashboardData(),
          getWorkareaData(),
        ]);
        setData(dashboardResult);
        setWorkareaData(workareaResult.points || []);
      } catch (error) {
        setData(null);
        setWorkareaData([]);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader className="size-10 animate-spin text-blue-950" />
      </div>
    );
  }

  if (!data) {
    return <div className="p-6">Fehler: Keine Daten verfügbar</div>;
  }

  return (
    <DashboardClient
      filenamesCount={data.filenamesCount}
      bahnenCount={data.bahnenCount}
      stats={data.stats}
      workareaPoints={workareaData}
    />
  );
}
