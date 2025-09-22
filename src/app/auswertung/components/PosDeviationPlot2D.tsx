/* eslint-disable react/button-has-type,no-console */

'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { Loader2 } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useCallback, useEffect, useState } from 'react';

import {
  getAuswertungInfoById,
  getDFDPositionById,
  getDTWPositionById,
  getEAPositionById,
  getSIDTWPositionById,
} from '@/src/actions/auswertung.service';
import { getBahnInfoById } from '@/src/actions/bewegungsdaten.service';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  EA: { line: '#003560' },
  DFD: { line: '#e63946' },
  DTW: { line: '#774936' },
  SIDTW: { line: '#2a9d8f' },
};

interface MetricState {
  isLoaded: boolean;
  isLoading: boolean;
  visible: boolean;
}

interface SegmentOption {
  label: string;
  value: string;
}

interface PosDeviationPlot2DProps {
  hasDeviationData: boolean;
  bahnId: string;
  selectedSegment: string;
  onSegmentChange: (segment: string) => void;
}

export const PosDeviationPlot2D: React.FC<PosDeviationPlot2DProps> = ({
  hasDeviationData,
  bahnId,
  selectedSegment,
  onSegmentChange,
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [segmentOptions, setSegmentOptions] = useState<SegmentOption[]>([]);
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

  const loadBahnInfo = useCallback(async () => {
    try {
      const bahnInfo = await getBahnInfoById(bahnId);
      setCurrentBahnInfo(bahnInfo);
    } catch (error) {
      console.error('Error loading Bahn info:', error);
    }
  }, [bahnId]);

  const loadAuswertungInfo = useCallback(async () => {
    try {
      const auswertungInfo = await getAuswertungInfoById(bahnId);
      setCurrentAuswertungInfo(auswertungInfo);
    } catch (error) {
      console.error('Error loading Auswertung info:', error);
    }
  }, [bahnId]);

  useEffect(() => {
    if (bahnId) {
      loadBahnInfo();
      loadAuswertungInfo();
    }
  }, [bahnId, loadBahnInfo, loadAuswertungInfo]);

  const loadMetricData = useCallback(
    async (metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw') => {
      if (!bahnId) return;

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
            throw new Error(`Unhandled metric type: ${metricType}`);
        }

        setMetrics((prev) => ({
          ...prev,
          [metricType]: { isLoaded: true, isLoading: false, visible: true },
        }));
      } catch (error) {
        console.error(`Error loading ${metricType} data:`, error);
        setMetrics((prev) => ({
          ...prev,
          [metricType]: { ...prev[metricType], isLoading: false },
        }));
      }
    },
    [bahnId, metrics],
  );

  // Verfügbare Segmente ermitteln
  useEffect(() => {
    const getAllSegmentNumbers = (data: any[]) => {
      if (!data?.length) return [];
      return Array.from(
        new Set(
          data
            .filter((d) => d.bahnID !== d.segmentID)
            .map((d) => {
              const segNum = d.segmentID.split('_')[1];
              return parseInt(segNum, 10);
            }),
        ),
      ).sort((a, b) => a - b);
    };

    const allSegments = [
      ...getAllSegmentNumbers(currentEuclideanDeviation),
      ...getAllSegmentNumbers(currentDiscreteFrechetDeviation),
      ...getAllSegmentNumbers(currentSIDTWDeviation),
      ...getAllSegmentNumbers(currentDTWDeviation),
    ];

    const uniqueSegments = Array.from(new Set(allSegments));

    const options: SegmentOption[] = [
      { label: 'Gesamtmessung', value: 'total' },
      ...uniqueSegments.map((num) => ({
        label: `Segment ${num}`,
        value: `segment_${num}`,
      })),
    ];

    setSegmentOptions(options);
  }, [
    currentEuclideanDeviation,
    currentDiscreteFrechetDeviation,
    currentSIDTWDeviation,
    currentDTWDeviation,
  ]);

  // Verfügbare Methoden prüfen
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

  const filterDataBySegment = (data: any[]) => {
    if (!data?.length) return [];

    return data.filter((d) => {
      if (selectedSegment === 'total') {
        return d.bahnID === d.segmentID;
      }
      const segmentNum = selectedSegment.split('_')[1];
      return d.segmentID === `${d.bahnID}_${segmentNum}`;
    });
  };

  const handleSegmentSelect = (segment: string) => {
    onSegmentChange(segment);
    setShowDropdown(false);
  };

  // 2D Plot erstellen
  const create2DPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    const getTimeArray = (data: any[]) => {
      if (!data.length) return [];

      if (!currentBahnInfo?.startTime || !currentBahnInfo?.endTime) {
        return data.map((_, i) => i);
      }

      const startTime = new Date(currentBahnInfo.startTime).getTime();
      const endTime = new Date(currentBahnInfo.endTime).getTime();
      const duration = endTime - startTime;
      const points = data.length;

      return Array(points)
        .fill(0)
        .map((_, i) => {
          const timeProgress = (i / (points - 1)) * duration;
          return timeProgress / 1000;
        });
    };

    if (metrics.ea.isLoaded && metrics.ea.visible) {
      const filteredData = filterDataBySegment(currentEuclideanDeviation);
      const sortedEA = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedEA);

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Euklidischer Abstand',
        x: timePoints,
        y: sortedEA.map((d) => d.EADistances),
        line: { color: methodColors.EA.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>EA: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.dfd.isLoaded && metrics.dfd.visible) {
      const filteredData = filterDataBySegment(currentDiscreteFrechetDeviation);
      const sortedDFD = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedDFD);

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Diskrete Fréchet-Distanz',
        x: timePoints,
        y: sortedDFD.map((d) => d.DFDDistances),
        line: { color: methodColors.DFD.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>DFD: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.sidtw.isLoaded && metrics.sidtw.visible) {
      const filteredData = filterDataBySegment(currentSIDTWDeviation);
      const sortedSIDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedSIDTW);

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'SIDTW',
        x: timePoints,
        y: sortedSIDTW.map((d) => d.SIDTWDistances),
        line: { color: methodColors.SIDTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>SIDTW: %{y:.2f}mm<extra></extra>',
      });
    }

    if (metrics.dtw.isLoaded && metrics.dtw.visible) {
      const filteredData = filterDataBySegment(currentDTWDeviation);
      const sortedDTW = [...filteredData].sort(
        (a, b) => a.pointsOrder - b.pointsOrder,
      );
      const timePoints = getTimeArray(sortedDTW);

      plots.push({
        type: 'scatter',
        mode: 'lines',
        name: 'DTW',
        x: timePoints,
        y: sortedDTW.map((d) => d.DTWDistances),
        line: { color: methodColors.DTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.2f}s<br>DTW: %{y:.2f}mm<extra></extra>',
      });
    }

    return plots;
  };

  const get2DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? '2D-Abweichungsplot (Gesamtmessung)'
        : `2D-Abweichungsplot (${segmentOptions.find((opt) => opt.value === selectedSegment)?.label})`,
    font: { family: 'Helvetica' },
    xaxis: { title: 'Zeit (s)' },
    yaxis: { title: 'Abweichung (mm)' },
    hovermode: 'x unified',
    height: 600,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
  });

  const anyMetricLoaded = Object.values(metrics).some((m) => m.isLoaded);
  const anyMetricVisible = Object.values(metrics).some(
    (m) => m.isLoaded && m.visible,
  );

  if (!hasDeviationData) {
    return (
      <button disabled className="rounded bg-gray-300 px-4 py-2 text-gray-600">
        Keine Abweichungsdaten verfügbar
      </button>
    );
  }

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

  return (
    <div className="w-full space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-4">
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

        <div className="flex items-center gap-4">
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
            >
              {segmentOptions.find((opt) => opt.value === selectedSegment)
                ?.label || 'Segment auswählen'}
              <ChevronDownIcon className="size-4" />
            </button>

            {showDropdown && (
              <div className="absolute right-0 top-10 z-10 w-48 rounded-md border bg-white shadow-lg">
                {segmentOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSegmentSelect(option.value)}
                    className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {anyMetricLoaded && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          {anyMetricVisible ? (
            <Plot
              data={create2DPlot()}
              layout={get2DLayout()}
              useResizeHandler
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage'],
                responsive: true,
              }}
              style={{ width: '100%', height: '600px' }}
            />
          ) : (
            <div className="flex h-[600px] items-center justify-center text-gray-500">
              Keine Datenquelle ausgewählt
            </div>
          )}
        </div>
      )}
    </div>
  );
};
