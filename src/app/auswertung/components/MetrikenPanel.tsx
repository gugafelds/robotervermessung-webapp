'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import * as Slider from '@radix-ui/react-slider';
import React, { useEffect, useState } from 'react';

import { formatNumber } from '@/src/lib/functions';
import type { DFDInfo, EAInfo, SIDTWInfo } from '@/types/auswertung.types';

interface SegmentRange {
  min: number;
  max: number;
}

export const MetrikenPanel: React.FC<{
  EAInfo: EAInfo[];
  DFDInfo: DFDInfo[];
  SIDTWInfo: SIDTWInfo[];
}> = ({ EAInfo, DFDInfo, SIDTWInfo }) => {
  // Finde das Minimum und Maximum der verfügbaren Segmente
  const getAllSegmentNumbers = (analyses: any[]) => {
    return analyses
      .filter((a) => a.bahnID !== a.segmentID) // Filtere zuerst die Zeilen mit gleicher ID
      .map((a) => parseInt(a.segmentID.split('_')[1], 10));
  };

  const [segmentRange, setSegmentRange] = useState<SegmentRange>({
    min: 0,
    max: 0,
  });
  const [selectedRange, setSelectedRange] = useState<SegmentRange>({
    min: 0,
    max: 0,
  });
  const [showSelector, setShowSelector] = useState(false);

  // Initialisiere den Bereich der verfügbaren Segmente
  useEffect(() => {
    const allSegments = [
      ...getAllSegmentNumbers(EAInfo),
      ...getAllSegmentNumbers(DFDInfo),
      ...getAllSegmentNumbers(SIDTWInfo),
    ];

    if (allSegments.length > 0) {
      const minSegment = Math.min(...allSegments);
      const maxSegment = Math.max(...allSegments);
      setSegmentRange({ min: minSegment, max: maxSegment });
      setSelectedRange({ min: minSegment, max: maxSegment });
    }
  }, [EAInfo, DFDInfo, SIDTWInfo]);

  // Funktion zum Berechnen der Durchschnittswerte pro Metrik im ausgewählten Bereich
  const calculateMetricAverages = (analyses: any[], prefix: string) => {
    if (analyses.length === 0) return null;

    const filteredAnalyses = analyses.filter((analysis) => {
      const segmentNum = parseInt(analysis.segmentID.split('_')[1], 10);
      return segmentNum >= selectedRange.min && segmentNum <= selectedRange.max;
    });

    if (filteredAnalyses.length === 0) return null;

    const { evaluation } = analyses[0];
    return {
      min:
        filteredAnalyses.reduce(
          (acc, curr) => acc + curr[`${prefix}MinDistance`],
          0,
        ) / filteredAnalyses.length,
      avg:
        filteredAnalyses.reduce(
          (acc, curr) => acc + curr[`${prefix}AvgDistance`],
          0,
        ) / filteredAnalyses.length,
      max:
        filteredAnalyses.reduce(
          (acc, curr) => acc + curr[`${prefix}MaxDistance`],
          0,
        ) / filteredAnalyses.length,
      std:
        filteredAnalyses.reduce(
          (acc, curr) => acc + curr[`${prefix}StdDeviation`],
          0,
        ) / filteredAnalyses.length,
      evaluation,
    };
  };

  const eaMetrics = calculateMetricAverages(EAInfo, 'EA');
  const dfdMetrics = calculateMetricAverages(DFDInfo, 'DFD');
  const sidtwMetrics = calculateMetricAverages(SIDTWInfo, 'SIDTW');

  return (
    <div className="mb-6 rounded-lg border bg-white p-6 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-primary">
          Auswertungsmetriken (segmentweise)
        </h3>

        <div className="relative">
          {/* eslint-disable-next-line react/button-has-type */}
          <button
            onClick={() => setShowSelector(!showSelector)}
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
          >
            {selectedRange.min === segmentRange.min &&
            selectedRange.max === segmentRange.max
              ? 'Alle Segmente'
              : `Segment ${selectedRange.min} - ${selectedRange.max}`}
            <ChevronDownIcon className="size-4" />
          </button>

          {showSelector && (
            <div className="absolute right-0 top-10 z-10 w-80 rounded-md border bg-white p-4 shadow-lg">
              <div className="space-y-4">
                <div className="space-y-2">
                  {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                  <label className="text-sm font-medium text-gray-600">
                    Segmentbereich:
                  </label>
                  <div className="px-2">
                    <Slider.Root
                      className="relative flex h-5 w-full touch-none items-center"
                      value={[selectedRange.min, selectedRange.max]}
                      max={segmentRange.max}
                      min={segmentRange.min}
                      step={1}
                      onValueChange={([min, max]) => {
                        setSelectedRange({ min, max });
                      }}
                    >
                      <Slider.Track className="relative h-1 w-full grow rounded-full bg-gray-200">
                        <Slider.Range className="absolute h-full rounded-full bg-primary" />
                      </Slider.Track>
                      <Slider.Thumb
                        /* eslint-disable-next-line tailwindcss/migration-from-tailwind-2 */
                        className="block size-4 rounded-full border border-primary bg-white focus:outline-none focus-visible:ring focus-visible:ring-primary focus-visible:ring-opacity-75"
                        aria-label="Minimum segment"
                      />
                      <Slider.Thumb
                        /* eslint-disable-next-line tailwindcss/migration-from-tailwind-2 */
                        className="block size-4 rounded-full border border-primary bg-white focus:outline-none focus-visible:ring focus-visible:ring-primary focus-visible:ring-opacity-75"
                        aria-label="Maximum segment"
                      />
                    </Slider.Root>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>{selectedRange.min}</span>
                    <span>{selectedRange.max}</span>
                  </div>
                </div>

                {/* eslint-disable-next-line react/button-has-type */}
                <button
                  onClick={() => {
                    setSelectedRange(segmentRange);
                    setShowSelector(false);
                  }}
                  className="w-full rounded-md bg-gray-100 px-3 py-1 text-sm text-gray-600 hover:bg-gray-200"
                >
                  Alle Segmente
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="pb-2 text-left font-semibold text-primary">
                Methode
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Min.
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Durchschnitt
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Max.
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Std. Abw.
              </th>
              <th className="pb-2 text-left font-semibold text-primary">
                Metriken
              </th>
            </tr>
          </thead>
          <tbody>
            {eaMetrics && (
              <tr className="border-b">
                <td className="py-3 text-primary">Euklidischer Abstand</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(eaMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(eaMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(eaMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(eaMetrics.std)}
                </td>
                <td className="py-3 text-primary">{eaMetrics.evaluation}</td>
              </tr>
            )}
            {sidtwMetrics && (
              <tr className="border-b">
                <td className="py-3 text-primary">SIDTW</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(sidtwMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(sidtwMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(sidtwMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(sidtwMetrics.std)}
                </td>
                <td className="py-3 text-primary">{sidtwMetrics.evaluation}</td>
              </tr>
            )}
            {dfdMetrics && (
              <tr className="border-b">
                <td className="py-3 text-primary">DFD</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dfdMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dfdMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dfdMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dfdMetrics.std)}
                </td>
                <td className="py-3 text-primary">{dfdMetrics.evaluation}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
