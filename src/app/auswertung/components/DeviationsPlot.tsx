/* eslint-disable react/button-has-type */

'use client';

import { Loader2 } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

import {
  getAuswertungInfoById,
  getDFDPositionById,
  getDTWPositionById,
  getEAPositionById,
  getQADOrientationById,
  getQDTWOrientationById,
  getSIDTWPositionById,
} from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';
import { PosDeviationPlot2D } from '@/src/app/auswertung/components/PosDeviationPlot2D';
import { PosDeviationPlot3D } from '@/src/app/auswertung/components/PosDeviationPlot3D';

import { OriDeviationPlot2D } from './OriDeviationPlot2D';

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface DeviationsPlotProps {
  hasDeviationData: boolean;
  hasOrientationData: boolean;
  bahnId: string;
  selectedSegment: string;
}

export const DeviationsPlot: React.FC<DeviationsPlotProps> = ({
  hasDeviationData,
  hasOrientationData,
  bahnId,
  selectedSegment,
}) => {
  // Zentrale States für alle Kontrollen
  const [posMetrics, setPosMetrics] = useState<{
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

  const [oriMetrics, setOriMetrics] = useState<{
    qad: MetricState;
    qdtw: MetricState;
  }>({
    qad: { isLoaded: false, isLoading: false, visible: false },
    qdtw: { isLoaded: false, isLoading: false, visible: false },
  });

  // Zentrale Daten States
  const [currentEuclideanDeviation, setCurrentEuclideanDeviation] = useState<
    any[]
  >([]);
  const [currentDiscreteFrechetDeviation, setCurrentDiscreteFrechetDeviation] =
    useState<any[]>([]);
  const [currentSIDTWDeviation, setCurrentSIDTWDeviation] = useState<any[]>([]);
  const [currentDTWDeviation, setCurrentDTWDeviation] = useState<any[]>([]);
  const [currentQADDeviation, setCurrentQADDeviation] = useState<any[]>([]);
  const [currentQDTWDeviation, setCurrentQDTWDeviation] = useState<any[]>([]);
  const [currentBahnInfo, setCurrentBahnInfo] = useState<any>(null);
  const [currentAuswertungInfo, setCurrentAuswertungInfo] = useState<any>({
    info_euclidean: [],
    info_dfd: [],
    info_sidtw: [],
    info_dtw: [],
    info_qdtw: [],
    info_qad: [],
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
  const loadPosMetricData = useCallback(
    async (metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw' ) => {
      if (!bahnId) return;

      // Wenn bereits geladen, toggle visibility
      if (posMetrics[metricType].isLoaded) {
        setPosMetrics((prev) => ({
          ...prev,
          [metricType]: {
            ...prev[metricType],
            visible: !prev[metricType].visible,
          },
        }));
        return;
      }

      // Loading state setzen
      setPosMetrics((prev) => ({
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

        setPosMetrics((prev) => ({
          ...prev,
          [metricType]: { isLoaded: true, isLoading: false, visible: true },
        }));
      } catch (error) {
        setPosMetrics((prev) => ({
          ...prev,
          [metricType]: { ...prev[metricType], isLoading: false },
        }));
      }
    },
    [bahnId, posMetrics],
  );

  const loadOriMetricData = useCallback(
    async (metricType: 'qad' | 'qdtw') => {
      if (!bahnId) return;

      // Wenn bereits geladen, toggle visibility
      if (oriMetrics[metricType].isLoaded) {
        setOriMetrics((prev) => ({
          ...prev,
          [metricType]: {
            ...prev[metricType],
            visible: !prev[metricType].visible,
          },
        }));
        return;
      }

      // Loading state setzen
      setOriMetrics((prev) => ({
        ...prev,
        [metricType]: { ...prev[metricType], isLoading: true },
      }));

      try {
        let data;
        switch (metricType) {
          case 'qad':
            data = await getQADOrientationById(bahnId);
            setCurrentQADDeviation(data);
            break;
          case 'qdtw':
            data = await getQDTWOrientationById(bahnId);
            setCurrentQDTWDeviation(data);
            break;
          default:
            throw new Error(`Unknown metric type: ${metricType}`);
        }

        setOriMetrics((prev) => ({
          ...prev,
          [metricType]: { isLoaded: true, isLoading: false, visible: true },
        }));
      } catch (error) {
        setOriMetrics((prev) => ({
          ...prev,
          [metricType]: { ...prev[metricType], isLoading: false },
        }));
      }
    },
    [bahnId, oriMetrics],
  );

  // Verfügbarkeit der Daten prüfen
  const hasEAData = currentAuswertungInfo.info_euclidean.length > 0;
  const hasDFDData = currentAuswertungInfo.info_dfd.length > 0;
  const hasSIDTWData = currentAuswertungInfo.info_sidtw.length > 0;
  const hasDTWData = currentAuswertungInfo.info_dtw.length > 0;
  const hasQADData = currentAuswertungInfo.info_qad.length > 0;
  const hasQDTWData = currentAuswertungInfo.info_qdtw.length > 0;

  // Automatisch EA laden, wenn verfügbar
  useEffect(() => {
    if (hasEAData && !posMetrics.ea.isLoaded && !posMetrics.ea.isLoading) {
      loadPosMetricData('ea');
    }
  }, [hasEAData, posMetrics.ea.isLoaded, posMetrics.ea.isLoading, loadPosMetricData]);

  useEffect(() => {
    if (hasQADData && !oriMetrics.qad.isLoaded && !oriMetrics.qad.isLoading) {
      loadOriMetricData('qad');
    }
  }, [hasQADData, oriMetrics.qad.isLoaded, oriMetrics.qad.isLoading, loadOriMetricData]);

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
      return 'bg-emerald-600 text-white hover:bg-red-700';
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

  const posMetricLoaded = Object.values(posMetrics).some((m) => m.isLoaded);
  const oriMetricLoaded = Object.values(oriMetrics).some((m) => m.isLoaded);

  return (
    <div className="w-full space-y-4 p-4">
      {/* Zentralisierte Kontrollen */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-white p-4 shadow-sm">
        <div>Position:</div>
        {hasEAData && (
          <button
            onClick={() => loadPosMetricData('ea')}
            disabled={posMetrics.ea.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.ea)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.ea, 'EA')}
          </button>
        )}

        {hasSIDTWData && (
          <button
            onClick={() => loadPosMetricData('sidtw')}
            disabled={posMetrics.sidtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.sidtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.sidtw, 'SIDTW')}
          </button>
        )}

        {hasDTWData && (
          <button
            onClick={() => loadPosMetricData('dtw')}
            disabled={posMetrics.dtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.dtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.dtw, 'DTW')}
          </button>
        )}

        {hasDFDData && (
          <button
            onClick={() => loadPosMetricData('dfd')}
            disabled={posMetrics.dfd.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.dfd)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.dfd, 'DFD')}
          </button>
        )}

        <div className='ml-2 border-l pl-6'>Orientierung:</div>
        {hasQADData && (
          <button
            onClick={() => loadOriMetricData('qad')}
            disabled={oriMetrics.qad.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(oriMetrics.qad)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(oriMetrics.qad, 'QAD')}
          </button>
        )}

        {hasQDTWData && (
          <button
            onClick={() => loadOriMetricData('qdtw')}
            disabled={oriMetrics.qdtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(oriMetrics.qdtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(oriMetrics.qdtw, 'QDTW')}
          </button>
        )}
      </div>

      {/* Plots rendern nur wenn Daten geladen */}
      {posMetricLoaded && (
        <div className="flex justify-items-stretch space-x-2">
          <PosDeviationPlot2D
            hasDeviationData={hasDeviationData}
            selectedSegment={selectedSegment}
            // Übergabe aller benötigten Daten und States
            metrics={posMetrics}
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
            metrics={posMetrics}
            currentEuclideanDeviation={currentEuclideanDeviation}
            currentDiscreteFrechetDeviation={currentDiscreteFrechetDeviation}
            currentSIDTWDeviation={currentSIDTWDeviation}
            currentDTWDeviation={currentDTWDeviation}
          />
        </div>
      )}
      {oriMetricLoaded && (
        <div className="flex justify-items-stretch space-x-2">
          <OriDeviationPlot2D
            hasOrientationData={hasOrientationData}
            selectedSegment={selectedSegment}
            // Übergabe aller benötigten Daten und States
            metrics={oriMetrics}
            currentQADDeviation={currentQADDeviation}
            currentQDTWDeviation={currentQDTWDeviation}
            currentBahnInfo={currentBahnInfo}
          />
        </div>
      )}
    </div>
  );
};
