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

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const methodColors = {
  EA: {
    soll: '#003560',
    ist: '#0066b8',
    connection: 'rgba(0, 53, 96, 0.7)',
  },
  DFD: {
    soll: '#e63946',
    ist: '#ff6b6b',
    connection: 'rgba(230, 57, 70, 0.7)',
  },
  DTW: {
    soll: '#774936',
    ist: '#a47551',
    connection: 'rgba(119, 73, 54, 0.7)',
  },
  SIDTW: {
    soll: '#2a9d8f',
    ist: '#54ccc0',
    connection: 'rgba(42, 157, 143, 0.7)',
  },
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

interface PosDeviationPlot3DProps {
  hasDeviationData: boolean;
  bahnId: string;
  selectedSegment: string;
  onSegmentChange: (segment: string) => void;
}

export const PosDeviationPlot3D: React.FC<PosDeviationPlot3DProps> = ({
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
  const [currentAuswertungInfo, setCurrentAuswertungInfo] = useState<any>({
    info_euclidean: [],
    info_dfd: [],
    info_sidtw: [],
    info_dtw: [],
  });

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
      loadAuswertungInfo();
    }
  }, [bahnId, loadAuswertungInfo]);

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

  // 3D Plot Funktionen
  const addMethodTraces = (
    data: any[],
    methodName: 'EA' | 'DFD' | 'SIDTW' | 'DTW',
    colors: typeof methodColors.EA,
  ): Partial<PlotData>[] => {
    const traces: Partial<PlotData>[] = [];

    const filteredData = filterDataBySegment(data);
    const sortedData = [...filteredData].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );

    const prefix = methodName;
    const sollFields = {
      x: `${prefix}SollX`,
      y: `${prefix}SollY`,
      z: `${prefix}SollZ`,
    };
    const istFields = {
      x: `${prefix}IstX`,
      y: `${prefix}IstY`,
      z: `${prefix}IstZ`,
    };

    // Add Soll trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Soll`,
      x: sortedData.map((d) => d[sollFields.x]),
      y: sortedData.map((d) => d[sollFields.y]),
      z: sortedData.map((d) => d[sollFields.z]),
      line: { color: colors.soll, width: 3 },
      hovertemplate:
        'X: %{x:.2f}mm<br>' +
        'Y: %{y:.2f}mm<br>' +
        'Z: %{z:.2f}mm<br>' +
        '<extra></extra>',
    });

    // Add Ist trajectory
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Ist`,
      x: sortedData.map((d) => d[istFields.x]),
      y: sortedData.map((d) => d[istFields.y]),
      z: sortedData.map((d) => d[istFields.z]),
      line: { color: colors.ist, width: 4 },
      hovertemplate:
        'X: %{x:.2f}mm<br>' +
        'Y: %{y:.2f}mm<br>' +
        'Z: %{z:.2f}mm<br>' +
        '<extra></extra>',
    });

    // Add connection lines for all points using flatMap
    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      name: `${methodName} Abweichungen`,
      showlegend: true,
      x: sortedData.flatMap((point) => [
        point[sollFields.x],
        point[istFields.x],
        null,
      ]),
      y: sortedData.flatMap((point) => [
        point[sollFields.y],
        point[istFields.y],
        null,
      ]),
      z: sortedData.flatMap((point) => [
        point[sollFields.z],
        point[istFields.z],
        null,
      ]),
      line: {
        color: colors.connection,
        width: 2,
        dash: 'solid',
      },
      hovertemplate: `${methodName} Abweichung: %{text:.2f}mm<br><extra></extra>`,
      text: sortedData.flatMap((point) => [
        point[`${methodName}Distances`],
        point[`${methodName}Distances`],
        null,
      ]),
    });

    return traces;
  };

  const create3DPlot = (): Partial<PlotData>[] => {
    let plotData: Partial<PlotData>[] = [];

    if (
      metrics.ea.isLoaded &&
      metrics.ea.visible &&
      currentEuclideanDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentEuclideanDeviation, 'EA', methodColors.EA),
      );
    }
    if (
      metrics.dfd.isLoaded &&
      metrics.dfd.visible &&
      currentDiscreteFrechetDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(
          currentDiscreteFrechetDeviation,
          'DFD',
          methodColors.DFD,
        ),
      );
    }
    if (
      metrics.sidtw.isLoaded &&
      metrics.sidtw.visible &&
      currentSIDTWDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentSIDTWDeviation, 'SIDTW', methodColors.SIDTW),
      );
    }
    if (
      metrics.dtw.isLoaded &&
      metrics.dtw.visible &&
      currentDTWDeviation?.length
    ) {
      plotData = plotData.concat(
        addMethodTraces(currentDTWDeviation, 'DTW', methodColors.DTW),
      );
    }

    return plotData;
  };

  const get3DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? '3D-Abweichungsplot (Gesamtmessung)'
        : `3D-Abweichungsplot (${segmentOptions.find((opt) => opt.value === selectedSegment)?.label})`,
    autosize: true,
    height: 600,
    scene: {
      camera: {
        up: { x: 0, y: 0, z: 1 },
        center: { x: 0, y: 0, z: -0.1 },
        eye: { x: 1.5, y: 1.5, z: 1 },
      },
      aspectmode: 'cube',
      dragmode: 'orbit',
      xaxis: { title: 'X (mm)', showgrid: true, zeroline: true },
      yaxis: { title: 'Y (mm)', showgrid: true, zeroline: true },
      zaxis: { title: 'Z (mm)', showgrid: true, zeroline: true },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.15,
      x: 0.5,
      xanchor: 'center',
      bgcolor: 'rgba(255,255,255,0.8)',
    },
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
              data={create3DPlot()}
              layout={get3DLayout()}
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
