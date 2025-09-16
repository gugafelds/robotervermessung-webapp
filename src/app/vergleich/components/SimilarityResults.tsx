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
}

const SimilarityResults: React.FC<SimilarityResultsProps> = ({ results, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="w-full bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Suche ähnliche Einträge...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full bg-white rounded-lg shadow-md p-6">
        <div className="text-red-600 text-center py-4">
          <p className="font-medium">Fehler bei der Suche</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="w-full bg-white rounded-lg shadow-md p-6">
        <div className="text-gray-500 text-center py-8">
          <p>Keine Ergebnisse gefunden</p>
          <p className="text-sm mt-1">Versuchen Sie eine andere ID</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 border-b">
        <h3 className="text-lg font-medium text-gray-900">
          Ähnlichkeitsergebnisse ({results.length})
        </h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Typ
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ähnlichkeit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Dauer (s)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Gewicht (kg)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Länge (mm)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Bewegungstyp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                SIDTW
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result, index) => {
              const isTarget = result.similarity_score === 0;
              const id = result.segment_id || result.bahn_id || 'N/A';
              const type = result.segment_id ? 'Segment' : 'Bahn';
              
              return (
                <tr
                  key={index}
                  className={`${
                    isTarget 
                      ? 'bg-blue-50 border-l-4 border-blue-500' 
                      : index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                  } hover:bg-gray-100 transition-colors`}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {isTarget && (
                        <span className="mr-2 text-blue-600 font-bold">🎯</span>
                      )}
                      <span className={`text-sm ${isTarget ? 'font-bold text-blue-900' : 'text-gray-900'}`}>
                        {id}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      type === 'Bahn' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-purple-100 text-purple-800'
                    }`}>
                      {type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {isTarget ? (
                      <span className="text-blue-600 font-bold">Original</span>
                    ) : (
                      <span className="font-mono">
                        {result.similarity_score.toFixed(4)}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {result.duration ? result.duration.toFixed(2) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {result.weight ? result.weight.toFixed(2) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {result.length ? result.length.toFixed(1) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className="capitalize">
                      {result.movement_type || '-'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
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