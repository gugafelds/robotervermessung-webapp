'use client';

import React, { useState } from 'react';

import { SimilarityService } from '@/src/actions/vergleich.service';
import type { BahnInfo } from '@/types/bewegungsdaten.types';
import type {
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

import SimilarityResults from './SimilarityResults';
import SimilaritySearch from './SimilaritySearch';
import { VergleichPlot } from './VergleichPlot';

interface SimilaritySearchWrapperProps {
  bahnInfo?: BahnInfo[];
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
    weights: {
      joint: number;
      position: number;
      orientation: number;
      velocity: number;
      acceleration: number;
    },
    prefilter_features: string[],
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
        { modes, weights, limit, prefilter_features },
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
    <div className="flex flex-col">
      <div className="w-full p-2">
        <SimilaritySearch onSearch={handleSearch} bahnInfo={bahnInfo} />
        {/* Plot-Bereich - fest verankert rechts */}
        <div className="my-2 flex gap-x-2 overflow-hidden">
          {bahnResults.length > 0 && (
            <VergleichPlot
              mode="bahnen"
              results={bahnResults}
              isLoading={isLoading}
              originalId={originalId}
            />
          )}

          {segmentGroups.length > 2 && (
            <VergleichPlot
              mode="segmente"
              results={bahnResults}
              segmentGroups={segmentGroups}
              isLoading={isLoading}
              originalId={originalId}
            />
          )}
        </div>
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
