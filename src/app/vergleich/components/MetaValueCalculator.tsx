/* eslint-disable react/button-has-type */

'use client';

import React, { useCallback, useEffect, useState } from 'react';

import type { MetaValuesStatus } from '@/src/actions/vergleich.service';
import { MetaValuesService } from '@/src/actions/vergleich.service';

export const MetaValuesCalculator: React.FC = () => {
  const [status, setStatus] = useState<MetaValuesStatus | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  // Status laden
  const loadStatus = useCallback(async () => {
    const data = await MetaValuesService.getStatus();
    setStatus(data);
  }, []);

  // Beim ersten Laden Status holen
  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  // Meta-Values berechnen
  const handleUpdate = useCallback(async () => {
    try {
      await MetaValuesService.calculateAndWait((isRunning) => {
        setIsUpdating(isRunning);
      });

      // Status neu laden nach Abschluss
      await loadStatus();
    } catch (error: any) {
      // Fehler stillschweigend behandeln
    } finally {
      setIsUpdating(false);
    }
  }, [loadStatus]);

  return (
    <div className="mx-auto w-fit min-w-96 max-w-xl space-y-2 p-6">
      <div className="text-justify">
        <h1 className="mb-2 text-xl font-bold">Metavalues</h1>
        <p className="text-gray-600">Aktueller Stand der Meta-Values</p>
      </div>

      {/* Status Tabelle */}
      {status && (
        <div className="rounded-lg bg-gray-50 p-4 shadow-md">
          <table className="w-full">
            <tbody className="space-y-2">
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">
                  Gesamte Einträge
                </td>
                <td className="py-2 text-right">
                  {status.total_rows.toLocaleString()}
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">
                  Mit Meta-Values
                </td>
                <td className="py-2 text-right">
                  {status.meta_values_count.toLocaleString()}
                </td>
              </tr>
              <tr className="border-b">
                <td className="py-2 font-medium text-gray-700">Abdeckung</td>
                <td className="py-2 text-right">
                  <span className="font-semibold">
                    {status.completion_rate}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Update Button */}
      <button
        onClick={handleUpdate}
        disabled={isUpdating}
        className={`w-full rounded-lg px-4 py-3 font-medium text-white transition-colors ${
          isUpdating ? 'cursor-not-allowed bg-gray-400' : 'hover:bg-gray-950'
        }`}
        style={!isUpdating ? { backgroundColor: '#003560' } : undefined}
      >
        {isUpdating ? 'Berechnung läuft...' : 'Meta-Values aktualisieren'}
      </button>
    </div>
  );
};

export default MetaValuesCalculator;
