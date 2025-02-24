/* eslint-disable */
'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { formatNumber } from '@/src/lib/functions';
import type { DFDInfo, EAInfo, DTWInfo, SIDTWInfo } from '@/types/auswertung.types';
import { Typography } from '@/src/components/Typography';

interface SegmentOption {
  label: string;
  value: string;
}

export const MetrikenPanel: React.FC<{
  EAInfo: EAInfo[];
  DFDInfo: DFDInfo[];
  DTWInfo: DTWInfo[];
  SIDTWInfo: SIDTWInfo[];
}> = ({ EAInfo, DFDInfo, DTWInfo, SIDTWInfo }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState<string>('total');
  const [segmentOptions, setSegmentOptions] = useState<SegmentOption[]>([]);

  // Get all available segments and create dropdown options
  useEffect(() => {
    const getAllSegmentNumbers = (analyses: any[]) => {
      return Array.from(
        analyses
          .filter((a) => a.bahnID !== a.segmentID)
          .map((a) => parseInt(a.segmentID.split('_')[1], 10))
          .reduce((acc, curr) => acc.add(curr), new Set<number>()),
      ).sort((a, b) => a - b);
    };

    const allSegments = [
      ...getAllSegmentNumbers(EAInfo),
      ...getAllSegmentNumbers(DFDInfo),
      ...getAllSegmentNumbers(DTWInfo),
      ...getAllSegmentNumbers(SIDTWInfo),
    ];

    const options: SegmentOption[] = [
      { label: 'Gesamtmessung', value: 'total' },
      ...allSegments
        .filter((value, index, self) => self.indexOf(value) === index)
        .map((segNum) => ({
          label: `Segment ${segNum}`,
          value: `segment_${segNum}`,
        })),
    ];

    setSegmentOptions(options);
  }, [EAInfo, DFDInfo, DTWInfo, SIDTWInfo]);

  // Calculate metrics for selected segment
  const calculateMetrics = (analyses: any[], prefix: string) => {
    if (analyses.length === 0) return null;

    const filteredAnalyses = analyses.filter((analysis) => {
      if (selectedSegment === 'total') {
        return analysis.bahnID === analysis.segmentID;
      }
      const segmentNum = selectedSegment.split('_')[1];
      return analysis.segmentID === `${analysis.bahnID}_${segmentNum}`;
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

  const eaMetrics = calculateMetrics(EAInfo, 'EA');
  const dfdMetrics = calculateMetrics(DFDInfo, 'DFD');
  const dtwMetrics = calculateMetrics(DTWInfo, 'DTW');
  const sidtwMetrics = calculateMetrics(SIDTWInfo, 'SIDTW');

  return (
    <div className="mb-6 rounded-lg border w-1/2 bg-white p-6 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <Typography as="h2">Position</Typography>

        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
          >
            {segmentOptions.find((opt) => opt.value === selectedSegment)
              ?.label || 'Auswählen'}
            <ChevronDownIcon className="size-4" />
          </button>

          {showDropdown && (
            <div className="absolute right-0 top-10 z-10 w-48 rounded-md border bg-white shadow-lg">
              {segmentOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    setSelectedSegment(option.value);
                    setShowDropdown(false);
                  }}
                  className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                >
                  {option.label}
                </button>
              ))}
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

            </tr>
          </thead>
          <tbody>
            {eaMetrics && (
              <tr className="border-b">
                <td className="py-3 text-primary">EA</td>
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
              </tr>
            )}
            {dtwMetrics && (
              <tr className="border-b">
                <td className="py-3 text-primary">DTW</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dtwMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dtwMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dtwMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(dtwMetrics.std)}
                </td>
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

              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
