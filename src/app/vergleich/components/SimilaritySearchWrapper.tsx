'use client';

import React, { useState } from 'react';

import { SimilarityService } from '@/src/actions/vergleich.service';
import type { BahnInfo } from '@/types/bewegungsdaten.types';
import type { SimilarityResult } from '@/types/similarity.types';

import SimilarityResults from './SimilarityResults';
import SimilaritySearch from './SimilaritySearch';

interface SimilaritySearchWrapperProps {
  bahnInfo?: BahnInfo[];
}

interface TargetFeatures {
  segment_id: string;
  bahn_id: string;
  duration?: number;
  length?: number;
  median_twist_ist?: number;
  median_acceleration_ist?: number;
  movement_type?: string;
}

interface SegmentGroup {
  target_segment: string;
  target_segment_features?: TargetFeatures;
  results: SimilarityResult[];
}

export default function SimilaritySearchWrapper({
  bahnInfo,
}: SimilaritySearchWrapperProps) {
  const [bahnResults, setBahnResults] = useState<SimilarityResult[]>([]);
  const [targetBahnFeatures, setTargetBahnFeatures] = useState<
    TargetFeatures | undefined
  >();
  const [segmentGroups, setSegmentGroups] = useState<SegmentGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [originalId, setOriginalId] = useState('');

  const handleSearch = async (
    id: string,
    limit: number,
    modes: string[],
    weights: { joint: number; position: number; orientation: number },
  ) => {
    setIsLoading(true);
    setError('');
    setOriginalId(id);
    setBahnResults([]);
    setTargetBahnFeatures(undefined);
    setSegmentGroups([]);

    try {
      await SimilarityService.searchSimilarityEmbedding(
        id,
        { modes, weights, limit },
        {
          onBahnenFound: (results, targetFeatures) => {
            setBahnResults(results);
            setTargetBahnFeatures(targetFeatures);
            setIsLoading(false);
          },
          onSegmentsFound: (groups) => {
            setSegmentGroups(groups);
          },
          onError: (errorMsg) => {
            setError(`Fehler bei der Suche: ${errorMsg}`);
            setIsLoading(false);
          },
        },
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`Fehler bei der Suche: ${errorMessage}`);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-fullscreen">
      <div className="flex flex-col w-full space-y-4 overflow-y-auto p-4">
        <SimilaritySearch onSearch={handleSearch} bahnInfo={bahnInfo} />
        <SimilarityResults
          results={bahnResults}
          isLoading={isLoading}
          error={error}
          originalId={originalId}
          targetBahnFeatures={targetBahnFeatures}
          segmentGroups={segmentGroups}
        />
      </div>
    </div>
  );
}
