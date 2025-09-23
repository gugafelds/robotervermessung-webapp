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
  sidtw_average_distance?: number;
}

interface SimilarityResultsProps {
  results: SimilarityResult[];
  isLoading: boolean;
  error?: string;
  originalId?: string;
  // Neue Props für progressives Loading
  isSegmentTaskRunning?: boolean;
  segmentProgress?: string;
}

const SimilarityResults: React.FC<SimilarityResultsProps> = ({
  results,
  isLoading,
  error,
  originalId,
  isSegmentTaskRunning = false,
  segmentProgress = '',
}) => {
  // Bahnen vs Segmente trennen für bessere Anzeige
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

  if (results.length === 0 && !isSegmentTaskRunning) {
    return (
      <div className="w-full rounded-lg bg-white p-6 shadow-md">
        <div className="py-8 text-center text-gray-500">
          <p>Keine Ergebnisse gefunden</p>
          <p className="mt-1 text-sm">Versuchen Sie eine andere ID</p>
        </div>
      </div>
    );
  }

  // Target-Erkennung basierend auf ursprünglich eingegebener ID
  const isTargetEntry = (result: SimilarityResult): boolean => {
    if (!originalId) return false;
    const currentId = result.segment_id || result.bahn_id || '';
    return currentId.includes(originalId);
  };

  const renderTable = (data: SimilarityResult[], title: string) => (
    <div className="border-t">
      <div className="border-b bg-gray-50 px-6 py-4">
        <h4 className="font-medium text-gray-900">
          {title} ({data.length})
        </h4>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Typ
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Ähnlichkeit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Dauer (s)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Gewicht (kg)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Länge (mm)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Bewegungstyp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Genauigkeit
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {data.map((result, index) => {
              const isTarget = isTargetEntry(result);
              const id = result.segment_id || result.bahn_id || 'N/A';
              const type = id.includes('_') ? 'Segment' : 'Bahn';
              const uniqueKey = `${id}-${index}`;

              let rowClassName = 'transition-colors hover:bg-gray-100';
              if (isTarget) {
                rowClassName += ' border-l-4 border-blue-500 bg-blue-50';
              } else if (index % 2 === 0) {
                rowClassName += ' bg-white';
              } else {
                rowClassName += ' bg-gray-50';
              }

              return (
                <tr key={uniqueKey} className={rowClassName}>
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center">
                      {isTarget && (
                        <span className="mr-2 font-bold text-blue-600">🎯</span>
                      )}
                      <span
                        className={`text-sm ${isTarget ? 'font-bold text-blue-900' : 'text-gray-900'}`}
                      >
                        <Link
                          href={`/bewegungsdaten/${id.split('_')[0]}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center hover:text-blue-600"
                        >
                          <span>{id}</span>
                        </Link>
                      </span>
                    </div>
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
                        {result.similarity_score.toFixed(4)}
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {result.duration ? result.duration.toFixed(2) : '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {result.weight ? result.weight.toFixed(2) : '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {result.length ? result.length.toFixed(1) : '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    <span className="uppercase">
                      {result.movement_type || '-'}
                    </span>
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
            })}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="w-full overflow-hidden rounded-lg border bg-white shadow-md">
      <div className="bg-gray-50 px-6 py-4">
        <h3 className="text-lg font-medium text-gray-900">
          Ähnlichkeitsergebnisse
        </h3>
        <p className="mt-1 text-sm text-gray-600">
          {bahnResults.length > 0 && `${bahnResults.length} Bahnen`}
          {bahnResults.length > 0 && segmentResults.length > 0 && ' • '}
          {segmentResults.length > 0 && `${segmentResults.length} Segmente`}
        </p>
      </div>

      {/* Bahn-Ergebnisse (sofort verfügbar) */}
      {bahnResults.length > 0 && renderTable(bahnResults, 'Ähnliche Bahnen')}

      {/* Segment-Status */}
      {isSegmentTaskRunning && (
        <div className="border-b bg-yellow-50 px-6 py-4">
          <div className="flex items-center">
            <div className="size-4 animate-spin rounded-full border-b-2 border-yellow-600" />
            <span className="ml-3 text-sm text-yellow-800">
              Berechne Segment-Ähnlichkeiten...
              {segmentProgress && ` ${segmentProgress}`}
            </span>
          </div>
        </div>
      )}

      {/* Segment-Ergebnisse (kommen später) */}
      {segmentResults.length > 0 &&
        renderTable(segmentResults, 'Ähnliche Segmente')}

      {/* Fallback wenn gar nichts da ist */}
      {!isSegmentTaskRunning &&
        bahnResults.length === 0 &&
        segmentResults.length === 0 && (
          <div className="py-8 text-center text-gray-500">
            <p>Keine Ergebnisse gefunden</p>
            <p className="mt-1 text-sm">Versuchen Sie eine andere ID</p>
          </div>
        )}
    </div>
  );
};

export default SimilarityResults;
