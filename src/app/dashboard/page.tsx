'use client';

import { Loader } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getDashboardData } from '@/src/actions/dashboard.service';

import DashboardClient from './components/DashboardClient';

interface BasicDashboardData {
  filenamesCount: number;
  bahnenCount: number;
}

export default function DashboardPage() {
  const [data, setData] = useState<BasicDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Nur die leichten Count-Daten laden
        const dashboardResult = await getDashboardData();
        setData({
          filenamesCount: dashboardResult.filenamesCount,
          bahnenCount: dashboardResult.bahnenCount,
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
    <DashboardClient
      filenamesCount={data.filenamesCount}
      bahnenCount={data.bahnenCount}
    />
  );
}
