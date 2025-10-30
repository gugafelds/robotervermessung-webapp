import Link from 'next/link';
import React from 'react';

import type {
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

interface SimilarityResultsProps {
  results: SimilarityResult[];
  isLoading: boolean;
  error?: string;
  originalId?: string;
  targetBahnFeatures?: TargetFeatures;
  segmentGroups?: SegmentGroup[];
  isSegmentTaskRunning?: boolean;
  segmentProgress?: string;
}

const SimilarityResults: React.FC<SimilarityResultsProps> = ({
  results,
  isLoading,
  error,
  originalId,
  targetBahnFeatures,
  segmentGroups = [],
  isSegmentTaskRunning = false,
  segmentProgress = '',
}) => {
  const bahnResults = results.filter(
    (r) => !r.segment_id || !r.segment_id.includes('_'),
  );
  const segmentResults = results.filter(
    (r) => r.segment_id && r.segment_id.includes('_'),
  );

  if (isLoading) {
    return (
      <div className="w-full rounded-lg border border-gray-400 bg-white p-6">
        <div className="flex items-center justify-center py-8">
          <div className="size-8 animate-spin rounded-full border-b-2 border-blue-950" />
          <span className="ml-3 text-gray-600">Lade Bahn-Ähnlichkeiten...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full rounded-lg border border-gray-400 bg-white p-6">
        <div className="py-4 text-center text-red-600">
          <p className="font-medium">Fehler bei der Suche!</p>
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
          <p>
            Gib eine Bahn- oder Segment-ID ein, um die Ähnlichkeiten zu
            durchsuchen.
          </p>
        </div>
      </div>
    );
  }

  const isTargetEntry = (result: SimilarityResult): boolean => {
    if (!originalId) return false;
    const currentId = result.segment_id || result.bahn_id || '';
    return currentId.includes(originalId);
  };

  const renderRows = (data: SimilarityResult[]) => {
    // ✅ Helper Funktionen für Profile
    const formatVelocityProfile = (result: SimilarityResult) => {
      if (!result.mean_twist_ist) return '-';
      return `[${result.max_twist_ist?.toFixed(0) || '-'}, ${result.mean_twist_ist?.toFixed(0) || '-'}, ${result.std_twist_ist?.toFixed(0) || '-'}]`;
    };

    const formatPosition3D = (result: SimilarityResult) => {
      if (!result.position_x) return '-';
      return `[${result.position_x?.toFixed(0) || '-'}, ${result.position_y?.toFixed(0) || '-'}, ${result.position_z?.toFixed(0) || '-'}]`;
    };

    const formatAccelerationProfile = (result: SimilarityResult) => {
      if (!result.mean_acceleration_ist) return '-';
      return `[${result.min_acceleration_ist?.toFixed(0) || '-'}, ${result.max_acceleration_ist?.toFixed(0) || '-'}, ${result.mean_acceleration_ist?.toFixed(0) || '-'}, ${result.std_acceleration_ist?.toFixed(0) || '-'}]`;
    };

    return data.map((result, index) => {
      const isTarget = isTargetEntry(result);
      const id = result.segment_id || result.bahn_id || 'N/A';
      const type = id.includes('_') ? 'Segment' : 'Bahn';
      const uniqueKey = `${id}-${index}`;

      let rowClass = 'transition-colors hover:bg-gray-100';
      if (isTarget) rowClass += ' border-t-4 border-blue-950 bg-blue-50';
      else if (index % 2 === 0) rowClass += ' bg-white';
      else rowClass += ' bg-gray-50';

      return (
        <tr key={uniqueKey} className={rowClass}>
          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            <Link
              href={`/bewegungsdaten/${id.split('_')[0]}`}
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
                type === 'Bahn'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-blue-100 text-blue-600'
              }`}
            >
              {type}
            </span>
          </td>
          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            {isTarget ? (
              <span className="font-bold text-blue-600">Original</span>
            ) : (
              <span className="font-mono">
                {result.similarity_score?.toFixed(4) ?? 'N/A'}
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
          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
            {result.sidtw_average_distance ? (
              <span className="font-mono">
                {result.sidtw_average_distance.toFixed(4)}
              </span>
            ) : (
              '-'
            )}
          </td>
        </tr>
      );
    });
  };

  const featuresToResult = (f: TargetFeatures): SimilarityResult => ({
    bahn_id: f.segment_id.includes('_') ? f.bahn_id : f.segment_id,
    segment_id: f.segment_id,
    similarity_score: 0,
    duration: f.duration,
    weight: f.weight,
    length: f.length,
    movement_type: f.movement_type,
    mean_twist_ist: f.mean_twist_ist,
    max_twist_ist: f.max_twist_ist,
    std_twist_ist: f.std_twist_ist,
    min_acceleration_ist: f.min_acceleration_ist,
    max_acceleration_ist: f.max_acceleration_ist,
    mean_acceleration_ist: f.mean_acceleration_ist,
    std_acceleration_ist: f.std_acceleration_ist,
    sidtw_average_distance: f.sidtw_average_distance,
    position_x: f.position_x,
    position_y: f.position_y,
    position_z: f.position_z,
  });

  // 👉 Alle Zeilen in einem Array sammeln
  const allRows: JSX.Element[] = [];
  if (targetBahnFeatures)
    allRows.push(...renderRows([featuresToResult(targetBahnFeatures)]));
  if (bahnResults.length > 0) allRows.push(...renderRows(bahnResults));
  if (segmentGroups.length > 0) {
    segmentGroups.forEach((group) => {
      if (group.target_segment_features)
        allRows.push(
          ...renderRows([featuresToResult(group.target_segment_features)]),
        );
      if (group.results.length > 0) allRows.push(...renderRows(group.results));
    });
  } else if (segmentResults.length > 0) {
    allRows.push(...renderRows(segmentResults));
  }

  return (
    <div className="flex flex-col overflow-y-auto rounded-lg border border-gray-400 bg-white shadow-md">
      <div className="bg-gray-50 px-6 py-4">
        <h3 className="text-lg font-medium text-gray-900">
          Ähnlichkeitsergebnisse
        </h3>
        <p className="mt-1 text-sm text-gray-600">
          {bahnResults.length > 0 && `${bahnResults.length} Bahnen`}
          {bahnResults.length > 0 &&
            (segmentResults.length > 0 || segmentGroups.length > 0) &&
            ' • '}
          {(segmentResults.length > 0 || segmentGroups.length > 0) &&
            `${segmentGroups.length || segmentResults.length} Segmente`}
        </p>
      </div>

      {isSegmentTaskRunning && (
        <div className="border-b bg-yellow-50 px-6 py-4">
          <div className="flex items-center">
            <div className="size-4 animate-spin rounded-full border-b-2 border-yellow-600" />
            <span className="ml-3 text-sm text-yellow-800">
              Berechne Segment-Ähnlichkeiten... {segmentProgress}
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
                Typ
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Ähnlichkeit
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Dauer (s)
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Gewicht (kg)
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Länge (mm)
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Bewegungstyp
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Geschwindigkeit [Max, Mean, Std]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Beschleunigung [Min, Max, Mean, Std]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Position [X, Y, Z]
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Genauigkeit
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
