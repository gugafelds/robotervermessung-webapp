/* eslint-disable react/button-has-type */

'use client';

import { Loader2 } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

import {
  getEDPositionById,
  getEvaluationInfoById,
  getGDOrientationById,
  getQDTWOrientationById,
  getSIDTWPositionById,
} from '@/src/actions/evaluation.service';
import { getTrajInfoById } from '@/src/actions/motion.service';
import { PosDeviationPlot2D } from '@/src/app/evaluation/components/PosDeviationPlot2D';
import { PosDeviationPlot3D } from '@/src/app/evaluation/components/PosDeviationPlot3D';

import { OriDeviationPlot2D } from './OriDeviationPlot2D';

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface DeviationsPlotProps {
  hasDeviationData: boolean;
  hasOrientationData: boolean;
  trajID: string;
  selectedSegment: string;
}

export const DeviationsPlot: React.FC<DeviationsPlotProps> = ({
  hasDeviationData,
  hasOrientationData,
  trajID,
  selectedSegment,
}) => {
  const [posMetrics, setPosMetrics] = useState<{
    ED: MetricState;
    SIDTW: MetricState;
  }>({
    ED: { isLoaded: false, isLoading: false, visible: false },
    SIDTW: { isLoaded: false, isLoading: false, visible: false },
  });

  const [oriMetrics, setOriMetrics] = useState<{
    GD: MetricState;
    QDTW: MetricState;
  }>({
    GD: { isLoaded: false, isLoading: false, visible: false },
    QDTW: { isLoaded: false, isLoading: false, visible: false },
  });

  // Zentrale Daten States
  const [currentEuclideanDeviation, setCurrentEuclideanDeviation] = useState<
    any[]
  >([]);
  const [currentSIDTWDeviation, setCurrentSIDTWDeviation] = useState<any[]>([]);
  const [currentGDDeviation, setCurrentGDDeviation] = useState<any[]>([]);
  const [currentQDTWDeviation, setCurrentQDTWDeviation] = useState<any[]>([]);
  const [currentBahnInfo, setCurrentBahnInfo] = useState<any>(null);
  const [currentEvaluationInfo, setCurrentEvaluationInfo] = useState<any>({
    EDInfo: [],
    SIDTWInfo: [],
    QDTWInfo: [],
    GDInfo: [],
  });

  // Bahn-Info laden
  const loadBahnInfo = useCallback(async () => {
    try {
      const bahnInfo = await getTrajInfoById(trajID);
      setCurrentBahnInfo(bahnInfo);
    } catch (error) {
      /* empty */
    }
  }, [trajID]);

  // Auswertungsinformationen laden
  const loadAuswertungInfo = useCallback(async () => {
    try {
      const evaluationInfo = await getEvaluationInfoById(trajID);
      setCurrentEvaluationInfo(evaluationInfo);
    } catch (error) {
      // Silently handle error
    }
  }, [trajID]);

  useEffect(() => {
    if (trajID) {
      loadBahnInfo();
      loadAuswertungInfo();
    }
  }, [trajID, loadBahnInfo, loadAuswertungInfo]);

  // Zentrale Funktion zum Laden der Metrik-Daten
  const loadPosMetricData = useCallback(
    async (metricType: 'ED' | 'SIDTW') => {
      if (!trajID) return;

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
          case 'ED':
            data = await getEDPositionById(trajID);
            setCurrentEuclideanDeviation(data);
            break;
          case 'SIDTW':
            data = await getSIDTWPositionById(trajID);
            setCurrentSIDTWDeviation(data);
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
    [trajID, posMetrics],
  );

  const loadOriMetricData = useCallback(
    async (metricType: 'GD' | 'QDTW') => {
      if (!trajID) return;

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
          case 'GD':
            data = await getGDOrientationById(trajID);
            setCurrentGDDeviation(data);
            break;
          case 'QDTW':
            data = await getQDTWOrientationById(trajID);
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
    [trajID, oriMetrics],
  );

  // Verfügbarkeit der Daten prüfen
  const hasEDData = currentEvaluationInfo.EDInfo.length > 0;
  const hasSIDTWData = currentEvaluationInfo.SIDTWInfo.length > 0;
  // const hasDTWData = currentEvaluationInfo.info_dtw.length > 0;
  const hasGDData = currentEvaluationInfo.GDInfo?.length > 0;
  const hasQDTWData = currentEvaluationInfo.QDTWInfo?.length > 0;

  // Automatisch EA laden, wenn verfügbar
  useEffect(() => {
    if (hasEDData && !posMetrics.ED.isLoaded && !posMetrics.ED.isLoading) {
      loadPosMetricData('ED');
    }
  }, [
    hasEDData,
    posMetrics.ED.isLoaded,
    posMetrics.ED.isLoading,
    loadPosMetricData,
  ]);

  useEffect(() => {
    if (hasGDData && !oriMetrics.GD.isLoaded && !oriMetrics.GD.isLoading) {
      loadOriMetricData('GD');
    }
  }, [
    hasGDData,
    oriMetrics.GD.isLoaded,
    oriMetrics.GD.isLoading,
    loadOriMetricData,
  ]);

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
      <div className="m-4 rounded-lg border border-gray-500 bg-gray-200 p-6 text-center text-gray-500">
        Keine Abweichungsdaten verfügbar
      </div>
    );
  }

  const posMetricLoaded = Object.values(posMetrics).some((m) => m.isLoaded);
  const oriMetricLoaded = Object.values(oriMetrics).some((m) => m.isLoaded);

  return (
    <div className="w-full space-y-4 p-4">
      {/* Zentralisierte Kontrollen */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-gray-500 bg-white p-4">
        <div>Position:</div>
        {hasEDData && (
          <button
            onClick={() => loadPosMetricData('ED')}
            disabled={posMetrics.ED.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.ED)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.ED, 'ED')}
          </button>
        )}

        {hasSIDTWData && (
          <button
            onClick={() => loadPosMetricData('SIDTW')}
            disabled={posMetrics.SIDTW.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.SIDTW)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.SIDTW, 'SIDTW')}
          </button>
        )}

        {/* hasDTWData && (
          <button
            onClick={() => loadPosMetricData('dtw')}
            disabled={posMetrics.dtw.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(posMetrics.dtw)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(posMetrics.dtw, 'DTW')}
          </button>
        ) */}

        {hasGDData ||
          (hasQDTWData && (
            <div className="ml-2 border-l border-gray-200 pl-6">
              Orientierung:
            </div>
          ))}
        {hasGDData && (
          <button
            onClick={() => loadOriMetricData('GD')}
            disabled={oriMetrics.GD.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(oriMetrics.GD)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(oriMetrics.GD, 'GD')}
          </button>
        )}

        {hasQDTWData && (
          <button
            onClick={() => loadOriMetricData('QDTW')}
            disabled={oriMetrics.QDTW.isLoading}
            className={`inline-flex items-center space-x-2 rounded px-3 py-1 text-sm 
              ${getButtonColorClass(oriMetrics.QDTW)} 
              disabled:bg-gray-300 disabled:text-gray-600`}
          >
            {getButtonContent(oriMetrics.QDTW, 'QDTW')}
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
            currentSIDTWDeviation={currentSIDTWDeviation}
            currentBahnInfo={currentBahnInfo}
          />
          <PosDeviationPlot3D
            hasDeviationData={hasDeviationData}
            selectedSegment={selectedSegment}
            // Übergabe aller benötigten Daten und States
            metrics={posMetrics}
            currentEuclideanDeviation={currentEuclideanDeviation}
            currentSIDTWDeviation={currentSIDTWDeviation}
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
            currentGDDeviation={currentGDDeviation}
            currentQDTWDeviation={currentQDTWDeviation}
            currentBahnInfo={currentBahnInfo}
          />
        </div>
      )}
    </div>
  );
};
