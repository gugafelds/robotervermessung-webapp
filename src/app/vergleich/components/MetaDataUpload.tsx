/* eslint-disable react/button-has-type,jsx-a11y/label-has-associated-control */

'use client';

import React, { useCallback, useEffect, useState } from 'react';

import type {
  AvailableDate,
  MetadataCalculationRequest,
  MetadataStats,
} from '@/src/actions/vergleich.service';
import { MetadataService } from '@/src/actions/vergleich.service';

export const MetadataUpload: React.FC = () => {
  const [stats, setStats] = useState<MetadataStats | null>(null);
  const [availableDates, setAvailableDates] = useState<AvailableDate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState<
    'all_missing' | 'single' | 'timerange'
  >('all_missing');
  const [duplicateHandling, setDuplicateHandling] = useState<
    'replace' | 'skip'
  >('skip');
  const [bahnId, setBahnId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Funktion um aktuelle Statistiken zu laden
  const loadStats = useCallback(async () => {
    try {
      const data = await MetadataService.getStats();
      setStats(data);
    } catch (error) {
      // Fehler stillschweigend behandeln
    }
  }, []);

  // Funktion um verfügbare Tage zu laden
  const loadAvailableDates = useCallback(async () => {
    try {
      const data = await MetadataService.getAvailableDates();
      setAvailableDates(data);
    } catch (error) {
      // Fehler stillschweigend behandeln
    }
  }, []);

  // Beim ersten Laden Statistiken und Tage holen
  useEffect(() => {
    loadStats();
    loadAvailableDates();
  }, [loadStats, loadAvailableDates]);

  const handleStartUpload = useCallback(async () => {
    if (selectedMode === 'single' && !bahnId) {
      return;
    }

    if (selectedMode === 'timerange' && (!startDate || !endDate)) {
      return;
    }

    try {
      const request: MetadataCalculationRequest = {
        mode: selectedMode,
        duplicate_handling: duplicateHandling,
        batch_size: 100,
      };

      if (selectedMode === 'single') {
        request.bahn_id = bahnId;
      } else if (selectedMode === 'timerange') {
        request.start_time = `${startDate} 00:00:00`;
        request.end_time = `${endDate} 23:59:59`;
      }

      await MetadataService.calculateAndWait(request, (isRunning) => {
        setIsLoading(isRunning);
      });

      // Stats neu laden nach Abschluss
      await loadStats();
    } catch (error: any) {
      // Fehler stillschweigend behandeln
    } finally {
      setIsLoading(false);
    }
  }, [selectedMode, bahnId, startDate, endDate, duplicateHandling, loadStats]);

  return (
    <div className="mx-auto w-fit min-w-96 max-w-xl space-y-2 p-6">
      <div className="text-justify">
        <h1 className="text-xl font-bold">Metadata</h1>
        <p className="text-gray-600">Aktueller Stand der Metadaten</p>
      </div>

      {/* Status Tabelle */}
      {stats && (
        <div className="rounded-lg bg-gray-50 p-4 shadow-md">
          <table className="w-full">
            <tbody className="space-y-1">
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">
                  Gesamte Bahnen
                </td>
                <td className="py-2 text-right">
                  {stats.total_bahns.toLocaleString()}
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">
                  Mit Metadaten
                </td>
                <td className="py-2 text-right">
                  {stats.bahns_with_metadata.toLocaleString()}
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">
                  Fehlende Metadaten
                </td>
                <td className="py-2 text-right">
                  {stats.missing_metadata.toLocaleString()}
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">Abdeckung</td>
                <td className="py-2 text-right">
                  <span className="font-semibold">
                    {stats.coverage_percent}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Upload Optionen */}
      <div className="rounded-lg bg-gray-50 p-4 shadow-md">
        <h2 className="mb-4 text-lg font-semibold">Upload-Modus</h2>

        <div className="space-y-3">
          {/* Alle fehlenden Bahnen */}
          <div className="flex items-center space-x-3">
            <input
              type="radio"
              name="mode"
              value="all_missing"
              id="mode-all-missing"
              checked={selectedMode === 'all_missing'}
              onChange={(e) => setSelectedMode(e.target.value as any)}
              className="size-4"
            />
            <label htmlFor="mode-all-missing" className="font-medium">
              Alle fehlenden Bahnen
              {stats && ` (${stats.missing_metadata})`}
            </label>
          </div>

          {/* Einzelne Bahn */}
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <input
                type="radio"
                name="mode"
                value="single"
                id="mode-single"
                checked={selectedMode === 'single'}
                onChange={(e) => setSelectedMode(e.target.value as any)}
                className="size-4"
              />
              <label htmlFor="mode-single" className="font-medium">
                Bahn-ID
              </label>
            </div>
            {selectedMode === 'single' && (
              <input
                type="text"
                placeholder="(z.B. 1719408730)"
                value={bahnId}
                onChange={(e) => setBahnId(e.target.value)}
                className="ml-7 w-min rounded border px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>

          {/* Zeitraum */}
          <div className="space-y-2">
            <label
              htmlFor="mode-timerange"
              className="flex cursor-pointer items-center space-x-3"
            >
              <input
                type="radio"
                name="mode"
                value="timerange"
                id="mode-timerange"
                checked={selectedMode === 'timerange'}
                onChange={(e) => setSelectedMode(e.target.value as any)}
                className="size-4"
              />
              <span className="font-medium">Zeitraum</span>
            </label>
            {selectedMode === 'timerange' && (
              <div className="ml-7 grid grid-rows-2 gap-1">
                <div>
                  <label
                    htmlFor="start-date"
                    className="block text-sm font-medium"
                  >
                    Von
                  </label>
                  <select
                    id="start-date"
                    value={startDate}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      if (!endDate) setEndDate(e.target.value);
                    }}
                    className="w-fit rounded border bg-white px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">?</option>
                    {availableDates.map((dateInfo) => (
                      <option key={dateInfo.date} value={dateInfo.date}>
                        {dateInfo.date}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="end-date"
                    className="block text-sm font-medium"
                  >
                    Bis
                  </label>
                  <select
                    id="end-date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-fit rounded border bg-white px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">?</option>
                    {availableDates.map((dateInfo) => (
                      <option key={dateInfo.date} value={dateInfo.date}>
                        {dateInfo.date}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
          <div>Duplikaten-Handling</div>
          <div>
            <input
              type="radio"
              name="duplicate_handling"
              value="skip"
              id="dh-skip"
              checked={duplicateHandling === 'skip'}
              onChange={(e) => setDuplicateHandling(e.target.value as any)}
              className="ml-2 size-4"
            />
            <span className="ml-2 mr-4 font-medium">Skip</span>
            <input
              type="radio"
              name="duplicate_handling"
              value="replace"
              id="dh-replace"
              checked={duplicateHandling === 'replace'}
              onChange={(e) => setDuplicateHandling(e.target.value as any)}
              className="ml-2 size-4"
            />
            <span className="ml-2 font-medium">Überschreiben</span>
          </div>
        </div>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStartUpload}
        disabled={isLoading}
        className={`w-full rounded-lg px-4 py-3 font-medium text-white transition-colors ${
          isLoading ? 'cursor-not-allowed bg-gray-400' : 'hover:bg-gray-950'
        }`}
        style={!isLoading ? { backgroundColor: '#003560' } : undefined}
      >
        {isLoading ? 'Berechnung läuft...' : 'Metadaten berechnen'}
      </button>
    </div>
  );
};

export default MetadataUpload;
