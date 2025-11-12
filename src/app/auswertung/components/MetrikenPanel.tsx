/* eslint-disable react/button-has-type,no-console */

'use client';

import { ChevronDownIcon } from '@heroicons/react/24/outline';
import React, { useEffect, useState } from 'react';

import { getAuswertungInfoById } from '@/src/actions/auswertung.service';
import { Typography } from '@/src/components/Typography';
import { formatNumber } from '@/src/lib/functions';
import type {
  DFDInfo,
  DTWInfo,
  EAInfo,
  QADInfo,
  QDTWInfo,
  SIDTWInfo,
} from '@/types/auswertung.types';

interface SegmentOption {
  label: string;
  value: string;
}

// Erweiterte Props Interface mit synchronisierter Segmentauswahl
interface MetrikenPanelProps {
  bahnId: string;
  selectedSegment: string; // Neu: von Parent kontrolliert
  onSegmentChange: (segment: string) => void; // Neu: Callback für Änderungen
}

export const MetrikenPanel: React.FC<MetrikenPanelProps> = ({
  bahnId,
  selectedSegment, // Verwendet den State vom Parent
  onSegmentChange, // Verwendet den Callback vom Parent
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  // selectedSegment State entfernt - wird jetzt als Prop übergeben
  const [segmentOptions, setSegmentOptions] = useState<SegmentOption[]>([]);

  const [eaInfo, setEaInfo] = useState<EAInfo[]>([]);
  const [dfdInfo, setDfdInfo] = useState<DFDInfo[]>([]);
  const [dtwInfo, setDtwInfo] = useState<DTWInfo[]>([]);
  const [sidtwInfo, setSidtwInfo] = useState<SIDTWInfo[]>([]);
  const [qadInfo, setQadInfo] = useState<QADInfo[]>([]);
  const [qdtwInfo, setQdtwInfo] = useState<QDTWInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch Auswertung info when component mounts or bahnId changes
  useEffect(() => {
    const fetchAuswertungInfo = async () => {
      if (!bahnId) return;

      setIsLoading(true);
      try {
        const infoResult = await getAuswertungInfoById(bahnId);

        setEaInfo(infoResult.info_euclidean || []);
        setDfdInfo(infoResult.info_dfd || []);
        setDtwInfo(infoResult.info_dtw || []);
        setSidtwInfo(infoResult.info_sidtw || []);
        setQadInfo(infoResult.info_qad || []);
        setQdtwInfo(infoResult.info_qdtw || []);
      } catch (error) {
        console.error('Fehler beim Laden der Auswertungsinformationen:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAuswertungInfo();
  }, [bahnId]);

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
      ...getAllSegmentNumbers(eaInfo),
      ...getAllSegmentNumbers(dfdInfo),
      ...getAllSegmentNumbers(dtwInfo),
      ...getAllSegmentNumbers(sidtwInfo),
      ...getAllSegmentNumbers(qadInfo),
      ...getAllSegmentNumbers(qdtwInfo),
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
  }, [eaInfo, dfdInfo, dtwInfo, sidtwInfo, qadInfo, qdtwInfo]);

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

  const eaMetrics = calculateMetrics(eaInfo, 'EA');
  const dfdMetrics = calculateMetrics(dfdInfo, 'DFD');
  const dtwMetrics = calculateMetrics(dtwInfo, 'DTW');
  const sidtwMetrics = calculateMetrics(sidtwInfo, 'SIDTW');
  const qadMetrics = calculateMetrics(qadInfo, 'QAD');
  const qdtwMetrics = calculateMetrics(qdtwInfo, 'QDTW');

  if (isLoading) {
    return (
      <div className="m-4 rounded-lg border border-gray-500 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-center">
          <div className="size-5 animate-spin rounded-full border-b-2 border-gray-900" />
          <span className="ml-2">Lade Metriken...</span>
        </div>
      </div>
    );
  }

  if (!eaMetrics && !dfdMetrics && !dtwMetrics && !sidtwMetrics) {
    return (
      <div className="m-4 rounded-lg border border-gray-500 bg-gray-200 p-6 text-center text-gray-500">
        Keine Metriken verfügbar
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
              ?.label || 'Auswählen'}
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
          </thead>
          <tbody>
            {eaMetrics && (
              <tr className="border-t">
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
              <tr className="border-t">
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
            )}
            {dfdMetrics && (
              <tr className="border-t">
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

      {qadMetrics && (
        <Typography as="h2" className="mt-4">
          Orientierung
        </Typography>
      )}

      {qadMetrics && (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
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
            </thead>
            <tbody>
              {qadMetrics && (
                <tr className="border-b">
                  <td className="py-3 text-primary">QAD</td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qadMetrics.min)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qadMetrics.avg)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qadMetrics.max)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qadMetrics.std)}
                  </td>
                </tr>
              )}
              {qdtwMetrics && (
                <tr className="border-b">
                  <td className="py-3 text-primary">QDTW</td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qdtwMetrics.min)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qdtwMetrics.avg)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qdtwMetrics.max)}
                  </td>
                  <td className="py-3 text-center text-primary">
                    {formatNumber(qdtwMetrics.std)}
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
