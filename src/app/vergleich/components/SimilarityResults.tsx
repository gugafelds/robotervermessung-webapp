import Link from 'next/link';
import React from 'react';

interface SimilarityResult {
  bahn_id?: string;
  segment_id?: string;
  similarity_score: number;
  meta_value?: number;
  duration?: number;
  weight?: number;
  length?: number;
  movement_type?: string;
  median_twist_ist?: number;
  median_acceleration_ist?: number;
  sidtw_average_distance?: number;
}

interface TargetFeatures {
  segment_id: string;
  bahn_id: string;
  duration?: number;
  length?: number;
  median_twist_ist?: number;
  median_acceleration_ist?: number;
  movement_type?: string;
}

interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  results: SimilarityResult[];
}

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
      <div className="w-full rounded-lg bg-white p-6 shadow-md">
        <div className="flex items-center justify-center py-8">
          <div className="size-8 animate-spin rounded-full border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600">Lade Bahn-Ähnlichkeiten...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full rounded-lg bg-white p-6 shadow-md">
        <div className="py-4 text-center text-red-600">
          <p className="font-medium">Fehler bei der Suche</p>
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
      <div className="w-full rounded-lg bg-white p-6 shadow-md">
        <div className="py-8 text-center text-gray-500">
          <p>Keine Ergebnisse gefunden</p>
          <p className="mt-1 text-sm">Versuchen Sie eine andere ID</p>
        </div>
      </div>
    );
  }

  const isTargetEntry = (result: SimilarityResult): boolean => {
    if (!originalId) return false;
    const currentId = result.segment_id || result.bahn_id || '';
    return currentId.includes(originalId);
  };

  const renderRows = (data: SimilarityResult[]) =>
    data.map((result, index) => {
      const isTarget = isTargetEntry(result);
      const id = result.segment_id || result.bahn_id || 'N/A';
      const type = id.includes('_') ? 'Segment' : 'Bahn';
      const uniqueKey = `${id}-${index}`;

      let rowClass = 'transition-colors hover:bg-gray-100';
      if (isTarget) rowClass += ' border-l-4 border-blue-500 bg-blue-50';
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

  const featuresToResult = (f: TargetFeatures): SimilarityResult => ({
    bahn_id: f.segment_id.includes('_') ? f.bahn_id : f.segment_id,
    segment_id: f.segment_id,
    similarity_score: 0,
    duration: f.duration,
    length: f.length,
    movement_type: f.movement_type,
    median_twist_ist: f.median_twist_ist,
    median_acceleration_ist: f.median_acceleration_ist,
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
    <div className="flex flex-col overflow-y-auto rounded-lg border bg-white shadow-md">
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
        <table className="w-fit min-w-full table-auto divide-y divide-gray-200">
          <thead className="sticky top-0 z-10 border-b-4 bg-gray-50 shadow-xl">
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
                Genauigkeit
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white text-center">
            {allRows}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SimilarityResults;
