/* eslint-disable react/button-has-type */

'use client';

import React, { useState } from 'react';

type SimilaritySearchProps = {
  onSearch: (
    id: string,
    bahnLimit: number,
    segmentLimit: number,
    weights: Record<string, number>,
  ) => void;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({ onSearch }) => {
  const [id, setId] = useState('');
  const [bahnLimit, setBahnLimit] = useState(10);

  // Gewichtungs-State
  const [weights, setWeights] = useState({
    duration: 1.0,
    weight: 1.0,
    length: 1.0,
    movement_type: 1.0,
    direction_x: 1.0,
    direction_y: 1.0,
    direction_z: 1.0,
  });

  // Segment Limit ist automatisch die Hälfte von Bahn Limit, aufgerundet
  const segmentLimit = Math.ceil(bahnLimit / 2);

  // Preset-Konfigurationen
  const presets = {
    standard: {
      duration: 1.0,
      weight: 1.0,
      length: 1.0,
      movement_type: 1.0,
      direction_x: 1.0,
      direction_y: 1.0,
      direction_z: 1.0,
    },
    geometrie: {
      duration: 2.0,
      weight: 1.0,
      length: 10.0,
      movement_type: 1.0,
      direction_x: 5.0,
      direction_y: 5.0,
      direction_z: 5.0,
    },
    bewegung: {
      duration: 1.0,
      weight: 1.0,
      length: 3.0,
      movement_type: 10.0,
      direction_x: 5.0,
      direction_y: 5.0,
      direction_z: 5.0,
    },
    zeit: {
      duration: 10.0,
      weight: 1.0,
      length: 1.0,
      movement_type: 1.0,
      direction_x: 1.0,
      direction_y: 1.0,
      direction_z: 1.0,
    },
  };

  const handleSearch = () => {
    if (id.trim()) {
      onSearch(id.trim(), bahnLimit, segmentLimit, weights);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleBahnLimitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (value >= 1 && value <= 50) {
      setBahnLimit(value);
    }
  };

  const handleWeightChange = (feature: string, value: number) => {
    setWeights((prev) => ({
      ...prev,
      [feature]: value,
    }));
  };

  const applyPreset = (presetName: keyof typeof presets) => {
    setWeights(presets[presetName]);
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

        {/* Preset-Buttons */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="mb-2 text-sm font-medium text-gray-700">
            Gewichtungs-Presets:
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => applyPreset('standard')}
              className="rounded-full bg-gray-200 px-3 py-1 text-xs transition-colors hover:bg-gray-300"
            >
              Standard
            </button>
            <button
              onClick={() => applyPreset('geometrie')}
              className="rounded-full bg-green-200 px-3 py-1 text-xs transition-colors hover:bg-green-300"
            >
              Fokus Geometrie
            </button>
            <button
              onClick={() => applyPreset('bewegung')}
              className="rounded-full bg-blue-200 px-3 py-1 text-xs transition-colors hover:bg-blue-300"
            >
              Fokus Bewegung
            </button>
            <button
              onClick={() => applyPreset('zeit')}
              className="rounded-full bg-yellow-200 px-3 py-1 text-xs transition-colors hover:bg-yellow-300"
            >
              Fokus Zeit
            </button>
          </div>
        </div>

        {/* Gewichtungs-Slider */}
        <div className="space-y-3 rounded-lg bg-white p-3">
          <div className="text-sm font-medium text-gray-700">
            Gewichtungen anpassen:
          </div>

          {Object.entries(weights).map(([feature, value]) => {
            const sliderId = `slider-${feature}`;
            return (
              <div key={feature} className="space-y-1">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor={sliderId}
                    className="text-xs capitalize text-gray-600"
                  >
                    {feature.replace('_', ' ')}:
                  </label>
                  <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
                    {value.toFixed(1)}
                  </span>
                </div>
                <input
                  id={sliderId}
                  type="range"
                  min="0"
                  max="10"
                  step="1.0"
                  value={value}
                  onChange={(e) =>
                    handleWeightChange(feature, parseFloat(e.target.value))
                  }
                  className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200"
                />
              </div>
            );
          })}
        </div>

        {/* Limit Einstellungen */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="flex items-center justify-between">
            {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
            <label
              htmlFor="bahn-limit"
              className="text-sm font-medium text-gray-700"
            >
              Anzahl ähnliche Bahnen:
            </label>
            <input
              id="bahn-limit"
              type="number"
              min="1"
              max="50"
              value={bahnLimit}
              onChange={handleBahnLimitChange}
              className="w-16 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>Segmente pro Target-Segment:</span>
            <span className="rounded bg-gray-100 px-2 py-1 font-mono">
              {segmentLimit}
            </span>
          </div>
        </div>

        {/* Auto-Schwellwert Info */}
        <div className="text-xs text-gray-600">
          Schwellwert wird automatisch optimiert
        </div>

        {/* Such-Button */}
        <button
          onClick={handleSearch}
          className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Ähnliche finden
        </button>
      </div>
    </div>
  );
};

export default SimilaritySearch;
