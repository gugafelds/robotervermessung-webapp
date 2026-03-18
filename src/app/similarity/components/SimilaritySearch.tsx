/* eslint-disable jsx-a11y/label-has-associated-control */
/* eslint-disable react/button-has-type */

'use client';

import React, { useEffect, useRef, useState } from 'react';

import type { TrajInfo } from '@/types/motion.types';

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
      metadata: number;
    },
    prefilterFeatures: string[],
    stage2Active: boolean,
    dtwMode: 'position' | 'joint',
  ) => void;
  trajInfo?: TrajInfo[];
  showPlots: boolean;
  onTogglePlots: () => void;
  hasResults: boolean;
};

const SimilaritySearch: React.FC<SimilaritySearchProps> = ({
  onSearch,
  trajInfo,
  showPlots,
  onTogglePlots,
  hasResults,
}) => {
  const [id, setId] = useState('');
  const [limit, setLimit] = useState(5);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [activeModes, setActiveModes] = useState<Set<string>>(
    new Set(['position', 'joint', 'orientation', 'velocity', 'metadata']),
  );
  const [weights, setWeights] = useState({
    position: 1.0,
    joint: 1.0,
    orientation: 1.0,
    velocity: 1.0,
    metadata: 1.0,
  });
  const [prefilterFeatures, setPrefilterFeatures] = useState<Set<string>>(
    new Set(['']),
  );
  const [stage2Active, setStage2Active] = useState(false);
  const [dtwMode, setDtwMode] = useState<'position' | 'joint'>('position');

  const recentBahnIds = trajInfo ? trajInfo.map((traj) => traj.trajID) : [];

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
      position: 1.0,
      joint: 1.0,
      orientation: 1.0,
      velocity: 1.0,
      metadata: 1.0,
      modes: ['position', 'joint', 'orientation', 'velocity', 'metadata'],
    },
    shape: {
      position: 1.0,
      joint: 0.0,
      orientation: 0.0,
      velocity: 1.0,
      metadata: 0.0,
      modes: ['position', 'velocity'],
    },
    motion: {
      position: 0.0,
      joint: 1.0,
      orientation: 0.0,
      velocity: 1.0,
      metadata: 0.0,
      modes: ['joint', 'velocity'],
    },
  };

  const handleSearch = () => {
    if (id.trim() && activeModes.size > 0) {
      const activeWeights = { ...weights };
      ['position', 'joint', 'orientation', 'velocity', 'metadata']
        .filter((m) => !activeModes.has(m))
        .forEach((mode) => {
          activeWeights[mode as keyof typeof weights] = 0;
        });

      onSearch(
        id.trim(),
        limit,
        Array.from(activeModes),
        activeWeights,
        Array.from(prefilterFeatures),
        stage2Active,
        dtwMode,
      );
      setShowDropdown(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
    else if (e.key === 'Escape') setShowDropdown(false);
  };

  const handleWeightChange = (mode: string, value: number) => {
    setWeights((prev) => ({ ...prev, [mode]: value }));
  };

  const toggleMode = (mode: string) => {
    setActiveModes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(mode)) {
        if (newSet.size > 1) newSet.delete(mode);
      } else {
        newSet.add(mode);
      }
      return newSet;
    });
  };

  const togglePrefilterFeature = (feature: string) => {
    setPrefilterFeatures((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(feature)) newSet.delete(feature);
      else newSet.add(feature);
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
      metadata: preset.metadata,
    });
    setActiveModes(new Set(preset.modes));
  };

  return (
    <div className="w-full rounded-xl border border-gray-400 bg-gray-100 p-4">
      <div className="space-y-2">
        {/* ID-Eingabe */}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            placeholder="Bahn-ID eingeben..."
            value={id}
            onChange={(e) => setId(e.target.value)}
            onKeyDown={handleKeyPress}
            onFocus={() => recentBahnIds.length > 0 && setShowDropdown(true)}
            className="w-full rounded-xl bg-gray-50 p-3 text-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {showDropdown && recentBahnIds.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute inset-x-0 top-full z-10 mt-1 rounded-lg border border-gray-200 bg-white shadow-lg"
            >
              <div className="p-2">
                {recentBahnIds.map((trajId, index) => (
                  <button
                    key={trajId}
                    onClick={() => {
                      setId(trajId);
                      setShowDropdown(false);
                    }}
                    className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100"
                  >
                    <span className="font-mono">{trajId}</span>
                    <span className="text-xs text-gray-400">#{index + 1}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modi + Gewichtungen */}
        <div className="flex items-center gap-8 rounded-lg bg-white p-3 text-sm sm:flex-col lg:flex-row">
          <div>Modes:</div>
          <div className="w-fit gap-2 space-x-2">
            {['position', 'joint', 'orientation', 'velocity', 'metadata'].map(
              (mode) => (
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
              ),
            )}
          </div>
          <div className="text-sm font-medium text-gray-700">Weights:</div>
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

        {/* Preset-Buttons + Prefilter + Limit + Plots */}
        <div className="space-y-2 rounded-lg bg-white p-3">
          <div className="flex flex-col items-center gap-6 sm:flex-row">
            {/* Prefilter Features */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Features:
              </span>
              {[
                { key: 'length', label: 'Length' },
                { key: 'duration', label: 'Duration' },
                { key: 'movement_type', label: 'Mov. Type' },
                { key: 'position_3d', label: 'Position' },
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

            {/* Limit */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">K:</span>
              <input
                type="number"
                min="1"
                max="100"
                value={limit}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (val >= 1 && val <= 100) setLimit(val);
                }}
                className="w-16 rounded border border-gray-300 px-2 py-1 text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Presets */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Preset:</span>
              {(Object.keys(presets) as Array<keyof typeof presets>).map(
                (preset) => (
                  <button
                    key={preset}
                    onClick={() => applyPreset(preset)}
                    className="rounded-full bg-gray-200 px-3 py-1 text-xs text-gray-700 transition-colors hover:bg-gray-300"
                  >
                    {preset.charAt(0).toUpperCase() + preset.slice(1)}
                  </button>
                ),
              )}
            </div>

            {/* Plot Toggle */}
            <div className="ml-auto flex items-center gap-2">
              {hasResults && (
                <button
                  onClick={onTogglePlots}
                  className="rounded-full bg-gray-200 px-3 py-1 text-xs text-gray-700 transition-colors hover:bg-gray-300"
                >
                  {showPlots ? 'Hide 3D-Plots' : 'Show 3D-Plots'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Stage 2: DTW Reranking */}
        <div className="rounded-lg bg-white p-3">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">
              Stage 2 DTW:
            </span>

            {/* Toggle */}
            {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
            <button
              onClick={() => setStage2Active((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                stage2Active ? 'bg-blue-600' : 'bg-gray-300'
              }`}
              role="switch"
              aria-checked={stage2Active}
            >
              <span
                className={`inline-block size-4 rounded-full bg-white shadow transition-transform ${
                  stage2Active ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>

            {/* DTW Mode Dropdown — nur sichtbar wenn aktiv */}
            {stage2Active && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Mode:</span>
                <select
                  value={dtwMode}
                  onChange={(e) =>
                    setDtwMode(e.target.value as 'position' | 'joint')
                  }
                  className="rounded border border-gray-300 bg-white px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="position">Shape (Position)</option>
                  <option value="joint">Motion (Joints)</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="text-xs text-gray-600">
          Stage 1 (RRF Fusion)
          {stage2Active && ' → Stage 2 (DTW Reranking)'}
        </div>

        {/* Such-Button */}
        <button
          onClick={handleSearch}
          disabled={activeModes.size === 0}
          className="w-full rounded-lg py-2 font-medium text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          style={{ backgroundColor: '#003560' }}
        >
          Find similar trajectories
        </button>
      </div>
    </div>
  );
};

export default SimilaritySearch;
