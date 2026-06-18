// src/app/similarity/components/Prognosis.tsx
import React from 'react';

import type {
  ConformalInterval,
  Prognosis,
  TargetFeatures,
  TrajectoryPrognosis,
} from '@/types/similarity.types';

// ═══════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════

const fmt = (v: number | null | undefined, decimals = 4): string =>
  v != null ? v.toFixed(decimals) : '—';

const getErrorColor = (predicted: number | null, gt: number | null): string => {
  if (predicted == null || gt == null) return 'text-gray-400';
  const err = Math.abs(predicted - gt);
  if (err < 0.05) return 'text-green-600';
  if (err < 0.15) return 'text-yellow-600';
  return 'text-red-600';
};

const getIntervalColor = (low: number, high: number): string => {
  const width = high - low;
  if (width < 0.1) return 'text-green-600';
  if (width < 0.3) return 'text-yellow-600';
  return 'text-red-600';
};

// ═══════════════════════════════════════════════════════════════════════════
// Subcomponents
// ═══════════════════════════════════════════════════════════════════════════

interface PredictionRowProps {
  label: string;
  predicted: number | null;
  gt: number | null;
  sigma?: number | null;
  mismatchWarning?: string | null;
}

const PredictionRow: React.FC<PredictionRowProps> = ({
  label,
  predicted,
  gt,
  sigma,
  mismatchWarning,
}) => (
  <div className="flex items-center justify-between gap-4 py-1">
    <p className="w-32 text-lg text-gray-800">{label}</p>
    <p
      className={`font-mono text-base font-semibold ${getErrorColor(predicted, gt)}`}
    >
      {fmt(predicted)}
      {gt != null && predicted != null && (
        <span className="ml-2 text-base font-semibold">
          ({fmt(Math.abs(predicted - gt))})
        </span>
      )}
      {mismatchWarning != null && (
        <span
          className="ml-2 cursor-help text-amber-500"
          title={mismatchWarning}
        >
          ⚠️
        </span>
      )}
    </p>
    {sigma != null && (
      <p className="font-mono text-sm text-primary">
        Consistency: {fmt(sigma, 3)}
      </p>
    )}
  </div>
);

interface IntervalDisplayProps {
  interval: ConformalInterval;
}

const IntervalDisplay: React.FC<IntervalDisplayProps> = ({ interval }) => (
  <div className="mt-2 rounded-md bg-gray-50 px-3 py-2">
    <div className="flex items-center justify-between">
      <p className="py-1 text-base text-primary">
        Conformal interval{' '}
        <span className="rounded-md bg-blue-100 px-1.5 py-0.5 text-sm text-blue-800">
          {(interval.coverage * 100).toFixed(0)}%
        </span>
      </p>
      {interval.n_segments != null && (
        <p className="text-sm text-gray-800">{interval.n_segments} segments</p>
      )}
    </div>
    <p
      className={`mt-1 font-mono text-base font-semibold ${getIntervalColor(interval.low, interval.high)}`}
    >
      [{fmt(interval.low)}, {fmt(interval.high)}] mm
    </p>
  </div>
);

interface PrognosisCardProps {
  label: string;
  prediction: TrajectoryPrognosis | null;
  gt: number | null;
  interval: ConformalInterval | null;
}

const PrognosisCard: React.FC<PrognosisCardProps> = ({
  label,
  prediction,
  gt,
  interval,
}) => (
  <div className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-4">
    <p className="text-lg font-medium uppercase tracking-wider text-primary">
      {label}
    </p>

    {prediction != null ? (
      <>
        <PredictionRow
          label="p̂ (error)"
          predicted={prediction.p_hat}
          gt={gt}
          sigma={prediction.sigma}
          mismatchWarning={interval?.calibration_mismatch?.warning ?? null}
        />
        {interval != null && <IntervalDisplay interval={interval} />}
      </>
    ) : (
      <p className="text-lg text-gray-800">—</p>
    )}
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════════

interface PrognosisViewProps {
  prognosis: Prognosis | null;
  targetTrajFeatures?: TargetFeatures;
  stage2Active: boolean;
  dtwMode?: 'position' | 'joint';
  metric?: 'sidtw' | 'qdtw';
}

const PrognosisView: React.FC<PrognosisViewProps> = ({
  prognosis,
  targetTrajFeatures,
  stage2Active,
  dtwMode = 'position',
  metric = 'sidtw',
}) => {
  if (prognosis == null) return null;

  const gt = targetTrajFeatures?.mean_distance ?? null;

  return (
    <div className="flex flex-col overflow-y-auto rounded-lg border border-gray-400 bg-white shadow-md">
      {/* Header */}
      <div className="bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              Performance prognosis
            </h3>
            <p className="mt-1 flex items-center gap-2 text-sm text-gray-600">
              <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium uppercase text-gray-700">
                {metric}
              </span>
              {stage2Active && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                  DTW {dtwMode}
                </span>
              )}
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                {prognosis.stage === 'stage2_dtw' ? 'Stage 2' : 'Stage 1'}
              </span>
            </p>
          </div>

          {gt != null && (
            <div className="flex flex-col items-end gap-1">
              <p className="text-xs text-gray-400">Ground truth (mean)</p>
              <p className="font-mono text-sm font-semibold text-blue-950">
                {fmt(gt)} mm
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-2 gap-4 border-t p-4">
        <PrognosisCard
          label="Direct (trajectories)"
          prediction={prognosis.direct}
          gt={gt}
          interval={prognosis.direct_conformal_interval}
        />
        <PrognosisCard
          label="Decomposed (segments)"
          prediction={prognosis.decomposed}
          gt={gt}
          interval={prognosis.decomposed_conformal_interval}
        />
      </div>
    </div>
  );
};

export default PrognosisView;
