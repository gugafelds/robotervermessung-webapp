/* eslint-disable react/button-has-type */

'use client';

import React, { useEffect, useRef, useState } from 'react';

import type { BahnInfo } from '@/types/bewegungsdaten.types';

type SimilaritySearchProps = {
  onSearch: (
    id: string,
    bahnLimit: number,
    segmentLimit: number,
    weights: Record<string, number>,
  ) => void;
  bahnInfo?: BahnInfo[] | undefined;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({
  onSearch,
  bahnInfo,
}) => {
  const [id, setId] = useState('');
  const [bahnLimit, setBahnLimit] = useState(5);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // Hole die letzten 5 Bahn-IDs (neueste zuerst)
  const recentBahnIds = bahnInfo ? bahnInfo.map((bahn) => bahn.bahnID) : [];

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        inputRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      length: 2.0,
      movement_type: 1.0,
      direction_x: 1.0,
      direction_y: 1.0,
      direction_z: 1.0,
    },
  };

  const handleSearch = () => {
    if (id.trim()) {
      onSearch(id.trim(), bahnLimit, segmentLimit, weights);
      setShowDropdown(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  const handleInputFocus = () => {
    if (recentBahnIds.length > 0) {
      setShowDropdown(true);
    }
  };

  const handleBahnIdSelect = (selectedId: string) => {
    setId(selectedId);
    setShowDropdown(false);
    // Optional: Sofort suchen nach Auswahl
    // onSearch(selectedId, bahnLimit, segmentLimit, weights);
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
    <div className="w-full rounded border border-gray-300 bg-gray-100 p-4">
      <div className="space-y-2">
        {/* Haupteingabe mit Dropdown */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            placeholder="Bahn/Segment-ID eingeben..."
            value={id}
            onChange={(e) => setId(e.target.value)}
            onKeyDown={handleKeyPress}
            onFocus={handleInputFocus}
            className="w-full rounded-xl bg-gray-50 p-3 text-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          {/* Dropdown mit letzten Bahn-IDs */}
          {showDropdown && recentBahnIds.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute inset-x-0 top-full z-10 mt-1 rounded-lg border border-gray-200 bg-white shadow-lg"
            >
              <div className="p-2">
                {recentBahnIds.map((bahnId, index) => (
                  <button
                    key={bahnId}
                    onClick={() => handleBahnIdSelect(bahnId)}
                    className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100"
                  >
                    <span className="font-mono">{bahnId}</span>
                    <span className="text-xs text-gray-400">#{index + 1}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
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
              Geometrie
            </button>
            <button
              onClick={() => applyPreset('bewegung')}
              className="rounded-full bg-blue-200 px-3 py-1 text-xs transition-colors hover:bg-blue-300"
            >
              Bewegung
            </button>
            <button
              onClick={() => applyPreset('zeit')}
              className="rounded-full bg-yellow-200 px-3 py-1 text-xs transition-colors hover:bg-yellow-300"
            >
              Zeit
            </button>
          </div>
        </div>

        {/* Gewichtungs-Slider */}
        <div className="space-y-3 rounded-lg bg-white p-3">
          <div className="text-sm font-medium text-gray-700">
            Gewichtungen anpassen:
          </div>

          {/* Responsive Grid: 4 Spalten auf großen Bildschirmen, 2 auf mittleren, 1 auf kleinen */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
                      {value.toFixed(0)}
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
          className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          style={{ backgroundColor: '#003560' }}
        >
          Ähnliche finden
        </button>
      </div>
    </div>
  );
};

export default SimilaritySearch;
