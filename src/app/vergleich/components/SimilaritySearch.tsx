/* eslint-disable jsx-a11y/label-has-associated-control */
/* eslint-disable react/button-has-type */
// components/SimilaritySearch.tsx

'use client';

import React, { useEffect, useRef, useState } from 'react';

import type { BahnInfo } from '@/types/bewegungsdaten.types';

type SimilaritySearchProps = {
  onSearch: (
    id: string,
    limit: number,
    modes: string[],
    weights: {
      position: number;
      joint: number;
      orientation: number;
      velocity: number;
      acceleration: number;
      metadata: number;
    },
    prefilterFeatures: string[],
  ) => void;
  bahnInfo?: BahnInfo[] | undefined;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({
  onSearch,
  bahnInfo,
}) => {
  const [id, setId] = useState('');
  const [limit, setLimit] = useState(5); // ✅ Ein Limit für Bahnen + Segmente
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [activeModes, setActiveModes] = useState<Set<string>>(
    new Set(['position']),
  );

  const [weights, setWeights] = useState({
    position: 0.2,
    joint: 0.2,
    orientation: 0.2,
    velocity: 0.2,
    acceleration: 0.2,
    metadata: 0.2,
  });

  const [prefilterFeatures, setPrefilterFeatures] = useState<Set<string>>(
    new Set(['movement_type']),
  );

  const recentBahnIds = bahnInfo ? bahnInfo.map((bahn) => bahn.bahnID) : [];

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

  const presets = {
    balanced: {
      position: 0.2,
      joint: 0.2,
      orientation: 0.2,
      velocity: 0.2,
      acceleration: 0.2,
      metadata: 0.2,
      modes: [
        'position',
        'joint',
        'orientation',
        'velocity',
        'acceleration',
        'metadata',
      ],
    },
    shape: {
      position: 1.0,
      joint: 0.0,
      orientation: 0.0,
      velocity: 0.0,
      acceleration: 0.0,
      metadata: 0.0,
      modes: ['position'],
    },
    motion: {
      position: 0.3,
      joint: 0.8,
      orientation: 0.3,
      velocity: 0.0,
      acceleration: 0.0,
      metadata: 0.0,
      modes: ['position', 'joint', 'orientation'],
    },
    intensity: {
      position: 0.0,
      joint: 0.3,
      orientation: 0.0,
      velocity: 0.6,
      acceleration: 0.3,
      metadata: 0.0,
      modes: ['joint', 'velocity', 'acceleration'],
    },
  };

  const handleSearch = () => {
    if (id.trim() && activeModes.size > 0) {
      // Normalisiere Gewichte basierend auf aktiven Modi
      const activeWeights = { ...weights };
      const inactiveModes = [
        'position',
        'joint',
        'orientation',
        'velocity',
        'acceleration',
        'metadata',
      ].filter((m) => !activeModes.has(m));

      // Setze inaktive Modi auf 0
      inactiveModes.forEach((mode) => {
        activeWeights[mode as keyof typeof weights] = 0;
      });

      onSearch(
        id.trim(),
        limit,
        Array.from(activeModes),
        activeWeights,
        Array.from(prefilterFeatures), // ✅ NEU
      );
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

  const togglePrefilterFeature = (feature: string) => {
    setPrefilterFeatures((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(feature)) {
        newSet.delete(feature);
      } else {
        newSet.add(feature);
      }
      return newSet;
    });
  };

  const applyPreset = (presetName: keyof typeof presets) => {
    const preset = presets[presetName];
    setWeights({
      position: preset.position,
      joint: preset.joint,
      orientation: preset.orientation,
      velocity: preset.velocity,
      acceleration: preset.acceleration,
      metadata: preset.metadata,
    });
    setActiveModes(new Set(preset.modes));
  };

  return (
    <div className="w-full rounded-xl border border-gray-400 bg-gray-100 p-4">
      <div className="space-y-2">
        {/* Haupteingabe mit Dropdown */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            placeholder="Bahn-ID eingeben..."
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

        <div className="flex items-center gap-8 rounded-lg bg-white p-3 text-sm sm:flex-col lg:flex-row">
          <div>Modi:</div>
          <div className="w-fit gap-2 space-x-2">
            {[
              'position',
              'joint',
              'orientation',
              'velocity',
              'acceleration',
              'metadata',
            ].map((mode) => (
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
          <div className="text-sm font-medium text-gray-700">Gewichtungen:</div>
          <span className="flex w-fit flex-col gap-3 sm:flex-row">
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
                      {value.toFixed(1)}
                    </span>
                  </div>
                  <input
                    id={sliderId}
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
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
          </span>
        </div>

        {/* Preset-Buttons */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="flex flex-col items-center gap-6 sm:flex-row">
            {/* Prefilter Features */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Features:
              </span>
              {[
                { key: 'length', label: 'Länge' },
                { key: 'duration', label: 'Dauer' },
                { key: 'movement_type', label: 'Bewegungstyp' },
                { key: 'position_3d', label: 'Lage' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => togglePrefilterFeature(key)}
                  className={`rounded-full px-3 py-1 text-xs transition-colors ${
                    prefilterFeatures.has(key)
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Vertikaler Separator */}
            <div className="h-6 w-px bg-gray-300" />

            {/* Presets */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Presets:
              </span>
              <button
                onClick={() => applyPreset('balanced')}
                className="rounded-full bg-gray-200 px-3 py-1 text-xs transition-colors hover:bg-gray-300"
              >
                Balanced
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
              <button
                onClick={() => applyPreset('intensity')}
                className="rounded-full bg-red-200 px-3 py-1 text-xs transition-colors hover:bg-red-300"
              >
                Intensity
              </button>
            </div>

            {/* Vertikaler Separator */}
            <div className="h-6 w-px bg-gray-300" />

            {/* Limit Einstellungen */}
            <div className=" rounded-lg bg-white p-3">
              <div className="flex items-center justify-between space-x-2">
                <label
                  htmlFor="limit"
                  className="text-sm font-medium text-gray-700"
                >
                  Anzahl Ergebnisse (Limit):
                </label>
                <input
                  id="limit"
                  type="number"
                  min="1"
                  max="50"
                  value={limit}
                  onChange={handleLimitChange}
                  className="w-16 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
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
