import Link from 'next/link';
import React from 'react';

import type {
  SearchTiming,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

interface SimilarityResultsProps {
  results: SimilarityResult[];
  isLoading: boolean;
  error?: string;
  originalId?: string;
  targetTrajFeatures?: TargetFeatures;
  segmentGroups?: SegmentGroup[];
  isSegmentTaskRunning?: boolean;
  segmentProgress?: string;
  timing?: SearchTiming;
  stage2Active?: boolean;
  dtwMode?: 'position' | 'joint';
  metric?: 'sidtw' | 'qdtw'; // NEU
}

const SimilarityResults: React.FC<SimilarityResultsProps> = ({
  results,
  isLoading,
  error,
  originalId,
  targetTrajFeatures,
  segmentGroups = [],
  isSegmentTaskRunning = false,
  segmentProgress = '',
  timing,
  stage2Active = false,
  dtwMode = 'position',
  metric = 'sidtw', // NEU
}) => {
  const bahnResults = results.filter(
    (r) => !r.seg_id || !r.seg_id.includes('_'),
  );
  const segmentResults = results.filter(
    (r) => r.seg_id && r.seg_id.includes('_'),
  );

  if (isLoading) {
    return (
      <div className="w-full rounded-lg border border-gray-400 bg-white p-6">
        <div className="flex items-center justify-center py-8">
          <div className="size-8 animate-spin rounded-full border-b-2 border-blue-950" />
          <span className="ml-3 text-gray-600">Loading similarities...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full rounded-lg border border-gray-400 bg-white p-6">
        <div className="py-4 text-center text-red-600">
          <p className="font-medium">Error in search!</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (
    results.length === 0 &&
    !isSegmentTaskRunning &&
    segmentGroups.length === 0
  ) {
    return (
      <div className="w-full rounded-lg border border-gray-400 bg-white p-6">
        <div className="py-8 text-center text-gray-500">
          <p>Enter a Trajectory-ID to search for similar trajectories</p>
        </div>
      </div>
    );
  }

  const isTargetEntry = (result: SimilarityResult): boolean => {
    if (!originalId) return false;
    const currentId = result.seg_id || result.traj_id || '';
    return currentId.includes(originalId);
  };

  const renderRows = (data: SimilarityResult[]) => {
    const formatVelocityProfile = (result: SimilarityResult) => {
      if (!result.mean_vel) return '-';
      return `[${result.max_vel?.toFixed(0) || '-'}, ${result.mean_vel?.toFixed(0) || '-'}, ${result.std_vel?.toFixed(0) || '-'}]`;
    };

    const formatPosition3D = (result: SimilarityResult) => {
      if (!result.position_x) return '-';
      return `[${result.position_x?.toFixed(0) || '-'}, ${result.position_y?.toFixed(0) || '-'}, ${result.position_z?.toFixed(0) || '-'}]`;
    };

    const formatAccelerationProfile = (result: SimilarityResult) => {
      if (!result.mean_accel) return '-';
      return `[${result.min_accel?.toFixed(0) || '-'}, ${result.max_accel?.toFixed(0) || '-'}, ${result.mean_accel?.toFixed(0) || '-'}, ${result.std_accel?.toFixed(0) || '-'}]`;
    };

    const formatAccuracy = (result: SimilarityResult) => {
      if (result.min_distance == null) return '-';
      return `[${result.min_distance.toFixed(4)}, ${result.mean_distance?.toFixed(4) ?? '-'}, ${result.max_distance?.toFixed(4) ?? '-'}]`;
    };

    return data.map((result, index) => {
      const isTarget = isTargetEntry(result);
      const id = result.seg_id || result.traj_id || 'N/A';
      const type = id.includes('_') ? 'Segment' : 'Trajectory';
      const uniqueKey = `${id}-${index}`;

      let rowClass = 'transition-colors hover:bg-gray-100';
      if (isTarget) rowClass += ' border-t-4 border-blue-950 bg-blue-50';
      else if (index % 2 === 0) rowClass += ' bg-white';
      else rowClass += ' bg-gray-50';

      return (
        <tr key={uniqueKey} className={rowClass}>
          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            <Link
              href={`/motion/${id.split('_')[0]}`}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex hover:text-blue-600 ${isTarget ? 'font-bold text-blue-900' : 'text-gray-900'}`}
            >
              {id}
            </Link>
          </td>
          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            <span
              className={`rounded-full px-2 py-1 text-xs ${
                type === 'Trajectory'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-blue-100 text-blue-600'
              }`}
            >
              {type}
            </span>
          </td>

          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            {isTarget ? (
              <span className="font-bold text-blue-600">Query</span>
            ) : (
              <span className="font-mono">
                {stage2Active
                  ? (result.dtw_distance?.toFixed(4) ?? 'N/A')
                  : (result.similarity_score?.toFixed(4) ?? 'N/A')}
              </span>
            )}
          </td>

          <td className="whitespace-nowrap px-6 py-4 font-mono text-sm text-gray-900">
            {result.duration ? result.duration.toFixed(2) : '-'}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-sm text-gray-900">
            {result.weight ? result.weight.toFixed(2) : '-'}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-sm text-gray-900">
            {result.length ? result.length.toFixed(1) : '-'}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-sm uppercase text-gray-900">
            {result.movement_type || '-'}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-900">
            {formatVelocityProfile(result)}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-900">
            {formatAccelerationProfile(result)}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-900">
            {formatPosition3D(result)}
          </td>
          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-gray-900">
            {formatAccuracy(result)}
          </td>
        </tr>
      );
    });
  };

  const featuresToResult = (f: TargetFeatures): SimilarityResult => ({
    traj_id: f.seg_id.includes('_') ? f.traj_id : f.seg_id,
    seg_id: f.seg_id,
    similarity_score: 0,
    duration: f.duration,
    weight: f.weight,
    length: f.length,
    movement_type: f.movement_type,
    mean_vel: f.mean_vel,
    max_vel: f.max_vel,
    std_vel: f.std_vel,
    min_accel: f.min_accel,
    max_accel: f.max_accel,
    mean_accel: f.mean_accel,
    std_accel: f.std_accel,
    min_distance: f.min_distance,
    mean_distance: f.mean_distance,
    max_distance: f.max_distance,
    position_x: f.position_x,
    position_y: f.position_y,
    position_z: f.position_z,
  });

  const allRows: JSX.Element[] = [];
  if (targetTrajFeatures)
    allRows.push(...renderRows([featuresToResult(targetTrajFeatures)]));
  if (bahnResults.length > 0) allRows.push(...renderRows(bahnResults));
  if (segmentGroups.length > 0) {
    segmentGroups.forEach((group) => {
      if (group.target_segment_features)
        allRows.push(
          ...renderRows([featuresToResult(group.target_segment_features)]),
        );
      if (group.similar_segments.results.length > 0)
        allRows.push(
          ...renderRows(
            group.similar_segments.results.map((r) => ({
              traj_id: r.traj_id,
              seg_id: r.seg_id,
              similarity_score: r.rrf_score ?? 0,
              rank_stage1: r.rank_stage1,
              rank_stage2: r.rank_stage2,
              dtw_distance: r.dtw_distance,
              duration: r.features?.duration ?? 0,
              weight: r.features?.weight ?? 0,
              length: r.features?.length ?? 0,
              movement_type: r.features?.movement_type ?? '',
              mean_vel: r.features?.mean_vel ?? 0,
              max_vel: r.features?.max_vel ?? 0,
              std_vel: r.features?.std_vel ?? 0,
              mean_accel: r.features?.mean_accel ?? 0,
              max_accel: r.features?.max_accel ?? 0,
              min_accel: r.features?.min_accel ?? 0,
              std_accel: r.features?.std_accel ?? 0,
              min_distance: r.features?.min_distance,
              mean_distance: r.features?.mean_distance,
              max_distance: r.features?.max_distance,
              position_x: r.features?.position_x ?? 0,
              position_y: r.features?.position_y ?? 0,
              position_z: r.features?.position_z ?? 0,
            })),
          ),
        );
    });
  } else if (segmentResults.length > 0) {
    allRows.push(...renderRows(segmentResults));
  }

  return (
    <div className="flex flex-col overflow-y-auto rounded-lg border border-gray-400 bg-white shadow-md">
      <div className="bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              Similarity results
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {bahnResults.length > 0 && `${bahnResults.length} Bahnen`}
              {bahnResults.length > 0 &&
                (segmentResults.length > 0 || segmentGroups.length > 0) &&
                ' • '}
              {(segmentResults.length > 0 || segmentGroups.length > 0) &&
                `${segmentGroups.length || segmentResults.length} Segmente`}
              <span className="ml-2 rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium uppercase text-gray-700">
                {metric}
              </span>
              {stage2Active && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                  DTW {dtwMode}
                </span>
              )}
            </p>
          </div>

          {timing && (
            <div className="flex gap-3 text-xs text-gray-500">
              <span>
                Stage 1:{' '}
                <span className="font-mono font-medium text-gray-700">
                  {timing.stage1_ms?.toFixed(0)} ms
                </span>
              </span>
              {timing.data_loading_ms !== undefined && (
                <span>
                  Loading:{' '}
                  <span className="font-mono font-medium text-gray-700">
                    {timing.data_loading_ms.toFixed(0)} ms
                  </span>
                </span>
              )}
              {timing.stage2_ms !== undefined && (
                <span>
                  Stage 2:{' '}
                  <span className="font-mono font-medium text-gray-700">
                    {timing.stage2_ms.toFixed(0)} ms
                  </span>
                </span>
              )}
              <span className="font-medium text-gray-700">
                Total: {timing.total_ms?.toFixed(0)} ms
              </span>
            </div>
          )}
        </div>
      </div>

      {isSegmentTaskRunning && (
        <div className="border-b bg-yellow-50 px-6 py-4">
          <div className="flex items-center">
            <div className="size-4 animate-spin rounded-full border-b-2 border-yellow-600" />
            <span className="ml-3 text-sm text-yellow-800">
              Calculation segment similarities... {segmentProgress}
            </span>
          </div>
        </div>
      )}

      <div className="max-h-[70vh] overflow-auto border-t">
        <table className="w-fit min-w-full table-auto">
          <thead className="sticky top-0 border-b-2 bg-gray-50 shadow-md">
            <tr>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                ID
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Type
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                {stage2Active ? 'DTW-Dist' : 'RRF Score'}
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Duration [s]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Weight [kg]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Length [mm]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Mov. Type
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Velocity [Max, Mean, Std]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Accel. [Min, Max, Mean, Std]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Position [X, Y, Z]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                {metric.toUpperCase()} [Min, Mean, Max]
              </th>
            </tr>
          </thead>
          <tbody className="bg-white text-center">{allRows}</tbody>
        </table>
      </div>
    </div>
  );
};

export default SimilarityResults;
