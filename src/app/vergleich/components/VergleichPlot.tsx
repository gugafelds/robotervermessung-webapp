/* eslint-disable no-await-in-loop */
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
import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  BahnEvents,
  BahnPositionSoll,
} from '@/types/bewegungsdaten.types';
import type { SegmentGroup, SimilarityResult } from '@/types/similarity.types';

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
  segmentGroups?: SegmentGroup[]; // ✅ NEU: Hierarchische Segment-Struktur
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
  segmentGroups,
  isLoading: searchLoading,
  originalId,
  mode,
  className = '',
}) => {
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryData[]>([]);
  const [isLoadingPlot, setIsLoadingPlot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedIds, setLoadedIds] = useState<Set<string>>(new Set());
  const [normalizeStartPoint, setNormalizeStartPoint] = useState(true);
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

  const normalizeTrajectory = useCallback(
    (trajectory: TrajectoryData): TrajectoryData => {
      if (trajectory.positions.length === 0) return trajectory;

      const offsetX = trajectory.positions[0].xSoll;
      const offsetY = trajectory.positions[0].ySoll;
      const offsetZ = trajectory.positions[0].zSoll;

      return {
        ...trajectory,
        positions: trajectory.positions.map((p) => ({
          ...p,
          xSoll: p.xSoll - offsetX,
          ySoll: p.ySoll - offsetY,
          zSoll: p.zSoll - offsetZ,
        })),
        events: trajectory.events.map((e) => ({
          ...e,
          xReached: e.xReached - offsetX,
          yReached: e.yReached - offsetY,
          zReached: e.zReached - offsetZ,
        })),
      };
    },
    [],
  );

  // ✅ NEU: Flatten hierarchische Segment-Struktur
  const { bahnResults, segmentResults } = useMemo(() => {
    const bahnen = results.filter(
      (result) => result.bahn_id && !result.segment_id?.includes('_'),
    );

    // Flatten hierarchische Segment-Struktur
    const segmente: SimilarityResult[] = [];
    if (segmentGroups) {
      segmentGroups.forEach((group) => {
        // Original Segment
        if (group.target_segment_features) {
          segmente.push({
            segment_id: group.target_segment,
            bahn_id: group.target_segment_features.bahn_id,
            similarity_score: 0,
            duration: group.target_segment_features.duration,
          });
        }

        // Ähnliche Segmente
        group.results.forEach((result) => {
          segmente.push(result);
        });
      });
    }

    return { bahnResults: bahnen, segmentResults: segmente };
  }, [results, segmentGroups]);

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

  // Lade Trajektorien
  useEffect(() => {
    const loadTrajectories = async () => {
      if (uniqueIds.length === 0) return;

      const newIds = uniqueIds.filter((id) => !loadedIds.has(id));
      if (newIds.length === 0) return;

      setIsLoadingPlot(true);
      setError(null);

      try {
        const loadedTrajectories: TrajectoryData[] = [];

        for (const [index, id] of newIds.entries()) {
          const isBahn = mode === 'bahnen';
          const isOriginal = id === originalId || id.startsWith(originalId);

          let positions: BahnPositionSoll[] = [];
          let events: BahnEvents[] = [];

          if (isBahn) {
            positions = await getBahnPositionSollById(id);
            events = await getBahnEventsById(id);
          } else {
            positions = await getSegmentPositionSollById(id);
            events = await getSegmentEventsById(id);
          }

          const sampledPositions = sampleEveryFifthPoint(positions);

          // Finde Similarity Score
          const result =
            mode === 'bahnen'
              ? bahnResults.find((r) => r.bahn_id === id)
              : segmentResults.find((r) => r.segment_id === id);

          loadedTrajectories.push({
            id,
            positions: sampledPositions,
            events,
            color: isOriginal
              ? '#003560'
              : TRAJECTORY_COLORS[index % TRAJECTORY_COLORS.length],
            name: isOriginal
              ? `${id} (Original)`
              : `${id} (${result?.similarity_score?.toFixed(3) || 'N/A'})`,
            isOriginal,
            similarityScore: result?.similarity_score,
          });
        }

        setTrajectoryData((prev) => {
          const existingIds = new Set(prev.map((t) => t.id));
          const newTrajectories = loadedTrajectories.filter(
            (t) => !existingIds.has(t.id),
          );
          return [...prev, ...newTrajectories];
        });

        setLoadedIds((prev) => new Set([...prev, ...newIds]));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Unbekannter Fehler beim Laden',
        );
      } finally {
        setIsLoadingPlot(false);
      }
    };

    loadTrajectories();
  }, [
    uniqueIds,
    loadedIds,
    mode,
    originalId,
    sampleEveryFifthPoint,
    bahnResults,
    segmentResults,
  ]);

  // Reset bei Modus- oder Segment-Wechsel
  useEffect(() => {
    setTrajectoryData([]);
    setLoadedIds(new Set());
  }, [mode, selectedSegment]);

  // Plot Data erstellen
  const createPlotData = useCallback((): Partial<PlotData>[] => {
    const plotData: Partial<PlotData>[] = [];

    const dataToPlot = normalizeStartPoint
      ? trajectoryData.map((t) => normalizeTrajectory(t))
      : trajectoryData;

    dataToPlot.forEach((trajectory) => {
      // Trajektorie (Linie)
      if (trajectory.positions.length > 0) {
        plotData.push({
          type: 'scatter3d',
          mode: 'lines',
          name: trajectory.name,
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
  }, [
    normalizeStartPoint,
    normalizeTrajectory,
    trajectoryData,
    visibleTrajectories,
  ]);

  // Dynamische Titel basierend auf Modus
  const getPlotTitle = () => {
    if (mode === 'bahnen') {
      return `3D-Position (${trajectoryData.length} Bahnen)`;
    }
    const selectedSegmentLabel =
      segmentOptions.find((opt) => opt.value === selectedSegment)?.label || '';
    return `3D-Position ${selectedSegmentLabel} (${trajectoryData.length} Segmente)`;
  };

  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    title: getPlotTitle(),
    height: 600,
    width: 600,
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
      },
      yaxis: {
        title: 'Y [mm]',
        showgrid: true,
        zeroline: true,
      },
      zaxis: {
        title: 'Z [mm]',
        showgrid: true,
        zeroline: true,
      },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: false,
    uirevision: 'true',
  };

  // Loading states - GENAU WIE ORIGINAL
  if (searchLoading || isLoadingPlot) {
    return (
      <div className="flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2">
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
      <div className="flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2 ">
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
        className={`flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2  ${className}`}
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
              : 'Warte auf Segment-Ähnlichkeitsergebnisse.'}
          </Typography>
        </div>
      </div>
    );
  }

  const plotData = createPlotData();

  return (
    <div className="flex w-full flex-row justify-start rounded-lg border border-gray-400 bg-gray-50 p-2 ">
      {/* Plot - GENAU WIE ORIGINAL */}
      <Plot
        data={plotData}
        layout={layout}
        useResizeHandler
        className="border border-gray-200"
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

      <div className="m-4 flex flex-col">
        {mode === 'segmente' && segmentOptions.length > 0 && (
          <div className="flex justify-between rounded">
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="inline-flex items-center rounded-md border border-gray-300 bg-white p-2 text-sm hover:bg-gray-50"
              >
                {segmentOptions.find((opt) => opt.value === selectedSegment)
                  ?.label || 'Segment auswählen'}
                <ChevronDownIcon className="size-4" />
              </button>

              {showDropdown && (
                <div className="absolute right-0 w-40 rounded-md border bg-white shadow-lg">
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
        {/* Normalisierungs-Toggle */}
        <div className="mt-4 flex flex-col justify-between rounded bg-gray-50">
          <label className="flex cursor-pointer items-center space-x-2">
            <input
              type="checkbox"
              checked={normalizeStartPoint}
              onChange={(e) => setNormalizeStartPoint(e.target.checked)}
              className="rounded"
            />
            <div className="text-sm text-gray-700">
              Startpunkt normalisieren
            </div>
          </label>
        </div>

        {/* Externe Legende - GENAU WIE ORIGINAL */}
        {trajectoryData.length > 0 && (
          <div className="mt-4 space-y-2 overflow-y-auto">
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
    </div>
  );
};
