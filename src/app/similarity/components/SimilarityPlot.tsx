/* eslint-disable react/button-has-type */
/* eslint-disable jsx-a11y/label-has-associated-control */

'use client';

import { Loader } from 'lucide-react';
import dynamic from 'next/dynamic';
import type { Layout, PlotData } from 'plotly.js';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getSegmentPositionCmdById,
  getSegmentSetpointsById,
  getTrajPositionCmdById,
  getTrajSetpointsById,
} from '@/src/actions/motion.service';
import { Typography } from '@/src/components/Typography';
import { plotLayoutConfig } from '@/src/lib/plot-config';
import type { TrajPositionCmd, TrajSetpoints } from '@/types/motion.types';
import type { SegmentGroup, SimilarityResult } from '@/types/similarity.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface VergleichPlotProps {
  results: SimilarityResult[];
  segmentGroups?: SegmentGroup[];
  isLoading: boolean;
  originalId: string;
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

type TabKey = string;
type TabDataMap = Record<TabKey, TrajectoryData[]>;
type LoadedIdsMap = Record<TabKey, Set<string>>;

export const SimilarityPlot: React.FC<VergleichPlotProps> = ({
  results,
  segmentGroups = [],
  isLoading: searchLoading,
  originalId,
  stage2Active = false,
  className = '',
}) => {
  const INITIAL_LIMIT = 5;
  const [showAll, setShowAll] = useState<Record<TabKey, boolean>>({});
  const [activeTab, setActiveTab] = useState<TabKey>('trajs');
  const [tabData, setTabData] = useState<TabDataMap>({});
  const [loadedIds, setLoadedIds] = useState<LoadedIdsMap>({});
  const [isLoadingPlot, setIsLoadingPlot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [normalizeStartPoint, setNormalizeStartPoint] = useState(true);
  const [visibleTrajectories, setVisibleTrajectories] = useState<Set<string>>(
    new Set(),
  );

  const tabs = useMemo(() => {
    const t: { key: TabKey; label: string }[] = [
      { key: 'trajs', label: 'Trajectory' },
    ];
    segmentGroups.forEach((group) => {
      const segNum = group.target_segment.split('_').pop();
      t.push({ key: `segment_${segNum}`, label: `Segment ${segNum}` });
    });
    return t;
  }, [segmentGroups]);

  const sampleEveryFifthPoint = useCallback(<T,>(data: T[]): T[] => {
    return data.filter((_, index) => index % 23 === 0);
  }, []);

  const getTrajectoryColor = (rank: number, totalCount: number): string => {
    const t = totalCount <= 1 ? 0 : rank / (totalCount - 1);
    const tSteep = t ** 2;
    const r = Math.round(255 * (1 - tSteep));
    return `rgb(${r}, 0, 0)`;
  };

  const normalizeTrajectory = useCallback(
    (
      trajectory: TrajectoryData,
      queryTrajectory?: TrajectoryData,
    ): TrajectoryData => {
      if (trajectory.positions.length === 0) return trajectory;

      const centroid = (positions: TrajPositionCmd[]) => ({
        x: positions.reduce((s, p) => s + p.xCmd, 0) / positions.length,
        y: positions.reduce((s, p) => s + p.yCmd, 0) / positions.length,
        z: positions.reduce((s, p) => s + p.zCmd, 0) / positions.length,
      });

      if (!queryTrajectory || trajectory.isOriginal) {
        return trajectory;
      }

      const queryCentroid = centroid(queryTrajectory.positions);
      const trajCentroid = centroid(trajectory.positions);

      const translated = trajectory.positions.map((p) => ({
        ...p,
        xCmd: p.xCmd - trajCentroid.x,
        yCmd: p.yCmd - trajCentroid.y,
        zCmd: p.zCmd - trajCentroid.z,
      }));
      const translatedEvents = trajectory.events.map((e) => ({
        ...e,
        xReached: e.xReached - trajCentroid.x,
        yReached: e.yReached - trajCentroid.y,
        zReached: e.zReached - trajCentroid.z,
      }));

      const qStart = queryTrajectory.positions[0];
      const qEnd =
        queryTrajectory.positions[queryTrajectory.positions.length - 1];
      const qVec = {
        x: qEnd.xCmd - qStart.xCmd,
        y: qEnd.yCmd - qStart.yCmd,
        z: qEnd.zCmd - qStart.zCmd,
      };

      const tStart = trajectory.positions[0];
      const tEnd = trajectory.positions[trajectory.positions.length - 1];
      const tVec = {
        x: tEnd.xCmd - tStart.xCmd,
        y: tEnd.yCmd - tStart.yCmd,
        z: tEnd.zCmd - tStart.zCmd,
      };

      const normalize = (v: { x: number; y: number; z: number }) => {
        const len = Math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2);
        if (len < 1e-10) return { x: 1, y: 0, z: 0 };
        return { x: v.x / len, y: v.y / len, z: v.z / len };
      };

      const qNorm = normalize(qVec);
      const tNorm = normalize(tVec);

      const cross = {
        x: tNorm.y * qNorm.z - tNorm.z * qNorm.y,
        y: tNorm.z * qNorm.x - tNorm.x * qNorm.z,
        z: tNorm.x * qNorm.y - tNorm.y * qNorm.x,
      };
      const crossLen = Math.sqrt(cross.x ** 2 + cross.y ** 2 + cross.z ** 2);
      const dot = tNorm.x * qNorm.x + tNorm.y * qNorm.y + tNorm.z * qNorm.z;

      const applyRotation = (p: { x: number; y: number; z: number }) => {
        if (crossLen < 1e-10) {
          if (dot > 0) return p;
          return { x: -p.x, y: -p.y, z: p.z };
        }
        const axis = normalize(cross);
        const angle = Math.atan2(crossLen, dot);
        const c = Math.cos(angle);
        const s = Math.sin(angle);
        const t = 1 - c;
        return {
          x:
            (t * axis.x * axis.x + c) * p.x +
            (t * axis.x * axis.y - s * axis.z) * p.y +
            (t * axis.x * axis.z + s * axis.y) * p.z,
          y:
            (t * axis.x * axis.y + s * axis.z) * p.x +
            (t * axis.y * axis.y + c) * p.y +
            (t * axis.y * axis.z - s * axis.x) * p.z,
          z:
            (t * axis.x * axis.z - s * axis.y) * p.x +
            (t * axis.y * axis.z + s * axis.x) * p.y +
            (t * axis.z * axis.z + c) * p.z,
        };
      };

      const rotatedPositions = translated.map((p) => {
        const r = applyRotation({ x: p.xCmd, y: p.yCmd, z: p.zCmd });
        return {
          ...p,
          xCmd: r.x + queryCentroid.x,
          yCmd: r.y + queryCentroid.y,
          zCmd: r.z + queryCentroid.z,
        };
      });
      const rotatedEvents = translatedEvents.map((e) => {
        const r = applyRotation({
          x: e.xReached,
          y: e.yReached,
          z: e.zReached,
        });
        return {
          ...e,
          xReached: r.x + queryCentroid.x,
          yReached: r.y + queryCentroid.y,
          zReached: r.z + queryCentroid.z,
        };
      });

      return {
        ...trajectory,
        positions: rotatedPositions,
        events: rotatedEvents,
      };
    },
    [],
  );

  const bahnResults = useMemo(
    () => results.filter((r) => r.traj_id && !r.seg_id?.includes('_')),
    [results],
  );

  console.log('results raw:', results);
  console.log('bahnResults:', bahnResults);

  const uniqueIdsForTab = useCallback(
    (tabKey: TabKey): string[] => {
      if (tabKey === 'trajs') {
        const trajIDs = new Set<string>();
        if (originalId) trajIDs.add(originalId);
        const sorted = [...bahnResults].sort((a, b) =>
          stage2Active
            ? (a.dtw_distance ?? Infinity) - (b.dtw_distance ?? Infinity)
            : (b.similarity_score ?? 0) - (a.similarity_score ?? 0),
        );
        sorted.forEach((r) => {
          if (r.traj_id) trajIDs.add(r.traj_id);
        });
        return Array.from(trajIDs).slice(0, 50);
      }

      const segNum = tabKey.replace('segment_', '');
      const group = segmentGroups.find(
        (g) => g.target_segment === `${originalId}_${segNum}`,
      );
      if (!group) return [];
      const ids: string[] = [group.target_segment];
      group.results.forEach((r) => {
        if (r.seg_id) ids.push(r.seg_id);
      });
      return ids.slice(0, 50);
    },
    [bahnResults, segmentGroups, originalId, stage2Active],
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const formatScoreLabel = (result: SimilarityResult | undefined): string => {
    if (!result) return 'N/A';
    if (stage2Active && result.dtw_distance !== undefined)
      return `DTW: ${result.dtw_distance.toFixed(1)}`;
    return `RRF: ${result.similarity_score?.toFixed(4) ?? 'N/A'}`;
  };

  useEffect(() => {
    const loadTrajectories = async () => {
      const uniqueIds = uniqueIdsForTab(activeTab);
      if (uniqueIds.length === 0) return;

      const isShowAll = showAll[activeTab] ?? false;
      const limitedIds = isShowAll
        ? uniqueIds
        : uniqueIds.slice(0, INITIAL_LIMIT + 1);

      const alreadyLoaded = loadedIds[activeTab] ?? new Set<string>();
      const newIds = limitedIds.filter((id) => !alreadyLoaded.has(id));
      if (newIds.length === 0) return;

      setIsLoadingPlot(true);
      setError(null);

      try {
        const isBahn = activeTab === 'trajs';
        const segNum = activeTab.replace('segment_', '');
        const originalSegId = isBahn ? originalId : `${originalId}_${segNum}`;
        const allCandidateIds = uniqueIds.filter((id) => id !== originalSegId);
        const visibleCandidateIds = limitedIds.filter(
          (id) => id !== originalSegId,
        );

        const loadedTrajectories = await Promise.all(
          newIds.map(async (id) => {
            const isOriginal = isBahn
              ? id === originalId
              : id === originalSegId;

            const [positions, events] = await Promise.all([
              isBahn
                ? getTrajPositionCmdById(id)
                : getSegmentPositionCmdById(id),
              isBahn ? getTrajSetpointsById(id) : getSegmentSetpointsById(id),
            ]);

            const sampledPositions = sampleEveryFifthPoint(positions);

            const result = isBahn
              ? bahnResults.find((r) => r.traj_id === id)
              : segmentGroups
                  .find((g) => g.target_segment === originalSegId)
                  ?.results.find((r) => r.seg_id === id);

            const scoreLabel = isOriginal
              ? 'Original'
              : formatScoreLabel(result);
            const candidateRank = allCandidateIds.indexOf(id);

            return {
              id,
              positions: sampledPositions,
              events,
              color: isOriginal
                ? '#ff0000'
                : getTrajectoryColor(
                    candidateRank,
                    visibleCandidateIds.length - 1,
                  ),
              name: isOriginal ? `${id} (Original)` : `${id} (${scoreLabel})`,
              isOriginal,
              similarityScore: result?.similarity_score,
              dtwDistance: result?.dtw_distance,
              rank: stage2Active ? result?.rank_stage2 : undefined,
            } satisfies TrajectoryData;
          }),
        );

        setTabData((prev) => {
          const existing = prev[activeTab] ?? [];
          const existingIds = new Set(existing.map((t) => t.id));
          const fresh = loadedTrajectories.filter(
            (t) => !existingIds.has(t.id),
          );
          return { ...prev, [activeTab]: [...existing, ...fresh] };
        });

        setLoadedIds((prev) => ({
          ...prev,
          [activeTab]: new Set([...alreadyLoaded, ...newIds]),
        }));
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
    activeTab,
    uniqueIdsForTab,
    loadedIds,
    showAll,
    originalId,
    sampleEveryFifthPoint,
    bahnResults,
    segmentGroups,
    stage2Active,
    formatScoreLabel,
  ]);

  // ── Current tab trajectories ──────────────────────────────────────────────
  const trajectoryData = useMemo(
    () => tabData[activeTab] ?? [],
    [tabData, activeTab],
  );

  useEffect(() => {
    setVisibleTrajectories(new Set(trajectoryData.map((t) => t.id)));
  }, [activeTab, tabData, trajectoryData]);

  const toggleVisibility = (id: string) => {
    setVisibleTrajectories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      return newSet;
    });
  };

  const createPlotData = useCallback((): Partial<PlotData>[] => {
    const plotData: Partial<PlotData>[] = [];

    const sorted = [...trajectoryData].sort((a, b) => {
      if (a.isOriginal) return -1;
      if (b.isOriginal) return 1;
      if (stage2Active)
        return (a.dtwDistance ?? Infinity) - (b.dtwDistance ?? Infinity);
      return (b.similarityScore ?? 0) - (a.similarityScore ?? 0);
    });

    const queryTraj = sorted.find((t) => t.isOriginal);
    const dataToPlot = normalizeStartPoint
      ? sorted.map((t) => normalizeTrajectory(t, queryTraj))
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

  const activeTabLabel = tabs.find((t) => t.key === activeTab)?.label ?? '';

  const layout: Partial<Layout> = {
    ...plotLayoutConfig,
    height: 700,
    width: 700,
    scene: {
      camera: {
        up: { x: 0, y: 0, z: 1 },
        center: { x: 0.1, y: 0.1, z: -0.1 },
        eye: { x: 1.5, y: 1.2, z: 1.2 },
      },
      aspectmode: 'cube',
      dragmode: 'orbit',
      xaxis: { title: { text: 'X [mm]' }, showgrid: true, zeroline: true },
      yaxis: { title: { text: 'Y [mm]' }, showgrid: true, zeroline: true },
      zaxis: { title: { text: 'Z [mm]' }, showgrid: true, zeroline: true },
    },
    margin: { t: 50, b: 20, l: 20, r: 20 },
    showlegend: false,
    uirevision: activeTab,
  };

  const sortedLegend = [...trajectoryData].sort((a, b) => {
    if (a.isOriginal) return -1;
    if (b.isOriginal) return 1;
    if (stage2Active)
      return (a.dtwDistance ?? Infinity) - (b.dtwDistance ?? Infinity);
    return (b.similarityScore ?? 0) - (a.similarityScore ?? 0);
  });

  if (searchLoading) {
    return (
      <div className="flex w-full flex-row justify-center rounded-lg border border-gray-400 bg-gray-50 p-2">
        <div className="flex flex-col items-center space-y-4 py-8">
          <div className="animate-spin">
            <Loader className="size-8" color="#003560" />
          </div>
          <Typography as="p">Loading results...</Typography>
        </div>
      </div>
    );
  }

  const plotData = createPlotData();

  return (
    <div
      className={`flex w-fit flex-col rounded-lg border border-gray-400 bg-white ${className}`}
    >
      <div className="flex border-b px-2 pt-2">
        {tabs.map((tab) => {
          const isActive = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`mr-2 flex items-center gap-2 rounded-t-md p-2 text-sm font-medium transition-colors ${
                isActive
                  ? '-mb-px border border-gray-200 border-b-white bg-white text-blue-950'
                  : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="flex flex-row justify-start p-2">
        {/* eslint-disable-next-line no-nested-ternary */}
        {error ? (
          <div className="flex flex-1 items-center justify-center py-8 text-center">
            <div>
              <Typography as="h5" className="mb-2 text-red-600">
                Error while loading
              </Typography>
              <Typography as="p" className="text-gray-600">
                {error}
              </Typography>
            </div>
          </div>
        ) : trajectoryData.length === 0 ? (
          <div className="flex flex-1 items-center justify-center py-8">
            {isLoadingPlot ? (
              <div className="flex flex-col items-center space-y-4">
                <div className="animate-spin">
                  <Loader className="size-8" color="#003560" />
                </div>
                <Typography as="p">Loading {activeTabLabel}...</Typography>
              </div>
            ) : (
              <div className="text-center">
                <Typography as="h5" className="mb-2">
                  No comparison data available
                </Typography>
                <Typography as="p" className="text-gray-600">
                  Conduct a similarity search to compare trajectories in
                  3D-space.
                </Typography>
              </div>
            )}
          </div>
        ) : (
          <Plot
            data={plotData}
            layout={layout}
            useResizeHandler
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
        )}

        <div className="m-4 flex flex-col">
          <div className="flex flex-col justify-between rounded">
            <label className="flex cursor-pointer items-center space-x-2">
              <input
                type="checkbox"
                checked={normalizeStartPoint}
                onChange={(e) => setNormalizeStartPoint(e.target.checked)}
                className="rounded"
              />
              <div className="text-sm text-gray-700">Normalize</div>
            </label>
          </div>

          {trajectoryData.length > 0 && (
            <div className="mt-4 space-y-2 overflow-y-auto">
              <div className="mb-2 text-sm font-medium text-gray-700">
                Visible:
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
          {!(showAll[activeTab] ?? false) &&
            uniqueIdsForTab(activeTab).length > INITIAL_LIMIT + 1 && (
              <button
                onClick={() => {
                  setShowAll((prev) => ({ ...prev, [activeTab]: true }));
                  setTabData((prev) => {
                    const allIds = uniqueIdsForTab(activeTab);
                    const isBahn = activeTab === 'trajs';
                    const segNum = activeTab.replace('segment_', '');
                    const originalSegId = isBahn
                      ? originalId
                      : `${originalId}_${segNum}`;
                    const candidateIds = allIds.filter(
                      (id) => id !== originalSegId,
                    ); // ← aus allIds, nicht newIds
                    const existing = prev[activeTab] ?? [];
                    const updated = existing.map((t) => {
                      if (t.isOriginal) return t;
                      const rank = candidateIds.indexOf(t.id);
                      return {
                        ...t,
                        color: getTrajectoryColor(
                          rank,
                          candidateIds.length - 1,
                        ),
                      };
                    });
                    return { ...prev, [activeTab]: updated };
                  });
                }}
                className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                {isLoadingPlot ? 'Loading...' : `Show all`}
              </button>
            )}
        </div>
      </div>
    </div>
  );
};
