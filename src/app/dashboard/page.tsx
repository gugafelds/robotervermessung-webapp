'use client';

import { Loader } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getDashboardData } from '@/src/actions/dashboard.service';
import type { PerformerData } from '@/types/dashboard.types';

import DashboardClient from './components/DashboardClient';

interface BasicDashboardData {
  filenamesCount: number;
  bahnenCount: number;
  medianSIDTW?: number;
  meanSIDTW?: number;
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
}

export default function DashboardPage() {
  const [data, setData] = useState<BasicDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const dashboardResult = await getDashboardData();
        setData({
          filenamesCount: dashboardResult.filenamesCount,
          bahnenCount: dashboardResult.bahnenCount,
          medianSIDTW: dashboardResult.medianSIDTW,
          meanSIDTW: dashboardResult.meanSIDTW,
          bestPerformers: dashboardResult.bestPerformers,
          worstPerformers: dashboardResult.worstPerformers,
        });
      } catch (error) {
        setData(null);
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
    <div className="flex justify-center">
      <DashboardClient
        filenamesCount={data.filenamesCount}
        bahnenCount={data.bahnenCount}
        medianSIDTW={data.medianSIDTW}
        meanSIDTW={data.meanSIDTW}
        bestPerformers={data.bestPerformers}
        worstPerformers={data.worstPerformers}
      />
    </div>
  );
}
