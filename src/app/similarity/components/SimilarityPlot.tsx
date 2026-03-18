/* eslint-disable react/button-has-type */
/* eslint-disable jsx-a11y/label-has-associated-control */

'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getTrajSetpointsById,
  getTrajPositionCmdById,
  getSegmentSetpointsById,
  getSegmentPositionCmdById,
} from '@/src/actions/motion.service';
import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type {
  TrajPositionCmd, TrajSetpoints,
} from '@/types/motion.types';
import type { SegmentGroup, SimilarityResult } from '@/types/similarity.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const TRAJECTORY_COLORS = [
  '#1f77b4',
  '#ff7f0e',
  '#2ca02c',
  '#d62728',
  '#9467bd',
  '#8c564b',
  '#e377c2',
  '#7f7f7f',
  '#bcbd22',
  '#17becf',
  '#aec7e8',
  '#ffbb78',
];

interface SegmentOption {
  value: string;
  label: string;
}

interface VergleichPlotProps {
  results: SimilarityResult[];
  segmentGroups?: SegmentGroup[];
  isLoading: boolean;
  originalId: string;
  mode: 'trajs' | 'segmente';
  stage2Active?: boolean;
  className?: string;
}

interface TrajectoryData {
  id: string;
  positions: TrajPositionCmd[];
  events: TrajSetpoints[];
  color: string;
  name: string;
  isOriginal: boolean;
  similarityScore?: number;
  dtwDistance?: number;
  rank?: number;
}

export const SimilarityPlot: React.FC<VergleichPlotProps> = ({
  results,
  segmentGroups,
  isLoading: searchLoading,
  originalId,
  mode,
  stage2Active = false,
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

  const [selectedSegment, setSelectedSegment] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState(false);

  const sampleEveryFifthPoint = useCallback(<T,>(data: T[]): T[] => {
    return data.filter((_, index) => index % 13 === 0);
  }, []);

  const normalizeTrajectory = useCallback(
    (trajectory: TrajectoryData): TrajectoryData => {
      if (trajectory.positions.length === 0) return trajectory;

      const offsetX = trajectory.positions[0].xCmd;
      const offsetY = trajectory.positions[0].yCmd;
      const offsetZ = trajectory.positions[0].zCmd;

      return {
        ...trajectory,
        positions: trajectory.positions.map((p) => ({
          ...p,
          xCmd: p.xCmd - offsetX,
          yCmd: p.yCmd - offsetY,
          zCmd: p.zCmd - offsetZ,
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

  const { bahnResults, segmentResults } = useMemo(() => {
    const trajs = results.filter(
      (result) => result.traj_id && !result.seg_id?.includes('_'),
    );

    const segmente: SimilarityResult[] = [];
    if (segmentGroups) {
      segmentGroups.forEach((group) => {
        if (group.target_segment_features) {
          segmente.push({
            seg_id: group.target_segment,
            traj_id: group.target_segment_features.traj_id,
            similarity_score: 0,
            duration: group.target_segment_features.duration,
          });
        }
        group.results.forEach((result) => {
          segmente.push(result);
        });
      });
    }

    return { bahnResults: trajs, segmentResults: segmente };
  }, [results, segmentGroups]);

  const segmentOptions = useMemo((): SegmentOption[] => {
    if (mode !== 'segmente' || !originalId) return [];

    const originalBahnSegments = segmentResults.filter((result) =>
      result.seg_id?.startsWith(originalId),
    );

    const segmentNumbers = new Set<number>();
    originalBahnSegments.forEach((result) => {
      if (result.seg_id) {
        const parts = result.seg_id.split('_');
        if (parts.length >= 2) {
          const segmentNum = parseInt(parts[parts.length - 1], 10);
          if (!Number.isNaN(segmentNum)) {
            segmentNumbers.add(segmentNum);
          }
        }
      }
    });

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
      if (result.seg_id?.includes(originalId)) {
        currentOriginal = result.seg_id;
        groups[currentOriginal] = [result.seg_id];
      } else if (currentOriginal && result.seg_id) {
        groups[currentOriginal].push(result.seg_id);
      }
    });

    return groups;
  }, [segmentResults, originalId]);

  useEffect(() => {
    if (mode === 'segmente' && segmentOptions.length > 0 && !selectedSegment) {
      setSelectedSegment(segmentOptions[0].value);
    }
  }, [segmentOptions, selectedSegment, mode]);

  const uniqueIds = useMemo((): string[] => {
    if (mode === 'trajs') {
      const trajIDs = new Set<string>();
      if (originalId) trajIDs.add(originalId);

      // Sort by rank (stage2: dtw_distance asc, stage1: similarity_score desc)
      const sorted = [...bahnResults].sort((a, b) => {
        if (stage2Active) {
          return (a.dtw_distance ?? Infinity) - (b.dtw_distance ?? Infinity);
        }
        return (b.similarity_score ?? 0) - (a.similarity_score ?? 0);
      });

      sorted.forEach((result) => {
        if (result.traj_id) trajIDs.add(result.traj_id);
      });

      return Array.from(trajIDs).slice(0, 50);
    }

    if (!selectedSegment || !originalId) return [];
    const targetSegmentId = `${originalId}_${selectedSegment.replace('segment_', '')}`;
    const segmentGroup = groupedSegments[targetSegmentId] || [];
    return segmentGroup.slice(0, 50);
  }, [
    mode,
    selectedSegment,
    originalId,
    groupedSegments,
    bahnResults,
    stage2Active,
  ]);

  useEffect(() => {
    setVisibleTrajectories(new Set(trajectoryData.map((t) => t.id)));
  }, [trajectoryData]);

  const toggleVisibility = (id: string) => {
    setVisibleTrajectories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      return newSet;
    });
  };

  const handleSegmentSelect = (segmentValue: string) => {
    setSelectedSegment(segmentValue);
    setShowDropdown(false);
  };

  // Format score label for legend
  const formatScoreLabel = (result: SimilarityResult | undefined): string => {
    if (!result) return 'N/A';
    if (stage2Active && result.dtw_distance !== undefined) {
      return `DTW: ${result.dtw_distance.toFixed(1)}`;
    }
    return `RRF: ${result.similarity_score?.toFixed(4) ?? 'N/A'}`;
  };

  // Parallel loading with Promise.all
  useEffect(() => {
    const loadTrajectories = async () => {
      if (uniqueIds.length === 0) return;

      const newIds = uniqueIds.filter((id) => !loadedIds.has(id));
      if (newIds.length === 0) return;

      setIsLoadingPlot(true);
      setError(null);

      try {
        const isBahn = mode === 'trajs';

        const loadedTrajectories = await Promise.all(
          newIds.map(async (id, index) => {
            const isOriginal = id === originalId || id.startsWith(originalId);

            const [positions, events] = await Promise.all([
              isBahn
                ? getTrajPositionCmdById(id)
                : getSegmentPositionCmdById(id),
              isBahn ? getTrajSetpointsById(id) : getSegmentSetpointsById(id),
            ]);

            const sampledPositions = sampleEveryFifthPoint(positions);

            const result =
              mode === 'trajs'
                ? bahnResults.find((r) => r.traj_id === id)
                : segmentResults.find((r) => r.seg_id === id);

            const scoreLabel = isOriginal
              ? 'Original'
              : formatScoreLabel(result);

            return {
              id,
              positions: sampledPositions,
              events,
              color: isOriginal
                ? '#003560'
                : TRAJECTORY_COLORS[index % TRAJECTORY_COLORS.length],
              name: isOriginal ? `${id} (Original)` : `${id} (${scoreLabel})`,
              isOriginal,
              similarityScore: result?.similarity_score,
              dtwDistance: result?.dtw_distance,
              rank: stage2Active ? result?.rank_stage2 : undefined,
            } satisfies TrajectoryData;
          }),
        );

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
          err instanceof Error ? err.message : 'Unknown error during loading',
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
    stage2Active,
  ]);

  useEffect(() => {
    setTrajectoryData([]);
    setLoadedIds(new Set());
  }, [mode, selectedSegment]);

  const createPlotData = useCallback((): Partial<PlotData>[] => {
    const plotData: Partial<PlotData>[] = [];

    // Sort trajectories for plot: original first, then by rank/score
    const sorted = [...trajectoryData].sort((a, b) => {
      if (a.isOriginal) return -1;
      if (b.isOriginal) return 1;
      if (stage2Active) {
        return (a.dtwDistance ?? Infinity) - (b.dtwDistance ?? Infinity);
      }
      return (b.similarityScore ?? 0) - (a.similarityScore ?? 0);
    });

    const dataToPlot = normalizeStartPoint
      ? sorted.map((t) => normalizeTrajectory(t))
      : sorted;

    dataToPlot.forEach((trajectory) => {
      if (trajectory.positions.length > 0) {
        plotData.push({
          type: 'scatter3d',
          mode: 'lines',
          name: trajectory.name,
          x: trajectory.positions.map((p) => p.xCmd),
          y: trajectory.positions.map((p) => p.yCmd),
          z: trajectory.positions.map((p) => p.zCmd),
          line: {
            color: trajectory.color,
            width: trajectory.isOriginal ? 4 : 3,
          },
          hoverlabel: { bgcolor: trajectory.color },
          visible: visibleTrajectories.has(trajectory.id),
        });
      }

      if (trajectory.events.length > 0) {
        plotData.push({
          type: 'scatter3d',
          mode: 'markers',
          name: `${trajectory.name} (Endpoints)`,
          x: trajectory.events.map((e) => e.xReached),
          y: trajectory.events.map((e) => e.yReached),
          z: trajectory.events.map((e) => e.zReached),
          marker: {
            size: 3,
            color: trajectory.color,
            symbol: 'diamond',
            opacity: 1.0,
          },
          hoverlabel: { bgcolor: trajectory.color },
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
    stage2Active,
  ]);

  const getPlotTitle = () => {
    if (mode === 'trajs') {
      return `3D-Position (${trajectoryData.length} Trajectories)`;
    }
    const selectedSegmentLabel =
      segmentOptions.find((opt) => opt.value === selectedSegment)?.label || '';
    return `3D-Position ${selectedSegmentLabel} (${trajectoryData.length} Segments)`;
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
      xaxis: { title: 'X [mm]', showgrid: true, zeroline: true },
      yaxis: { title: 'Y [mm]', showgrid: true, zeroline: true },
      zaxis: { title: 'Z [mm]', showgrid: true, zeroline: true },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: false,
    uirevision: 'true',
  };

  if (searchLoading || isLoadingPlot) {
    return (
      <div className="flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2">
        <div className="flex flex-col items-center space-y-4 py-8">
          <div className="animate-spin">
            <Loader className="size-8" color="#003560" />
          </div>
          <Typography as="p">
            Loading {mode === 'trajs' ? 'trajectories' : 'segments'}...
          </Typography>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2">
        <div className="py-8 text-center">
          <Typography as="h5" className="mb-2 text-red-600">
            Error while loading
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
        className={`flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2 ${className}`}
      >
        <div className="py-8 text-center">
          <Typography as="h5" className="mb-2">
            {mode === 'segmente' && segmentOptions.length === 0
              ? 'No segments found for visalisation'
              : 'No comparison data available'}
          </Typography>
          <Typography as="p" className="text-gray-600">
            {mode === 'trajs'
              ? 'Conduct a similarity search to compare trajectories in 3D-space.'
              : 'Waiting for results of segment similarity search.'}
          </Typography>
        </div>
      </div>
    );
  }

  const plotData = createPlotData();

  // Sort legend same as plot
  const sortedLegend = [...trajectoryData].sort((a, b) => {
    if (a.isOriginal) return -1;
    if (b.isOriginal) return 1;
    if (stage2Active) {
      return (a.dtwDistance ?? Infinity) - (b.dtwDistance ?? Infinity);
    }
    return (b.similarityScore ?? 0) - (a.similarityScore ?? 0);
  });

  return (
    <div className="flex w-full flex-row justify-start rounded-lg border border-gray-400 bg-gray-50 p-2">
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
                  ?.label || 'Choose Segment'}
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

        <div className="mt-4 flex flex-col justify-between rounded bg-gray-50">
          <label className="flex cursor-pointer items-center space-x-2">
            <input
              type="checkbox"
              checked={normalizeStartPoint}
              onChange={(e) => setNormalizeStartPoint(e.target.checked)}
              className="rounded"
            />
            <div className="text-sm text-gray-700">
              Normalize starting point
            </div>
          </label>
        </div>

        {trajectoryData.length > 0 && (
          <div className="mt-4 space-y-2 overflow-y-auto">
            <div className="mb-2 text-sm font-medium text-gray-700">
              visible {mode === 'trajs' ? 'trajectories' : 'sements'}:
            </div>
            {sortedLegend.map((trajectory) => (
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