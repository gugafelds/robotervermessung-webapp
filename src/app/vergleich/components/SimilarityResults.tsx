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
}

const SimilarityResults: React.FC<SimilarityResultsProps> = ({
  results,
  isLoading,
  error,
  originalId,
}) => {
  if (isLoading) {
    return (
      <div className="w-full rounded-lg bg-white p-6 shadow-md">
        <div className="flex items-center justify-center py-8">
          <div className="size-8 animate-spin rounded-full border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600">Suche ähnliche Einträge...</span>
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

  if (results.length === 0) {
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

  return (
    <div className="w-full overflow-hidden rounded-lg bg-white shadow-md">
      <div className="border-b bg-gray-50 px-6 py-4">
        <h3 className="text-lg font-medium text-gray-900">
          Ähnlichkeitsergebnisse ({results.length})
        </h3>
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
            {results.map((result, index) => {
              const isTarget = isTargetEntry(result);
              const id = result.segment_id || result.bahn_id || 'N/A';
              const type = id.includes('_') ? 'Segment' : 'Bahn';

              // Eindeutiger Key basierend auf ID statt Array-Index
              const uniqueKey = `${id}-${index}`;

              // Bedingte Klassennamen aufteilen für bessere Lesbarkeit
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
                        {id}
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
};

export default SimilarityResults;
