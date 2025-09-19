'use client';

import React, { useState } from 'react';

import type {
  SimilarityResult,
  SimilaritySearchParams,
} from '@/src/actions/vergleich.service';
import { SimilarityService } from '@/src/actions/vergleich.service';
import type { BahnInfo } from '@/types/bewegungsdaten.types';

import SimilarityResults from './SimilarityResults';
import SimilaritySearch from './SimilaritySearch';

interface SimilaritySearchWrapperProps {
  bahnInfo?: BahnInfo[];
}

export default function SimilaritySearchWrapper({
  bahnInfo,
}: SimilaritySearchWrapperProps) {
  const [results, setResults] = useState<SimilarityResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [originalId, setOriginalId] = useState('');
  const [isSegmentTaskRunning, setIsSegmentTaskRunning] = useState(false);
  const [segmentProgress, setSegmentProgress] = useState('');

  const handleSearch = async (
    id: string,
    bahnLimit: number,
    segmentLimit: number,
    weights: Record<string, number>,
  ) => {
    setIsLoading(true);
    setError('');
    setOriginalId(id);
    setResults([]);

    const params: SimilaritySearchParams = {
      bahnLimit,
      segmentLimit,
      weights: {
        duration: weights.duration,
        weight: weights.weight,
        length: weights.length,
        movement_type: weights.movement_type,
        direction_x: weights.direction_x,
        direction_y: weights.direction_y,
        direction_z: weights.direction_z,
      },
    };

    try {
      await SimilarityService.searchSimilarity(id, params, {
        onBahnenFound: (bahnResults) => {
          setResults(bahnResults);
          setIsLoading(false);
        },
        onSegmentProgress: (progress) => {
          setIsSegmentTaskRunning(true);
          setSegmentProgress(progress);
        },
        onSegmentsFound: (segmentResults) => {
          setResults((prev) => [...prev, ...segmentResults]);
          setIsSegmentTaskRunning(false);
          setSegmentProgress('');
        },
        onError: (errorMsg) => {
          setError(`Fehler bei der Suche: ${errorMsg}`);
          setIsLoading(false);
          setIsSegmentTaskRunning(false);
        },
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`Fehler bei der Suche: ${errorMessage}`);
      setIsLoading(false);
      setIsSegmentTaskRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <SimilaritySearch onSearch={handleSearch} bahnInfo={bahnInfo} />
      <SimilarityResults
        results={results}
        isLoading={isLoading}
        error={error}
        originalId={originalId}
        isSegmentTaskRunning={isSegmentTaskRunning}
        segmentProgress={segmentProgress}
      />
    </div>
  );
}
