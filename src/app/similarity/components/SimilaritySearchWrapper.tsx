'use client';

import React, { useState } from 'react';

import { SimilarityService } from '@/src/actions/similarity.service';
import type { TrajInfo } from '@/types/motion.types';
import type {
  Prognosis,
  SearchTiming,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

import PrognosisView from './Prognosis';
import { SimilarityPlot } from './SimilarityPlot';
import SimilarityResults from './SimilarityResults';
import SimilaritySearch from './SimilaritySearch';

interface SimilaritySearchWrapperProps {
  trajInfo?: TrajInfo[];
}

export default function SimilaritySearchWrapper({
  trajInfo,
}: SimilaritySearchWrapperProps) {
  const [trajResults, setTrajResults] = useState<SimilarityResult[]>([]);
  const [targetTrajFeatures, setTargetTrajFeatures] = useState<
    TargetFeatures | undefined
  >();
  const [segmentGroups, setSegmentGroups] = useState<SegmentGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [originalId, setOriginalId] = useState('');
  const [showPlots, setShowPlots] = useState(false);
  const [timing, setTiming] = useState<SearchTiming | undefined>();
  const [stage2Active, setStage2Active] = useState(false);
  const [dtwMode, setDtwMode] = useState<'position' | 'joint'>('position');
  const [metric, setMetric] = useState<'sidtw' | 'qdtw'>('sidtw');
  const [prognosis, setPrognosis] = useState<Prognosis | null>(null);

  const hasResults = trajResults.length > 0 || segmentGroups.length > 0;

  const handleSearch = async (
    id: string,
    limit: number,
    modes: string[],
    weights: {
      joint: number;
      position: number;
      orientation: number;
      velocity: number;
      metadata: number;
    },
    prefilter_features: string[],
    stage2_active: boolean,
    dtw_mode: 'position' | 'joint',
    search_metric: 'sidtw' | 'qdtw',
    prognosis_active: boolean,
    include_tags: string[],
  ) => {
    setIsLoading(true);
    setError('');
    setOriginalId(id);
    setTrajResults([]);
    setTargetTrajFeatures(undefined);
    setSegmentGroups([]);
    setTiming(undefined);
    setStage2Active(false);
    setMetric(search_metric);
    setPrognosis(null);

    try {
      await SimilarityService.searchSimilarityEmbedding(
        id,
        {
          modes,
          weights,
          limit,
          prefilter_features,
          stage2_active,
          dtw_mode,
          metric: search_metric,
          prognosis_active,
          coverage: 0.9,
          include_tags,
        },
        {
          onTrajsFound: (
            results,
            targetFeatures,
            responseTiming,
            responseStage2,
            responseDtwMode,
          ) => {
            setTrajResults(results);
            setTargetTrajFeatures(targetFeatures);
            setTiming(responseTiming);
            setStage2Active(responseStage2 ?? false);
            setDtwMode(responseDtwMode ?? 'position');
            setIsLoading(false);
          },
          onSegmentsFound: (groups) => {
            setSegmentGroups(groups);
          },
          onPrognosisFound: (prog) => {
            setPrognosis(prog);
          },
          onError: (errorMsg) => {
            setError(`Error on the search: ${errorMsg}`);
            setIsLoading(false);
          },
        },
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`Error on the search: ${errorMessage}`);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col">
      <div className="w-full p-2">
        <SimilaritySearch
          onSearch={handleSearch}
          trajInfo={trajInfo}
          showPlots={showPlots}
          onTogglePlots={() => setShowPlots(!showPlots)}
          hasResults={hasResults}
        />

        {showPlots && (
          <div className="my-2 flex items-start gap-x-2 overflow-hidden">
            {segmentGroups.length > 1 && (
              <SimilarityPlot
                results={trajResults}
                segmentGroups={segmentGroups}
                isLoading={isLoading}
                originalId={originalId}
                stage2Active={stage2Active}
              />
            )}
          </div>
        )}

        <div className="my-2 items-start gap-x-2 overflow-hidden">
          <PrognosisView
            prognosis={prognosis}
            targetTrajFeatures={targetTrajFeatures}
            stage2Active={stage2Active}
            metric={metric}
            dtwMode={dtwMode}
          />
        </div>

        <SimilarityResults
          results={trajResults}
          isLoading={isLoading}
          error={error}
          originalId={originalId}
          targetTrajFeatures={targetTrajFeatures}
          segmentGroups={segmentGroups}
          timing={timing}
          stage2Active={stage2Active}
          dtwMode={dtwMode}
          metric={metric}
        />
      </div>
    </div>
  );
}
