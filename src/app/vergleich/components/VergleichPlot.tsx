/* eslint-disable react/button-has-type */
/* eslint-disable jsx-a11y/label-has-associated-control */

'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getBahnEventsById,
  getBahnPositionSollById,
  getSegmentEventsById,
  getSegmentPositionSollById,
} from '@/src/actions/bewegungsdaten.service';
import type { SimilarityResult } from '@/src/actions/vergleich.service';
import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  BahnEvents,
  BahnPositionSoll,
} from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// Farben für verschiedene Bahnen/Segmente
const TRAJECTORY_COLORS = [
  '#1f77b4', // Blau
  '#ff7f0e', // Orange
  '#2ca02c', // Grün
  '#d62728', // Rot
  '#9467bd', // Lila
  '#8c564b', // Braun
  '#e377c2', // Pink
  '#7f7f7f', // Grau
  '#bcbd22', // Olive
  '#17becf', // Cyan
  '#aec7e8', // Hellblau
  '#ffbb78', // Hellorange
];

interface SegmentOption {
  value: string; // z.B. "segment_1"
  label: string; // z.B. "Segment 1"
}

interface VergleichPlotProps {
  results: SimilarityResult[];
  isLoading: boolean;
  originalId: string;
  mode: 'bahnen' | 'segmente';
  className?: string;
}

interface TrajectoryData {
  id: string; // bahnId oder segmentId
  positions: BahnPositionSoll[];
  events: BahnEvents[];
  color: string;
  name: string;
  isOriginal: boolean;
  similarityScore?: number;
}

export const VergleichPlot: React.FC<VergleichPlotProps> = ({
  results,
  isLoading: searchLoading,
  originalId,
  mode,
  className = '',
}) => {
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryData[]>([]);
  const [isLoadingPlot, setIsLoadingPlot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedIds, setLoadedIds] = useState<Set<string>>(new Set());
  const [visibleTrajectories, setVisibleTrajectories] = useState<Set<string>>(
    new Set(),
  );

  // Segment-spezifische States
  const [selectedSegment, setSelectedSegment] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState(false);

  // Hilfsfunktion um jeden 13. Punkt zu nehmen
  const sampleEveryFifthPoint = useCallback(<T,>(data: T[]): T[] => {
    return data.filter((_, index) => index % 1 === 0);
  }, []);

  // Separate Bahnen und Segmente aus den Ergebnissen
  const { bahnResults, segmentResults } = useMemo(() => {
    const bahnen = results.filter(
      (result) => result.bahn_id && !result.segment_id?.includes('_'),
    );
    const segmente = results.filter((result) =>
      result.segment_id?.includes('_'),
    );
    return { bahnResults: bahnen, segmentResults: segmente };
  }, [results]);

  // Segment-Dropdown-Optionen (nur für Segmente-Modus)
  const segmentOptions = useMemo((): SegmentOption[] => {
    if (mode !== 'segmente' || !originalId) return [];

    // Finde alle Segmente der Original-Bahn in den Segment-Ergebnissen
    const originalBahnSegments = segmentResults.filter((result) =>
      result.segment_id?.startsWith(originalId),
    );

    // Extrahiere eindeutige Segment-Nummern
    const segmentNumbers = new Set<number>();
    originalBahnSegments.forEach((result) => {
      if (result.segment_id) {
        const parts = result.segment_id.split('_');
        if (parts.length >= 2) {
          const segmentNum = parseInt(parts[parts.length - 1], 10);
          if (!Number.isNaN(segmentNum)) {
            segmentNumbers.add(segmentNum);
          }
        }
      }
    });

    // Sortiere und erstelle Optionen
    return Array.from(segmentNumbers)
      .sort((a, b) => a - b)
      .map((segNum) => ({
        value: `segment_${segNum}`,
        label: `Segment ${segNum}`,
      }));
  }, [segmentResults, originalId, mode]);

  const groupedSegments = useMemo((): Record<string, string[]> => {
    const groups: Record<string, string[]> = {};
    let currentOriginal: string | null = null;

    segmentResults.forEach((result) => {
      if (result.segment_id?.includes(originalId)) {
        // Neues Original gefunden
        currentOriginal = result.segment_id;
        groups[currentOriginal] = [result.segment_id];
      } else if (currentOriginal && result.segment_id) {
        // Gehört zum aktuellen Original
        groups[currentOriginal].push(result.segment_id);
      }
    });

    return groups;
  }, [segmentResults, originalId]);

  // Setze initial das erste Segment als ausgewählt
  useEffect(() => {
    if (mode === 'segmente' && segmentOptions.length > 0 && !selectedSegment) {
      setSelectedSegment(segmentOptions[0].value);
    }
  }, [segmentOptions, selectedSegment, mode]);

  // Extrahiere relevante IDs basierend auf Modus
  const uniqueIds = useMemo((): string[] => {
    if (mode === 'bahnen') {
      // Bahn-Modus: Extrahiere Bahn-IDs
      const bahnIds = new Set<string>();

      // Original-Bahn hinzufügen
      if (originalId) {
        bahnIds.add(originalId);
      }

      // Ähnliche Bahnen hinzufügen
      bahnResults.forEach((result) => {
        if (result.bahn_id) {
          bahnIds.add(result.bahn_id);
        }
      });

      return Array.from(bahnIds).slice(0, 50); // Max 50 Bahnen
    }
    // Segment-Modus: Filtere für ausgewähltes Segment
    if (!selectedSegment || !originalId) return [];

    const targetSegmentId = `${originalId}_${selectedSegment.replace('segment_', '')}`;

    // Verwende die gruppierten Segmente
    const segmentGroup = groupedSegments[targetSegmentId] || [];
    return segmentGroup.slice(0, 50); // Max 50 Segmente pro Gruppe
  }, [mode, selectedSegment, originalId, groupedSegments, bahnResults]);

  // Setze alle Trajektorien initial als sichtbar
  useEffect(() => {
    setVisibleTrajectories(new Set(trajectoryData.map((t) => t.id)));
  }, [trajectoryData]);

  // Toggle Visibility für eine Trajektorie
  const toggleVisibility = (id: string) => {
    setVisibleTrajectories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  // Segment-Auswahl Handler
  const handleSegmentSelect = (segmentValue: string) => {
    setSelectedSegment(segmentValue);
    setShowDropdown(false);
  };

  // Berechne Bounds aus den geladenen Trajektorien
  const calculateBounds = useCallback(() => {
    if (trajectoryData.length === 0) return null;

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;

    trajectoryData.forEach((trajectory) => {
      // Aus Positionen
      trajectory.positions.forEach((pos) => {
        minX = Math.min(minX, pos.xSoll);
        maxX = Math.max(maxX, pos.xSoll);
        minY = Math.min(minY, pos.ySoll);
        maxY = Math.max(maxY, pos.ySoll);
        minZ = Math.min(minZ, pos.zSoll);
        maxZ = Math.max(maxZ, pos.zSoll);
      });

      // Aus Events
      trajectory.events.forEach((event) => {
        minX = Math.min(minX, event.xReached);
        maxX = Math.max(maxX, event.xReached);
        minY = Math.min(minY, event.yReached);
        maxY = Math.max(maxY, event.yReached);
        minZ = Math.min(minZ, event.zReached);
        maxZ = Math.max(maxZ, event.zReached);
      });
    });

    // 10% Padding hinzufügen
    const paddingX = (maxX - minX) * 0.1;
    const paddingY = (maxY - minY) * 0.1;
    const paddingZ = (maxZ - minZ) * 0.1;

    return {
      x: [minX - paddingX, maxX + paddingX],
      y: [minY - paddingY, maxY + paddingY],
      z: [minZ - paddingZ, maxZ + paddingZ],
    };
  }, [trajectoryData]);

  // Lade Trajektorien-Daten
  const loadTrajectoryData = useCallback(async () => {
    if (uniqueIds.length === 0) {
      setTrajectoryData([]);
      setIsLoadingPlot(false);
      return;
    }

    // Prüfe ob wir diese IDs bereits geladen haben
    const newIds = uniqueIds.filter((id) => !loadedIds.has(id));
    if (newIds.length === 0) {
      return; // Keine neuen IDs zu laden
    }

    setIsLoadingPlot(true);
    setError(null);

    try {
      const trajectories: TrajectoryData[] = [];

      // Parallel laden aller IDs
      const trajectoryPromises = uniqueIds.map(async (id, i) => {
        const isOriginal =
          id === originalId ||
          (mode === 'segmente' &&
            id === `${originalId}_${selectedSegment.replace('segment_', '')}`);

        // Finde zugehöriges Ergebnis für Similarity Score
        const resultForId =
          mode === 'bahnen'
            ? bahnResults.find((r) => r.bahn_id === id)
            : segmentResults.find((r) => r.segment_id === id);

        try {
          // API-Calls basierend auf Modus
          const [positionsResult, eventsResult] =
            mode === 'bahnen'
              ? await Promise.all([
                  getBahnPositionSollById(id),
                  getBahnEventsById(id),
                ])
              : await Promise.all([
                  getSegmentPositionSollById(id),
                  getSegmentEventsById(id),
                ]);

          const sampledPositions = sampleEveryFifthPoint(positionsResult);

          return {
            id,
            positions: sampledPositions,
            events: eventsResult,
            color: isOriginal
              ? '#000000'
              : TRAJECTORY_COLORS[i % TRAJECTORY_COLORS.length],
            name: isOriginal
              ? `${id} (Original)`
              : `${id}${resultForId ? ` (${resultForId.similarity_score?.toFixed(3)})` : ''}`,
            isOriginal,
            similarityScore: resultForId?.similarity_score,
          };
        } catch {
          return null;
        }
      });

      const trajectoryResults = await Promise.all(trajectoryPromises);
      const validTrajectories = trajectoryResults.filter(
        (t) => t !== null,
      ) as TrajectoryData[];

      trajectories.push(...validTrajectories);

      // Sortiere: Original zuerst, dann nach Similarity Score
      trajectories.sort((a, b) => {
        if (a.isOriginal) return -1;
        if (b.isOriginal) return 1;
        return (a.similarityScore || 0) - (b.similarityScore || 0);
      });

      setTrajectoryData(trajectories);
      setLoadedIds(new Set(uniqueIds)); // Markiere als geladen
    } catch (err) {
      setError('Fehler beim Laden der Trajektorien');
    } finally {
      setIsLoadingPlot(false);
    }
  }, [
    uniqueIds,
    loadedIds,
    originalId,
    mode,
    selectedSegment,
    bahnResults,
    segmentResults,
    sampleEveryFifthPoint,
  ]);

  // Effect für Daten laden
  useEffect(() => {
    if (!searchLoading && uniqueIds.length > 0) {
      loadTrajectoryData();
    } else if (uniqueIds.length === 0) {
      setTrajectoryData([]);
      setLoadedIds(new Set());
      setIsLoadingPlot(false);
    }
  }, [uniqueIds, searchLoading, loadTrajectoryData]);

  // Erstelle Plot-Daten für alle Trajektorien
  const createPlotData = useCallback((): Partial<PlotData>[] => {
    const plotData: Partial<PlotData>[] = [];

    trajectoryData.forEach((trajectory) => {
      // Soll-Trajectory (Linie)
      if (trajectory.positions.length > 0) {
        plotData.push({
          type: 'scatter3d',
          mode: 'lines',
          name: `${trajectory.name} (Soll)`,
          x: trajectory.positions.map((p) => p.xSoll),
          y: trajectory.positions.map((p) => p.ySoll),
          z: trajectory.positions.map((p) => p.zSoll),
          line: {
            color: trajectory.color,
            width: trajectory.isOriginal ? 4 : 3, // Original dicker
          },
          hoverlabel: {
            bgcolor: trajectory.color,
          },
          visible: visibleTrajectories.has(trajectory.id),
        });
      }

      // Zielpunkte (Marker)
      if (trajectory.events.length > 0) {
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: `${trajectory.name} (Zielpunkte)`,
          x: trajectory.events.map((e) => e.xReached),
          y: trajectory.events.map((e) => e.yReached),
          z: trajectory.events.map((e) => e.zReached),
          marker: {
            size: 3, // Original größer
            color: trajectory.color,
            symbol: 'diamond',
            opacity: 1.0,
          },
          hoverlabel: {
            bgcolor: trajectory.color,
          },
          visible: visibleTrajectories.has(trajectory.id),
        });
      }
    });

    return plotData;
  }, [trajectoryData, visibleTrajectories]);

  // Dynamische Titel basierend auf Modus
  const getPlotTitle = () => {
    if (mode === 'bahnen') {
      return `3D-Position (${trajectoryData.length} Bahnen)`;
    }
    const selectedSegmentLabel =
      segmentOptions.find((opt) => opt.value === selectedSegment)?.label || '';
    return `3D-Position ${selectedSegmentLabel} (${trajectoryData.length} Segmente)`;
  };

  const bounds = calculateBounds();
  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    title: getPlotTitle(),
    autosize: true,
    scene: {
      camera: {
        up: { x: 0, y: 0, z: 1 },
        center: { x: 0, y: 0, z: -0.1 },
        eye: { x: 1.5, y: 1.2, z: 1.2 },
      },
      aspectmode: 'cube',
      dragmode: 'orbit',
      xaxis: {
        title: 'X [mm]',
        showgrid: true,
        zeroline: true,
        range: bounds?.x,
      },
      yaxis: {
        title: 'Y [mm]',
        showgrid: true,
        zeroline: true,
        range: bounds?.y,
      },
      zaxis: {
        title: 'Z [mm]',
        showgrid: true,
        zeroline: true,
        range: bounds?.z,
      },
    },
    margin: { t: 60, b: 20, l: 20, r: 20 },
    showlegend: false,
  };

  // Loading states - GENAU WIE ORIGINAL
  if (searchLoading || isLoadingPlot) {
    return (
      <div className="m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-4 shadow-sm">
        <div className="flex flex-col items-center space-y-4 py-8">
          <div className="animate-spin">
            <Loader className="size-8" color="#003560" />
          </div>
          <Typography as="p">
            Lade {mode === 'bahnen' ? 'Bahnen' : 'Segmente'}...
          </Typography>
        </div>
      </div>
    );
  }

  // Error state - GENAU WIE ORIGINAL
  if (error) {
    return (
      <div className="m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-4 shadow-sm">
        <div className="py-8 text-center">
          <Typography as="h5" className="mb-2 text-red-600">
            Fehler beim Laden
          </Typography>
          <Typography as="p" className="text-gray-600">
            {error}
          </Typography>
        </div>
      </div>
    );
  }

  // Keine Daten - ANGEPASST FÜR BEIDE MODI
  if (trajectoryData.length === 0) {
    return (
      <div
        className={`m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-4 shadow-sm ${className}`}
      >
        <div className="py-8 text-center">
          <Typography as="h5" className="mb-2">
            {mode === 'segmente' && segmentOptions.length === 0
              ? 'Keine Segmente für Visualisierung gefunden'
              : 'Keine Vergleichsdaten verfügbar'}
          </Typography>
          <Typography as="p" className="text-gray-600">
            {mode === 'bahnen'
              ? 'Führe eine Ähnlichkeitssuche durch, um Bahnen im 3D-Raum zu vergleichen.'
              : 'Warte auf Segment-Ähnlichkeitsergebnisse aus dem Background-Task.'}
          </Typography>
        </div>
      </div>
    );
  }

  const plotData = createPlotData();

  return (
    <div className="m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-2 shadow-sm">
      {/* Segment-Dropdown (nur im Segment-Modus) - NEU */}
      {mode === 'segmente' && segmentOptions.length > 0 && (
        <div className="mb-2 flex items-center justify-between rounded border bg-white p-2">
          <Typography as="h6" className="font-medium text-gray-700">
            Segment-Auswahl:
          </Typography>

          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1 text-sm hover:bg-gray-50"
            >
              {segmentOptions.find((opt) => opt.value === selectedSegment)
                ?.label || 'Segment auswählen'}
              <ChevronDownIcon className="size-4" />
            </button>

            {showDropdown && (
              <div className="absolute right-0 top-10 z-10 w-40 rounded-md border bg-white shadow-lg">
                {segmentOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSegmentSelect(option.value)}
                    className={`block w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                      option.value === selectedSegment
                        ? 'bg-blue-50 text-blue-600'
                        : ''
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Plot - GENAU WIE ORIGINAL */}
      <Plot
        data={plotData}
        layout={layout}
        useResizeHandler
        className="border border-gray-400"
        style={{ width: '100%', height: '100%' }}
        config={{
          displaylogo: false,
          modeBarButtonsToRemove: [
            'toImage',
            'orbitRotation',
            'zoom3d',
            'tableRotation',
            'pan3d',
            'resetCameraDefault3d',
          ],
          responsive: true,
        }}
      />

      {/* Externe Legende - GENAU WIE ORIGINAL */}
      {trajectoryData.length > 0 && (
        <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
          <div className="mb-2 text-sm font-medium text-gray-700">
            Sichtbare {mode === 'bahnen' ? 'Bahnen' : 'Segmente'}:
          </div>
          {trajectoryData.map((trajectory) => (
            <label
              key={trajectory.id}
              className="flex cursor-pointer items-center space-x-2"
            >
              <input
                type="checkbox"
                checked={visibleTrajectories.has(trajectory.id)}
                onChange={() => toggleVisibility(trajectory.id)}
                className="rounded"
              />
              <div
                className="h-2 w-4 rounded"
                style={{ backgroundColor: trajectory.color }}
              />
              <span className="text-sm">{trajectory.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
};
