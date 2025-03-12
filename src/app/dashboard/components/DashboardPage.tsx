/* eslint-disable react/button-has-type,no-console */

'use client';

import { Loader } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { FallbackProps } from 'react-error-boundary';
import { ErrorBoundary } from 'react-error-boundary';

import { getDashboardData } from '@/src/actions/dashboard.service';

import DashboardClient from './DashboardClient';

// Definiere Typen für sichere Datenübergabe
interface DashboardData {
  filenamesCount: number;
  bahnenCount: number;
  componentCounts: {
    bahnPoseIst: number;
    bahnTwistIst: number;
    bahnTwistSoll: number;
    bahnAccelIst: number;
    bahnPositionSoll: number;
    bahnOrientationSoll: number;
    bahnJointStates: number;
    bahnEvents: number;
    bahnPoseTrans: number;
  };
  analysisCounts: {
    infoDFD: number;
    infoDTW: number;
    infoEA: number;
    infoLCSS: number;
    infoSIDTW: number;
  };
}

// Standardwerte für den Fall eines Fehlers
const DEFAULT_DATA: DashboardData = {
  filenamesCount: 0,
  bahnenCount: 0,
  componentCounts: {
    bahnPoseIst: 0,
    bahnTwistIst: 0,
    bahnTwistSoll: 0,
    bahnAccelIst: 0,
    bahnPositionSoll: 0,
    bahnOrientationSoll: 0,
    bahnJointStates: 0,
    bahnEvents: 0,
    bahnPoseTrans: 0,
  },
  analysisCounts: {
    infoDFD: 0,
    infoDTW: 0,
    infoEA: 0,
    infoLCSS: 0,
    infoSIDTW: 0,
  },
};

// Fallback-Komponente für Fehler mit korrekten TypeScript-Typen
function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6">
      <h2 className="mb-4 text-xl font-bold text-red-700">
        Beim Laden des Dashboards ist ein Fehler aufgetreten
      </h2>
      <p className="mb-4 text-red-600">Fehlermeldung: {error.message}</p>
      <button
        onClick={resetErrorBoundary}
        className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
      >
        Erneut versuchen
      </button>
    </div>
  );
}

// Client-Komponente für das Dashboard
export default function DashboardPage() {
  const [data, setData] = useState<DashboardData>(DEFAULT_DATA);
  const [loading, setLoading] = useState(true);

  // Lade Daten beim ersten Rendern
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getDashboardData();

        // Stelle sicher, dass alle Werte Zahlen sind
        const sanitizedData: DashboardData = {
          filenamesCount: Number(result.filenamesCount) || 0,
          bahnenCount: Number(result.bahnenCount) || 0,
          componentCounts: {
            bahnPoseIst: Number(result.componentCounts?.bahnPoseIst) || 0,
            bahnTwistIst: Number(result.componentCounts?.bahnTwistIst) || 0,
            bahnTwistSoll: Number(result.componentCounts?.bahnTwistSoll) || 0,
            bahnAccelIst: Number(result.componentCounts?.bahnAccelIst) || 0,
            bahnPositionSoll:
              Number(result.componentCounts?.bahnPositionSoll) || 0,
            bahnOrientationSoll:
              Number(result.componentCounts?.bahnOrientationSoll) || 0,
            bahnJointStates:
              Number(result.componentCounts?.bahnJointStates) || 0,
            bahnEvents: Number(result.componentCounts?.bahnEvents) || 0,
            bahnPoseTrans: Number(result.componentCounts?.bahnPoseTrans) || 0,
          },
          analysisCounts: {
            infoDFD: Number(result.analysisCounts?.infoDFD) || 0,
            infoDTW: Number(result.analysisCounts?.infoDTW) || 0,
            infoEA: Number(result.analysisCounts?.infoEA) || 0,
            infoLCSS: Number(result.analysisCounts?.infoLCSS) || 0,
            infoSIDTW: Number(result.analysisCounts?.infoSIDTW) || 0,
          },
        };

        setData(sanitizedData);
      } catch (error) {
        console.error('Fehler beim Laden der Dashboard-Daten:', error);
        // Bei Fehlern verwenden wir die Standardwerte
        setData(DEFAULT_DATA);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Zeige Ladezustand
  if (loading) {
    return (
      <div className="flex h-fullscreen w-full flex-wrap justify-center overflow-scroll p-4">
        <div className="my-10 flex size-fit flex-col items-center justify-center rounded-xl bg-gray-200 p-2 shadow-sm">
          <div className="animate-spin">
            <Loader className="mx-auto w-10" color="#003560" />
          </div>
          <span className="mt-2">Es lädt...</span>
        </div>
      </div>
    );
  }

  // Rendere die Client-Komponente mit den geladenen Daten
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => window.location.reload()}
    >
      <DashboardClient
        bahnenCount={data.bahnenCount}
        filenamesCount={data.filenamesCount}
        componentCounts={data.componentCounts}
        analysisCounts={data.analysisCounts}
      />
    </ErrorBoundary>
  );
}
