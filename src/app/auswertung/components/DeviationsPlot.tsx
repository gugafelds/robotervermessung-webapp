/* eslint-disable react/button-has-type,no-console */

'use client';

import { ChevronDownIcon, ViewColumnsIcon } from '@heroicons/react/24/outline';
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
  EA: {
    soll: '#003560',
    ist: '#0066b8',
    connection: 'rgba(0, 53, 96, 0.7)',
    line: '#003560',
  },
  DFD: {
    soll: '#e63946',
    ist: '#ff6b6b',
    connection: 'rgba(230, 57, 70, 0.7)',
    line: '#e63946',
  },
  DTW: {
    soll: '#774936',
    ist: '#a47551',
    connection: 'rgba(119, 73, 54, 0.7)',
    line: '#774936',
  },
  SIDTW: {
    soll: '#2a9d8f',
    ist: '#54ccc0',
    connection: 'rgba(42, 157, 143, 0.7)',
    line: '#2a9d8f',
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

interface DeviationsPlotProps {
  hasDeviationData: boolean;
  bahnId: string;
}

export const DeviationsPlot: React.FC<DeviationsPlotProps> = ({
  hasDeviationData,
  bahnId,
}) => {
  const [view, setView] = useState<'2d' | '3d'>('2d');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState<string>('total');
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
  }, [bahnId, loadBahnInfo, loadAuswertungInfo]); // Fixed: Added all required dependencies

  const loadMetricData = useCallback(
    async (metricType: 'ea' | 'dfd' | 'sidtw' | 'dtw') => {
      if (!bahnId) return;

      // Wenn bereits geladen, dann Toggle-Verhalten
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

  // 2D Plot Funktionen
  const create2DPlot = (): Partial<PlotData>[] => {
    const plots: Partial<PlotData>[] = [];

    // Helper function to get time array for a dataset
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
          return timeProgress / 1000; // Convert to seconds
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
        hovertemplate: 'Zeit: %{x:.1f}s<br>EA: %{y:.1f}mm<extra></extra>',
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
        hovertemplate: 'Zeit: %{x:.1f}s<br>DFD: %{y:.1f}mm<extra></extra>',
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
        hovertemplate: 'Zeit: %{x:.1f}s<br>SIDTW: %{y:.1f}mm<extra></extra>',
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
        name: 'SIDTW',
        x: timePoints,
        y: sortedDTW.map((d) => d.DTWDistances),
        line: { color: methodColors.DTW.line, width: 2 },
        hovertemplate: 'Zeit: %{x:.1f}s<br>DTW: %{y:.1f}mm<extra></extra>',
      });
    }

    return plots;
  };

  // 3D Plot Funktionen
  const addMethodTraces = (
    data: any[],
    methodName: 'EA' | 'DFD' | 'SIDTW' | 'DTW',
    colors: typeof methodColors.EA,
  ): Partial<PlotData>[] => {
    // We'll collect all traces in this array
    const traces: Partial<PlotData>[] = [];

    // Filter and sort data
    const filteredData = filterDataBySegment(data);
    const sortedData = [...filteredData].sort(
      (a, b) => a.pointsOrder - b.pointsOrder,
    );

    // Get the correct field names based on method
    const prefix = methodName; // EA, DFD, or SIDTW
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
      line: {
        color: colors.soll,
        width: 3,
      },
      hovertemplate:
        'X: %{x:.1f}mm<br>' +
        'Y: %{y:.1f}mm<br>' +
        'Z: %{z:.1f}mm<br>' +
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
      line: {
        color: colors.ist,
        width: 4,
      },
      hovertemplate:
        'X: %{x:.1f}mm<br>' +
        'Y: %{y:.1f}mm<br>' +
        'Z: %{z:.1f}mm<br>' +
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
      hovertemplate: `${methodName} Abweichung: %{text:.1f}mm<br><extra></extra>`,
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
  const get2DLayout = (): Partial<Layout> => ({
    title:
      selectedSegment === 'total'
        ? '2D-Abweichungsplot (Gesamtmessung)'
        : `2D-Abweichungsplot (${segmentOptions.find((opt) => opt.value === selectedSegment)?.label})`,
    font: { family: 'Helvetica' },
    xaxis: {
      title: 'Zeit (s)',
    },
    yaxis: {
      title: 'Abweichung (mm)',
    },
    hovermode: 'x unified',
    height: 500,
    margin: { t: 40, b: 40, l: 60, r: 20 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.2,
    },
  });
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
    <div className="w-full space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-4">
          {/* EA Control */}
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

          {/* SIDTW Control */}
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

          {/* DTW Control */}
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

          {/* DFD Control */}
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
          {/* Segment Selection Dropdown */}
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
                    onClick={() => {
                      setSelectedSegment(option.value);
                      setShowDropdown(false);
                    }}
                    className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* View Toggle Button */}
          {anyMetricLoaded && (
            <button
              onClick={() => setView(view === '2d' ? '3d' : '2d')}
              className="inline-flex items-center gap-2 rounded bg-gray-100 px-3 py-1 text-sm text-gray-700 hover:bg-gray-200"
            >
              <ViewColumnsIcon className="size-4" />
              <span>{view === '2d' ? '3D-Ansicht' : '2D-Ansicht'}</span>
            </button>
          )}
        </div>
      </div>

      {anyMetricLoaded && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          {anyMetricVisible ? (
            <Plot
              data={view === '2d' ? create2DPlot() : create3DPlot()}
              layout={view === '2d' ? get2DLayout() : get3DLayout()}
              useResizeHandler
              config={{
                displaylogo: false,
                modeBarButtonsToRemove: ['toImage'],
                responsive: true,
              }}
              style={{
                width: '100%',
                height: view === '2d' ? '500px' : '600px',
              }}
            />
          ) : (
            <div className="flex h-[500px] items-center justify-center text-gray-500">
              Keine Datenquelle ausgewählt
            </div>
          )}
        </div>
      )}
    </div>
  );
};
