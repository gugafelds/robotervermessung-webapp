'use client';

import React, { useState } from 'react';

interface MetadataStats {
  total_bahns: number;
  bahns_with_metadata: number;
  missing_metadata: number;
  coverage_percent: number;
}

interface AvailableDate {
  date: string;
  display_date: string;
  bahn_count: number;
  earliest_time: string;
  latest_time: string;
}

export const MetadataUpload: React.FC = () => {
  const [stats, setStats] = useState<MetadataStats | null>(null);
  const [availableDates, setAvailableDates] = useState<AvailableDate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState<
    'all_missing' | 'single' | 'timerange'
  >('all_missing');
  const [bahnId, setBahnId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Funktion um aktuelle Statistiken zu laden
  const loadStats = async () => {
    try {
      const response = await fetch('/api/vergleich/metadata-stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Fehler beim Laden der Statistiken:', error);
    }
  };

  // Funktion um verfügbare Tage zu laden
  const loadAvailableDates = async () => {
    try {
      const response = await fetch('/api/vergleich/available-dates');
      if (response.ok) {
        const data = await response.json();
        setAvailableDates(data.available_dates);
      }
    } catch (error) {
      console.error('Fehler beim Laden der verfügbaren Tage:', error);
    }
  };

  // Beim ersten Laden Statistiken und Tage holen
  React.useEffect(() => {
    loadStats();
    loadAvailableDates();
  }, []);

  const handleStartUpload = async () => {
    if (selectedMode === 'single' && !bahnId) {
      alert('Bitte geben Sie eine Bahn-ID ein');
      return;
    }

    if (selectedMode === 'timerange' && (!startDate || !endDate)) {
      alert('Bitte wählen Sie Start- und End-Datum');
      return;
    }

    setIsLoading(true);

    try {
      const requestBody: any = {
        mode: selectedMode,
        duplicate_handling: 'skip',
        batch_size: 10,
      };

      if (selectedMode === 'single') {
        requestBody.bahn_id = bahnId;
      } else if (selectedMode === 'timerange') {
        // Verwende die recording_dates direkt
        requestBody.start_time = `${startDate} 00:00:00`;
        requestBody.end_time = `${endDate} 23:59:59`;
      }

      const response = await fetch('/api/vergleich/calculate-metadata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Upload gestartet! Task ID: ${result.task_id}`);
        // TODO: Hier könnten wir später zu einer Progress-Seite weiterleiten
      } else {
        const error = await response.json();
        alert(`Fehler: ${error.detail}`);
      }
    } catch (error) {
      console.error('Fehler:', error);
      alert('Unbekannter Fehler aufgetreten');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="text-center">
        <h1 className="mb-2 text-3xl font-bold">Metadata Upload</h1>
        <p className="text-gray-600">Berechne und lade Bahn-Metadaten hoch</p>
      </div>

      {/* Aktuelle Statistiken */}
      {stats && (
        <div className="rounded-lg bg-white p-6 shadow-md">
          <h2 className="mb-4 text-xl font-semibold">Aktueller Status</h2>
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="rounded bg-blue-50 p-4">
              <div className="text-2xl font-bold text-blue-600">
                {stats.total_bahns}
              </div>
              <div className="text-sm text-gray-600">Gesamt Bahnen</div>
            </div>
            <div className="rounded bg-green-50 p-4">
              <div className="text-2xl font-bold text-green-600">
                {stats.bahns_with_metadata}
              </div>
              <div className="text-sm text-gray-600">Mit Metadaten</div>
            </div>
            <div className="rounded bg-orange-50 p-4">
              <div className="text-2xl font-bold text-orange-600">
                {stats.missing_metadata}
              </div>
              <div className="text-sm text-gray-600">Fehlende Metadaten</div>
            </div>
            <div className="rounded bg-purple-50 p-4">
              <div className="text-2xl font-bold text-purple-600">
                {stats.coverage_percent}%
              </div>
              <div className="text-sm text-gray-600">Abdeckung</div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Optionen */}
      <div className="rounded-lg bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold">Upload Modus wählen</h2>

        <div className="space-y-4">
          {/* Alle fehlenden Bahnen */}
          <label className="flex cursor-pointer items-center space-x-3 rounded border p-4 hover:bg-gray-50">
            <input
              type="radio"
              name="mode"
              value="all_missing"
              checked={selectedMode === 'all_missing'}
              onChange={(e) => setSelectedMode(e.target.value as any)}
              className="size-4"
            />
            <div>
              <div className="font-medium">Alle fehlenden Bahnen</div>
              <div className="text-sm text-gray-600">
                Verarbeitet alle Bahnen, die noch keine Metadaten haben
                {stats && ` (${stats.missing_metadata} Bahnen)`}
              </div>
            </div>
          </label>

          {/* Einzelne Bahn */}
          <label className="flex cursor-pointer items-center space-x-3 rounded border p-4 hover:bg-gray-50">
            <input
              type="radio"
              name="mode"
              value="single"
              checked={selectedMode === 'single'}
              onChange={(e) => setSelectedMode(e.target.value as any)}
              className="size-4"
            />
            <div className="flex-1">
              <div className="font-medium">Einzelne Bahn</div>
              <div className="text-sm text-gray-600">
                Verarbeitet nur eine spezifische Bahn-ID
              </div>
              {selectedMode === 'single' && (
                <input
                  type="text"
                  placeholder="Bahn-ID eingeben (z.B. 1719408730)"
                  value={bahnId}
                  onChange={(e) => setBahnId(e.target.value)}
                  className="mt-2 w-full rounded border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}
            </div>
          </label>

          {/* Zeitraum */}
          <label className="flex cursor-pointer items-center space-x-3 rounded border p-4 hover:bg-gray-50">
            <input
              type="radio"
              name="mode"
              value="timerange"
              checked={selectedMode === 'timerange'}
              onChange={(e) => setSelectedMode(e.target.value as any)}
              className="size-4"
            />
            <div className="flex-1">
              <div className="font-medium">Zeitraum</div>
              <div className="text-sm text-gray-600">
                Verarbeitet Bahnen in einem bestimmten Zeitraum
              </div>
              {selectedMode === 'timerange' && (
                <div className="mt-3 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium">
                        Start-Datum
                      </label>
                      <select
                        value={startDate}
                        onChange={(e) => {
                          setStartDate(e.target.value);
                          if (!endDate) setEndDate(e.target.value); // Auto-set end date wenn leer
                        }}
                        className="w-full rounded border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">-- Tag wählen --</option>
                        {availableDates.map((dateInfo) => (
                          <option key={dateInfo.date} value={dateInfo.date}>
                            {dateInfo.date}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium">
                        End-Datum
                      </label>
                      <select
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="w-full rounded border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">-- Tag wählen --</option>
                        {availableDates.map((dateInfo) => (
                          <option key={dateInfo.date} value={dateInfo.date}>
                            {dateInfo.date}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </label>
        </div>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStartUpload}
        disabled={isLoading}
        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
      >
        {isLoading ? 'Starte Upload...' : 'Metadaten-Upload starten'}
      </button>

      {/* Info Box */}
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
        <h3 className="mb-2 font-medium text-yellow-800">Hinweis</h3>
        <ul className="space-y-1 text-sm text-yellow-700">
          <li>
            • Der Upload läuft im Hintergrund und kann einige Minuten dauern
          </li>
          <li>• Existierende Metadaten werden übersprungen</li>
          <li>• Sie erhalten eine Task-ID zur Verfolgung des Fortschritts</li>
        </ul>
      </div>
    </div>
  );
};

export default MetadataUpload;
