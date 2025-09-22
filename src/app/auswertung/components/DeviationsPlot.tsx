/* eslint-disable react/button-has-type */

'use client';

import { Loader2 } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

import {
  getAuswertungInfoById,
  getDFDPositionById,
  getDTWPositionById,
  getEAPositionById,
  getSIDTWPositionById,
} from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';
import { PosDeviationPlot2D } from '@/src/app/auswertung/components/PosDeviationPlot2D';
import { PosDeviationPlot3D } from '@/src/app/auswertung/components/PosDeviationPlot3D';

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface DeviationsPlotProps {
  hasDeviationData: boolean;
  bahnId: string;
  selectedSegment: string;
}

export const DeviationsPlot: React.FC<DeviationsPlotProps> = ({
  hasDeviationData,
  bahnId,
  selectedSegment,
}) => {
  // Zentrale States für alle Kontrollen
  const [metrics, setMetrics] = useState<{
    ea: MetricState;
    dfd: MetricState;
    sidtw: MetricState;
    dtw: MetricState;
  }>({
    ea: { isLoaded: false, isLoading: false, visible: false },
    dfd: { isLoaded: false, isLoading: false, visible: false },
    sidtw: { isLoaded: false, isLoading: false, visible: false },
    dtw: { isLoaded: false, isLoading: false, visible: false },
  });

  // Zentrale Daten States
  const [currentEuclideanDeviation, setCurrentEuclideanDeviation] = useState<
    any[]
  >([]);
  const [currentDiscreteFrechetDeviation, setCurrentDiscreteFrechetDeviation] =
    useState<any[]>([]);
  const [currentSIDTWDeviation, setCurrentSIDTWDeviation] = useState<any[]>([]);
  const [currentDTWDeviation, setCurrentDTWDeviation] = useState<any[]>([]);
  const [currentBahnInfo, setCurrentBahnInfo] = useState<any>(null);
  const [currentAuswertungInfo, setCurrentAuswertungInfo] = useState<any>({
    info_euclidean: [],
    info_dfd: [],
    info_sidtw: [],
    info_dtw: [],
  });

  // Bahn-Info laden
  const loadBahnInfo = useCallback(async () => {
    try {
      const bahnInfo = await getBahnInfoById(bahnId);
      setCurrentBahnInfo(bahnInfo);
    } catch (error) {
      /* empty */
    }
  }, [bahnId]);

  // Auswertungsinformationen laden
  const loadAuswertungInfo = useCallback(async () => {
    try {
      const auswertungInfo = await getAuswertungInfoById(bahnId);
      setCurrentAuswertungInfo(auswertungInfo);
    } catch (error) {
      // Silently handle error
    }
  }, [bahnId]);

  useEffect(() => {
    if (bahnId) {
      loadBahnInfo();
      loadAuswertungInfo();
    }
  }, [bahnId, loadBahnInfo, loadAuswertungInfo]);

  // Zentrale Funktion zum Laden der Metrik-Daten
  const loadMetricData = useCallback(
    async (metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw') => {
      if (!bahnId) return;

      // Wenn bereits geladen, toggle visibility
      if (metrics[metricType].isLoaded) {
        setMetrics((prev) => ({
          ...prev,
          [metricType]: {
            ...prev[metricType],
            visible: !prev[metricType].visible,
          },
        }));
        return;
      }

      // Loading state setzen
      setMetrics((prev) => ({
        ...prev,
        [metricType]: { ...prev[metricType], isLoading: true },
      }));

      try {
        let data;
        switch (metricType) {
          case 'ea':
            data = await getEAPositionById(bahnId);
            setCurrentEuclideanDeviation(data);
            break;
          case 'dfd':
            data = await getDFDPositionById(bahnId);
            setCurrentDiscreteFrechetDeviation(data);
            break;
          case 'sidtw':
            data = await getSIDTWPositionById(bahnId);
            setCurrentSIDTWDeviation(data);
            break;
          case 'dtw':
            data = await getDTWPositionById(bahnId);
            setCurrentDTWDeviation(data);
            break;
          default:
            throw new Error(`Unknown metric type: ${metricType}`);
        }

        setMetrics((prev) => ({
          ...prev,
          [metricType]: { isLoaded: true, isLoading: false, visible: true },
        }));
      } catch (error) {
        setMetrics((prev) => ({
          ...prev,
          [metricType]: { ...prev[metricType], isLoading: false },
        }));
      }
    },
    [bahnId, metrics],
  );

  // Verfügbarkeit der Daten prüfen
  const hasEAData = currentAuswertungInfo.info_euclidean.length > 0;
  const hasDFDData = currentAuswertungInfo.info_dfd.length > 0;
  const hasSIDTWData = currentAuswertungInfo.info_sidtw.length > 0;
  const hasDTWData = currentAuswertungInfo.info_dtw.length > 0;

  // Automatisch EA laden, wenn verfügbar
  useEffect(() => {
    if (hasEAData && !metrics.ea.isLoaded && !metrics.ea.isLoading) {
      loadMetricData('ea');
    }
  }, [hasEAData, metrics.ea.isLoaded, metrics.ea.isLoading, loadMetricData]);

  const getButtonContent = (metric: MetricState, label: string) => {
    if (metric.isLoading) {
      return (
        <>
          <Loader2 className="size-4 animate-spin" />
          <span>Lädt {label}...</span>
        </>
      );
    }

    if (metric.isLoaded) {
      return metric.visible ? `${label} ausblenden` : `${label} einblenden`;
    }

    return `${label} laden`;
  };

  const getButtonColorClass = (metric: MetricState) => {
    if (!metric.isLoaded) {
      return 'bg-primary text-white hover:bg-primary/80';
    }
    if (metric.visible) {
      return 'bg-emerald-600 text-white hover:bg-emerald-700';
    }
    return 'bg-gray-500 text-white hover:bg-gray-600';
  };

  if (!hasDeviationData) {
    return (
      <div className="w-full">
        <button
          disabled
          className="rounded bg-gray-300 px-4 py-2 text-gray-600"
        >
          Keine Abweichungsdaten verfügbar
        </button>
      </div>
    );
  }

  const anyMetricLoaded = Object.values(metrics).some((m) => m.isLoaded);

  return (
    <div className="w-full space-y-4 p-4">
      {/* Zentralisierte Kontrollen */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-white p-4 shadow-sm">
        <div>Verfügbare Metriken:</div>
        {hasEAData && (
          <button
            onClick={() => loadMetricData('ea')}
            disabled={metrics.ea.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(metrics.ea)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(metrics.ea, 'EA')}
          </button>
        )}

        {hasSIDTWData && (
          <button
            onClick={() => loadMetricData('sidtw')}
            disabled={metrics.sidtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(metrics.sidtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(metrics.sidtw, 'SIDTW')}
          </button>
        )}

        {hasDTWData && (
          <button
            onClick={() => loadMetricData('dtw')}
            disabled={metrics.dtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(metrics.dtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(metrics.dtw, 'DTW')}
          </button>
        )}

        {hasDFDData && (
          <button
            onClick={() => loadMetricData('dfd')}
            disabled={metrics.dfd.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(metrics.dfd)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(metrics.dfd, 'DFD')}
          </button>
        )}
      </div>

      {/* Plots rendern nur wenn Daten geladen */}
      {anyMetricLoaded && (
        <div className="flex justify-items-stretch space-x-2">
          <PosDeviationPlot2D
            hasDeviationData={hasDeviationData}
            selectedSegment={selectedSegment}
            // Übergabe aller benötigten Daten und States
            metrics={metrics}
            currentEuclideanDeviation={currentEuclideanDeviation}
            currentDiscreteFrechetDeviation={currentDiscreteFrechetDeviation}
            currentSIDTWDeviation={currentSIDTWDeviation}
            currentDTWDeviation={currentDTWDeviation}
            currentBahnInfo={currentBahnInfo}
          />
          <PosDeviationPlot3D
            hasDeviationData={hasDeviationData}
            selectedSegment={selectedSegment}
            // Übergabe aller benötigten Daten und States
            metrics={metrics}
            currentEuclideanDeviation={currentEuclideanDeviation}
            currentDiscreteFrechetDeviation={currentDiscreteFrechetDeviation}
            currentSIDTWDeviation={currentSIDTWDeviation}
            currentDTWDeviation={currentDTWDeviation}
          />
        </div>
      )}
    </div>
  );
};
