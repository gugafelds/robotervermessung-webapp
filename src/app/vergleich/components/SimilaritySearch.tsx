'use client';

import React, { useState } from 'react';

type SimilaritySearchProps = {
  onSearch: (id: string) => void;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({ onSearch }) => {
  const [id, setId] = useState('');

  const handleSearch = () => {
    if (id.trim()) {
      onSearch(id.trim());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="w-full bg-gray-100 p-4">
      <div className="space-y-3">
        {/* Haupteingabe */}
        <div>
          <input
            type="text"
            placeholder="Bahn/Segment-ID eingeben..."
            value={id}
            onChange={(e) => setId(e.target.value)}
            onKeyDown={handleKeyPress}
            className="w-full rounded-xl bg-gray-50 p-3 text-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Auto-Schwellwert Info */}
        <div className="text-xs text-gray-600">
          Schwellwert wird automatisch optimiert
        </div>

        {/* Such-Button */}
        <button
          onClick={handleSearch}
          className="w-full rounded-lg bg-blue-600 py-2 text-white font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Ähnliche finden
        </button>
      </div>
    </div>
  );
};

export default SimilaritySearch;