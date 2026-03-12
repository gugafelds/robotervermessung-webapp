/* eslint-disable react/button-has-type,no-console */

'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { getEvaluationInfoById } from '@/src/actions/evaluation.service';
import { Typography } from '@/src/components/Typography';
import { formatNumber } from '@/src/lib/functions';
import type {
  EDInfo,
  GDInfo,
  QDTWInfo,
  SIDTWInfo,
} from '@/types/evaluation.types';

interface SegmentOption {
  label: string;
  value: string;
}

// Erweiterte Props Interface mit synchronisierter Segmentauswahl
interface MetrikenPanelProps {
  trajID: string;
  selectedSegment: string; // Neu: von Parent kontrolliert
  onSegmentChange: (segment: string) => void; // Neu: Callback für Änderungen
}

export const MetricsPanel: React.FC<MetrikenPanelProps> = ({
  trajID,
  selectedSegment, // Verwendet den State vom Parent
  onSegmentChange, // Verwendet den Callback vom Parent
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  // selectedSegment State entfernt - wird jetzt als Prop übergeben
  const [segmentOptions, setSegmentOptions] = useState<SegmentOption[]>([]);

  const [EDInfo, setEDInfo] = useState<EDInfo[]>([]);
  const [SIDTWInfo, setSIDTWInfo] = useState<SIDTWInfo[]>([]);
  const [GDInfo, setGDInfo] = useState<GDInfo[]>([]);
  const [QDTWInfo, setQdtwInfo] = useState<QDTWInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch Auswertung info when component mounts or trajID changes
  useEffect(() => {
    const fetchAuswertungInfo = async () => {
      if (!trajID) return;

      setIsLoading(true);
      try {
        const infoResult = await getEvaluationInfoById(trajID);

        setEDInfo(infoResult.EDInfo || []);
        setSIDTWInfo(infoResult.SIDTWInfo || []);
        setGDInfo(infoResult.GDInfo || []);
        setQdtwInfo(infoResult.QDTWInfo || []);
      } catch (error) {
        console.error('Fehler beim Laden der Auswertungsinformationen:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAuswertungInfo();
  }, [trajID]);

  // Get all available segments and create dropdown options
  useEffect(() => {
    const getAllSegmentNumbers = (analyses: any[]) => {
      return Array.from(
        analyses
          .filter((a) => a.trajID !== a.segID)
          .map((a) => parseInt(a.segID.split('_')[1], 10))
          .reduce((acc, curr) => acc.add(curr), new Set<number>()),
      ).sort((a, b) => a - b);
    };

    const allSegments = [
      ...getAllSegmentNumbers(EDInfo),
      ...getAllSegmentNumbers(SIDTWInfo),
      ...getAllSegmentNumbers(GDInfo),
      ...getAllSegmentNumbers(QDTWInfo),
    ];

    const options: SegmentOption[] = [
      { label: 'Trajectory', value: 'total' },
      ...allSegments
        .filter((value, index, self) => self.indexOf(value) === index)
        .map((segNum) => ({
          label: `Segment ${segNum}`,
          value: `segment_${segNum}`,
        })),
    ];

    setSegmentOptions(options);
  }, [EDInfo, SIDTWInfo, GDInfo, QDTWInfo]);

  // Handler für Segmentauswahl - verwendet den Parent Callback
  const handleSegmentSelect = (segment: string) => {
    onSegmentChange(segment);
    setShowDropdown(false);
  };

  // Calculate metrics for selected segment
  const calculateMetrics = (analyses: any[], prefix: string) => {
    if (analyses.length === 0) return null;

    const filteredAnalyses = analyses.filter((analysis) => {
      if (selectedSegment === 'total') {
        return analysis.trajID === analysis.segID;
      }
      const segmentNum = selectedSegment.split('_')[1];
      return analysis.segID === `${analysis.trajID}_${segmentNum}`;
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

  const EDMetrics = calculateMetrics(EDInfo, 'ED');
  const SIDTWMetrics = calculateMetrics(SIDTWInfo, 'SIDTW');
  const GDMetrics = calculateMetrics(GDInfo, 'GD');
  const QDTWMetrics = calculateMetrics(QDTWInfo, 'QDTW');

  if (isLoading) {
    return (
      <div className="m-4 rounded-lg border border-gray-500 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-center">
          <div className="size-5 animate-spin rounded-full border-b-2 border-gray-900" />
          <span className="ml-2">Loading metrics...</span>
        </div>
      </div>
    );
  }

  if (!EDMetrics && !SIDTWMetrics) {
    return (
      <div className="m-4 rounded-lg border border-gray-500 bg-gray-200 p-6 text-center text-gray-500">
        No metrics available for this trajectory.
      </div>
    );
  }

  return (
    <div className="mx-4 h-fit rounded-lg border border-gray-500 bg-white p-6">
      <div className="mb-3 flex items-center justify-between">
        <Typography as="h2">Position</Typography>

        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1 text-sm hover:bg-gray-50"
          >
            {segmentOptions.find((opt) => opt.value === selectedSegment)
              ?.label || 'Select'}
            <ChevronDownIcon className="size-4" />
          </button>

          {showDropdown && (
            <div className="absolute right-0 top-10 z-10 w-48 rounded-md border  bg-white shadow-lg">
              {segmentOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleSegmentSelect(option.value)}
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
            <th className="pb-2 text-left font-semibold text-primary">
              Method
            </th>
            <th className="pb-2 text-center font-semibold text-primary">
              Min.
            </th>
            <th className="pb-2 text-center font-semibold text-primary">
              Avg.
            </th>
            <th className="pb-2 text-center font-semibold text-primary">
              Max.
            </th>
            <th className="pb-2 text-center font-semibold text-primary">
              Std.
            </th>
          </thead>
          <tbody>
            {EDMetrics && (
              <tr className="border-t">
                <td className="py-3 text-primary">ED</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(EDMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(EDMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(EDMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(EDMetrics.std)}
                </td>
              </tr>
            )}
            {SIDTWMetrics && (
              <tr className="border-t">
                <td className="py-3 text-primary">SIDTW</td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(SIDTWMetrics.min)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(SIDTWMetrics.avg)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(SIDTWMetrics.max)}
                </td>
                <td className="py-3 text-center text-primary">
                  {formatNumber(SIDTWMetrics.std)}
                </td>
              </tr>
            )}
            {/*dtwMetrics && (
              <tr className="border-t">
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
            )*/}
          </tbody>
        </table>
      </div>

      {GDMetrics && (
        <Typography as="h2" className="mt-4">
          Orientation
        </Typography>
      )}

      {GDMetrics && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <th className="pb-2 text-left font-semibold text-primary">
                Method
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Min.
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Avg.
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Max.
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Std.
              </th>
            </thead>
            <tbody>
              {GDMetrics && (
                <tr className="border-b">
                  <td className="py-3 text-primary">QAD</td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(GDMetrics.min)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(GDMetrics.avg)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(GDMetrics.max)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(GDMetrics.std)}
                  </td>
                </tr>
              )}
              {QDTWMetrics && (
                <tr className="border-b">
                  <td className="py-3 text-primary">QDTW</td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(QDTWMetrics.min)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(QDTWMetrics.avg)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(QDTWMetrics.max)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(QDTWMetrics.std)}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
