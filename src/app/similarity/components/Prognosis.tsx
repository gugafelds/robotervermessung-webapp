import React from 'react';

import { computePrognosis } from '@/src/lib/prognosis';
import type {
  PrognosisFields,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

const formatVal = (v: number | null) => (v != null ? v.toFixed(4) : '—');

const formatError = (v: number | null, gt: number | null) => {
  if (v == null || gt == null) return '—';
  return Math.abs(v - gt).toFixed(4);
};

const getErrorColor = (v: number | null, gt: number | null): string => {
  if (v == null || gt == null) return 'text-gray-400';
  const err = Math.abs(v - gt);
  if (err < 0.05) return 'text-green-600';
  if (err < 0.15) return 'text-yellow-600';
  return 'text-red-600';
};

const getConfidenceColor = (v: number): string => {
  if (v > 0.7) return 'text-green-600';
  if (v > 0.4) return 'text-yellow-600';
  return 'text-red-600';
};

interface PrognosisRowProps {
  label: string;
  min: number | null;
  mean: number | null;
  max: number | null;
  gtMin: number | null;
  gtMean: number | null;
  gtMax: number | null;
}

const PrognosisRow: React.FC<PrognosisRowProps> = ({
  label,
  min,
  mean,
  max,
  gtMin,
  gtMean,
  gtMax,
}) => (
  <div className="grid grid-cols-4 items-center gap-x-4">
    <p className="text-xs text-gray-400">{label}</p>
    <p className={`font-mono text-sm font-medium ${getErrorColor(min, gtMin)}`}>
      {formatVal(min)}
      {gtMin != null && min != null && (
        <span className="ml-1 text-xs text-gray-400">
          ±{formatError(min, gtMin)}
        </span>
      )}
    </p>
    <p
      className={`font-mono text-sm font-medium ${getErrorColor(mean, gtMean)}`}
    >
      {formatVal(mean)}
      {gtMean != null && mean != null && (
        <span className="ml-1 text-xs text-gray-400">
          ±{formatError(mean, gtMean)}
        </span>
      )}
    </p>
    <p className={`font-mono text-sm font-medium ${getErrorColor(max, gtMax)}`}>
      {formatVal(max)}
      {gtMax != null && max != null && (
        <span className="ml-1 text-xs text-gray-400">
          ±{formatError(max, gtMax)}
        </span>
      )}
    </p>
  </div>
);

interface PrognosisCardProps {
  label: string;
  fields: PrognosisFields;
  gtMin: number | null;
  gtMean: number | null;
  gtMax: number | null;
  confidence?: number | null;
}

const PrognosisCard: React.FC<PrognosisCardProps> = ({
  label,
  fields,
  gtMin,
  gtMean,
  gtMax,
  confidence,
}) => (
  <div className="flex flex-col gap-3 rounded-lg border border-gray-300 bg-white p-4">
    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
      {label}
    </p>

    <div className="grid grid-cols-4 gap-x-4">
      <span />
      <p className="text-xs font-medium text-gray-500">Min</p>
      <p className="text-xs font-medium text-gray-500">Mean</p>
      <p className="text-xs font-medium text-gray-500">Max</p>
    </div>

    <div className="flex flex-col gap-2">
      <PrognosisRow
        label="Simple"
        min={fields.min.simple}
        mean={fields.mean.simple}
        max={fields.max.simple}
        gtMin={gtMin}
        gtMean={gtMean}
        gtMax={gtMax}
      />
      <PrognosisRow
        label="Weighted"
        min={fields.min.weighted}
        mean={fields.mean.weighted}
        max={fields.max.weighted}
        gtMin={gtMin}
        gtMean={gtMean}
        gtMax={gtMax}
      />
    </div>

    {confidence != null && (
      <div className="mt-2 border-t pt-2">
        <p className="text-xs text-gray-400">Confidence</p>
        <p
          className={`font-mono text-sm font-medium ${getConfidenceColor(confidence)}`}
        >
          {(confidence * 100).toFixed(1)}%
        </p>
      </div>
    )}
  </div>
);

interface PrognosisProps {
  trajResults: SimilarityResult[];
  segmentGroups: SegmentGroup[];
  targetTrajFeatures?: TargetFeatures;
  stage2Active: boolean;
  dtwMode?: 'position' | 'joint';
  metric?: 'sidtw' | 'qdtw';
}

const Prognosis: React.FC<PrognosisProps> = ({
  trajResults,
  segmentGroups,
  targetTrajFeatures,
  stage2Active,
  dtwMode = 'position',
  metric = 'sidtw',
}) => {
  const hasData = trajResults.length > 0 || segmentGroups.length > 0;
  if (!hasData) return null;

  const { direct, decomposed, groundTruth, confidence } = computePrognosis(
    trajResults,
    segmentGroups,
    targetTrajFeatures,
    stage2Active,
  );

  return (
    <div className="flex flex-col overflow-y-auto rounded-lg border border-gray-400 bg-white shadow-md">
      <div className="bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              Performance prognosis
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium uppercase text-gray-700">
                {metric}
              </span>
              {stage2Active && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                  DTW {dtwMode}
                </span>
              )}
            </p>
          </div>

          <div className="flex flex-col items-end gap-1">
            <p className="text-xs text-gray-400">
              Ground Truth [min, mean, max]
            </p>
            <p className="font-mono text-sm font-semibold text-blue-950">
              [{formatVal(groundTruth.min)}, {formatVal(groundTruth.mean)},{' '}
              {formatVal(groundTruth.max)}]
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 border-t p-4">
        <PrognosisCard
          label="Direct (Trajectories)"
          fields={direct}
          gtMin={groundTruth.min}
          gtMean={groundTruth.mean}
          gtMax={groundTruth.max}
          confidence={confidence.direct}
        />
        <PrognosisCard
          label="Decomposed (Segments)"
          fields={decomposed}
          gtMin={groundTruth.min}
          gtMean={groundTruth.mean}
          gtMax={groundTruth.max}
          confidence={confidence.decomposed.weightedMean}
        />
      </div>
    </div>
  );
};

export default Prognosis;
