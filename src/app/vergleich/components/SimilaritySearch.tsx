// components/SimilaritySearch.tsx

'use client';

import React, { useEffect, useRef, useState } from 'react';

import type { BahnInfo } from '@/types/bewegungsdaten.types';

type SimilaritySearchProps = {
  onSearch: (
    id: string,
    limit: number,
    modes: string[],
    weights: { joint: number; position: number; orientation: number },
  ) => void;
  bahnInfo?: BahnInfo[] | undefined;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({
  onSearch,
  bahnInfo,
}) => {
  const [id, setId] = useState('');
  const [limit, setLimit] = useState(10); // ✅ Ein Limit für Bahnen + Segmente
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ✅ NEU: Embedding Modi (welche Embeddings nutzen?)
  const [activeModes, setActiveModes] = useState<Set<string>>(
    new Set(['joint', 'position', 'orientation']),
  );

  // ✅ NEU: Embedding Gewichtungen (statt Feature-Gewichtungen)
  const [weights, setWeights] = useState({
    joint: 0.33,
    position: 0.33,
    orientation: 0.34,
  });

  // Hole die letzten Bahn-IDs
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

  // ✅ NEU: Preset-Konfigurationen für Embeddings
  const presets = {
    balanced: {
      joint: 0.33,
      position: 0.33,
      orientation: 0.34,
      modes: ['joint', 'position', 'orientation'],
    },
    geometry: {
      joint: 0.1,
      position: 0.6,
      orientation: 0.3,
      modes: ['position', 'orientation'],
    },
    motion: {
      joint: 0.7,
      position: 0.2,
      orientation: 0.1,
      modes: ['joint', 'position'],
    },
    shape: {
      joint: 0.0,
      position: 0.5,
      orientation: 0.5,
      modes: ['position', 'orientation'],
    },
  };

  const handleSearch = () => {
    if (id.trim() && activeModes.size > 0) {
      // Normalisiere Gewichte basierend auf aktiven Modi
      const activeWeights = { ...weights };
      const inactiveModes = ['joint', 'position', 'orientation'].filter(
        (m) => !activeModes.has(m),
      );

      // Setze inaktive Modi auf 0
      inactiveModes.forEach((mode) => {
        activeWeights[mode as keyof typeof weights] = 0;
      });

      onSearch(id.trim(), limit, Array.from(activeModes), activeWeights);
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
  };

  const handleLimitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (value >= 1 && value <= 100) {
      setLimit(value);
    }
  };

  const handleWeightChange = (mode: string, value: number) => {
    setWeights((prev) => ({
      ...prev,
      [mode]: value,
    }));
  };

  const toggleMode = (mode: string) => {
    setActiveModes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(mode)) {
        // Mindestens ein Modus muss aktiv bleiben
        if (newSet.size > 1) {
          newSet.delete(mode);
        }
      } else {
        newSet.add(mode);
      }
      return newSet;
    });
  };

  const applyPreset = (presetName: keyof typeof presets) => {
    const preset = presets[presetName];
    setWeights({
      joint: preset.joint,
      position: preset.position,
      orientation: preset.orientation,
    });
    setActiveModes(new Set(preset.modes));
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

        {/* ✅ NEU: Embedding Modi Auswahl */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="mb-2 text-sm font-medium text-gray-700">
            Embedding Modi:
          </div>
          <div className="flex flex-wrap gap-2">
            {['joint', 'position', 'orientation'].map((mode) => (
              <button
                key={mode}
                onClick={() => toggleMode(mode)}
                className={`rounded-full px-3 py-1 text-xs transition-colors ${
                  activeModes.has(mode)
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Preset-Buttons */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="mb-2 text-sm font-medium text-gray-700">Presets:</div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => applyPreset('balanced')}
              className="rounded-full bg-gray-200 px-3 py-1 text-xs transition-colors hover:bg-gray-300"
            >
              Balanced
            </button>
            <button
              onClick={() => applyPreset('geometry')}
              className="rounded-full bg-green-200 px-3 py-1 text-xs transition-colors hover:bg-green-300"
            >
              Geometry
            </button>
            <button
              onClick={() => applyPreset('motion')}
              className="rounded-full bg-blue-200 px-3 py-1 text-xs transition-colors hover:bg-blue-300"
            >
              Motion
            </button>
            <button
              onClick={() => applyPreset('shape')}
              className="rounded-full bg-purple-200 px-3 py-1 text-xs transition-colors hover:bg-purple-300"
            >
              Shape
            </button>
          </div>
        </div>

        {/* ✅ Embedding Gewichtungs-Slider */}
        <div className="space-y-3 rounded-lg bg-white p-3">
          <div className="text-sm font-medium text-gray-700">
            Embedding Gewichtungen:
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {Object.entries(weights).map(([mode, value]) => {
              const isActive = activeModes.has(mode);
              const sliderId = `slider-${mode}`;

              return (
                <div
                  key={mode}
                  className={`space-y-1 ${!isActive ? 'opacity-40' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor={sliderId}
                      className="text-xs capitalize text-gray-600"
                    >
                      {mode}:
                    </label>
                    <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
                      {value.toFixed(2)}
                    </span>
                  </div>
                  <input
                    id={sliderId}
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={value}
                    onChange={(e) =>
                      handleWeightChange(mode, parseFloat(e.target.value))
                    }
                    disabled={!isActive}
                    className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-200 disabled:cursor-not-allowed"
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Limit Einstellungen */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="flex items-center justify-between">
            <label
              htmlFor="limit"
              className="text-sm font-medium text-gray-700"
            >
              Anzahl Ergebnisse (Bahnen + Segmente):
            </label>
            <input
              id="limit"
              type="number"
              min="1"
              max="100"
              value={limit}
              onChange={handleLimitChange}
              className="w-16 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Info */}
        <div className="text-xs text-gray-600">
          🎯 Embedding-basierte Ähnlichkeitssuche (RRF Fusion)
        </div>

        {/* Such-Button */}
        <button
          onClick={handleSearch}
          disabled={activeModes.size === 0}
          className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          style={{ backgroundColor: '#003560' }}
        >
          Ähnliche finden
        </button>
      </div>
    </div>
  );
};

export default SimilaritySearch;
