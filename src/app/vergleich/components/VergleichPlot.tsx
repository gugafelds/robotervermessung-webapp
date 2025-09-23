/* eslint-disable jsx-a11y/label-has-associated-control */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getBahnEventsById,
  getBahnPositionSollById,
} from '@/src/actions/bewegungsdaten.service';
import type { SimilarityResult } from '@/src/actions/vergleich.service';
import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  BahnEvents,
  BahnPositionSoll,
} from '@/types/bewegungsdaten.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// Farben für verschiedene Bahnen
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

interface VergleichPlotProps {
  results: SimilarityResult[];
  isLoading: boolean;
  originalId: string;
  className?: string;
}

interface BahnTrajectoryData {
  bahnId: string;
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
  className = '',
}) => {
  const [trajectoryData, setTrajectoryData] = useState<BahnTrajectoryData[]>(
    [],
  );
  const [isLoadingPlot, setIsLoadingPlot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedBahnIds, setLoadedBahnIds] = useState<Set<string>>(new Set());
  const [visibleTrajectories, setVisibleTrajectories] = useState<Set<string>>(
    new Set(),
  );

  // Hilfsfunktion um jeden 5. Punkt zu nehmen
  const sampleEveryFifthPoint = useCallback(<T,>(data: T[]): T[] => {
    return data.filter((_, index) => index % 13 === 0);
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

  // Extrahiere eindeutige Bahn-IDs aus Bahn-Ergebnissen
  const uniqueBahnIds = useMemo((): string[] => {
    const bahnIds = new Set<string>();

    // Original-Bahn hinzufügen
    if (originalId) {
      bahnIds.add(originalId);
    }

    // Nur Bahnen hinzufügen
    bahnResults.forEach((result) => {
      if (result.bahn_id) {
        bahnIds.add(result.bahn_id);
      }
    });

    return Array.from(bahnIds).slice(0, 50); // Max 50 Bahnen
  }, [bahnResults, originalId]);

  // Setze alle Bahnen initial als sichtbar
  useEffect(() => {
    setVisibleTrajectories(new Set(trajectoryData.map((t) => t.bahnId)));
  }, [trajectoryData]);

  // Toggle Visibility für eine Bahn
  const toggleVisibility = (bahnId: string) => {
    setVisibleTrajectories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(bahnId)) {
        newSet.delete(bahnId);
      } else {
        newSet.add(bahnId);
      }
      return newSet;
    });
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

  // Lade Daten für alle ähnlichen Bahnen
  const loadTrajectoryData = useCallback(async () => {
    if (uniqueBahnIds.length === 0) {
      setTrajectoryData([]);
      setIsLoadingPlot(false);
      return;
    }

    // Prüfe ob wir diese Bahnen bereits geladen haben
    const newBahnIds = uniqueBahnIds.filter((id) => !loadedBahnIds.has(id));
    if (newBahnIds.length === 0) {
      return; // Keine neuen Bahnen zu laden
    }

    setIsLoadingPlot(true);
    setError(null);

    try {
      const trajectories: BahnTrajectoryData[] = [];

      // Parallel laden aller Bahnen
      const trajectoryPromises = uniqueBahnIds.map(async (bahnId, i) => {
        const isOriginal = bahnId === originalId;
        const resultForBahn = bahnResults.find((r) => r.bahn_id === bahnId);

        try {
          const [positionsResult, eventsResult] = await Promise.all([
            getBahnPositionSollById(bahnId),
            getBahnEventsById(bahnId),
          ]);

          const sampledPositions = sampleEveryFifthPoint(positionsResult);

          return {
            bahnId,
            positions: sampledPositions,
            events: eventsResult,
            color: isOriginal
              ? '#000000'
              : TRAJECTORY_COLORS[i % TRAJECTORY_COLORS.length],
            name: isOriginal
              ? `${bahnId} (Original)`
              : `${bahnId}${resultForBahn ? ` (${resultForBahn.similarity_score.toFixed(3)})` : ''}`,
            isOriginal,
            similarityScore: resultForBahn?.similarity_score,
          };
        } catch {
          return null;
        }
      });

      const trajectoryResults = await Promise.all(trajectoryPromises);
      const validTrajectories = trajectoryResults.filter(
        (t) => t !== null,
      ) as BahnTrajectoryData[];

      trajectories.push(...validTrajectories);

      // Sortiere: Original zuerst, dann nach Similarity Score
      trajectories.sort((a, b) => {
        if (a.isOriginal) return -1;
        if (b.isOriginal) return 1;
        return (a.similarityScore || 0) - (b.similarityScore || 0);
      });

      setTrajectoryData(trajectories);
      setLoadedBahnIds(new Set(uniqueBahnIds)); // Markiere als geladen
    } catch (err) {
      setError('Fehler beim Laden der Trajektorien');
    } finally {
      setIsLoadingPlot(false);
    }
  }, [
    uniqueBahnIds,
    loadedBahnIds,
    originalId,
    bahnResults,
    sampleEveryFifthPoint,
  ]);

  // Effect für Bahn-Ergebnisse - lädt nur wenn sich uniqueBahnIds ändert
  useEffect(() => {
    if (!searchLoading && uniqueBahnIds.length > 0) {
      loadTrajectoryData();
    } else if (uniqueBahnIds.length === 0) {
      setTrajectoryData([]);
      setLoadedBahnIds(new Set());
      setIsLoadingPlot(false);
    }
  }, [uniqueBahnIds, searchLoading, loadTrajectoryData]);

  // Separater Effect für Segment-Ergebnisse - tut derzeit nichts, nur für Logging
  useEffect(() => {
    if (segmentResults.length > 0) {
      /* empty */
    }
  }, [segmentResults]);

  // Erstelle Plot-Daten für alle Bahnen
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
          visible: visibleTrajectories.has(trajectory.bahnId),
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
          visible: visibleTrajectories.has(trajectory.bahnId),
        });
      }
    });

    return plotData;
  }, [trajectoryData, visibleTrajectories]);

  const bounds = calculateBounds();
  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    title: `3D-Position (${trajectoryData.length} Bahnen)`,
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

  // Loading states
  if (searchLoading || isLoadingPlot) {
    return (
      <div className="m-2 h-fit w-[520.467px] rounded-lg border border-gray-400 bg-gray-50 p-4 shadow-sm">
        <div className="flex flex-col items-center space-y-4 py-8">
          <div className="animate-spin">
            <Loader className="size-8" color="#003560" />
          </div>
          <Typography as="p">Lade Bahnen...</Typography>
        </div>
      </div>
    );
  }

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

  if (trajectoryData.length === 0) {
    return (
      <div
        className={`m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-4 shadow-sm ${className}`}
      >
        <div className="py-8 text-center">
          <Typography as="h5" className="mb-2">
            Keine Vergleichsdaten verfügbar
          </Typography>
          <Typography as="p" className="text-gray-600">
            Führe eine Ähnlichkeitssuche durch, um Bahnen im 3D-Raum zu
            vergleichen.
          </Typography>
        </div>
      </div>
    );
  }

  const plotData = createPlotData();

  return (
    <div className="m-2 w-fit rounded-lg border border-gray-400 bg-gray-50 p-2 shadow-sm">
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

      {/* Externe Legende */}
      {trajectoryData.length > 0 && (
        <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
          <div className="mb-2 text-sm font-medium text-gray-700">
            Sichtbare Bahnen:
          </div>
          {trajectoryData.map((trajectory) => (
            <label
              key={trajectory.bahnId}
              className="flex cursor-pointer items-center space-x-2"
            >
              <input
                type="checkbox"
                checked={visibleTrajectories.has(trajectory.bahnId)}
                onChange={() => toggleVisibility(trajectory.bahnId)}
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
