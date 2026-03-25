import type {
  PrognosisResult,
  SegmentGroup,
  SimilarityResult,
  TargetFeatures,
} from '@/types/similarity.types';

// ─────────────────────────────────────────────────────────────
// HELPER: Simple + Weighted Mean für ein einzelnes Feld
// ─────────────────────────────────────────────────────────────
function simpleAndWeighted(
  values: number[],
  rawWeights: number[],
): { simple: number | null; weighted: number | null } {
  if (values.length === 0) return { simple: null, weighted: null };

  const simple = values.reduce((a, b) => a + b, 0) / values.length;

  const totalW = rawWeights.reduce((a, b) => a + b, 0);
  const weighted =
    values.reduce((sum, v, i) => sum + v * rawWeights[i], 0) / totalW;

  return { simple, weighted };
}

// ─────────────────────────────────────────────────────────────
// HELPER: Extrahiert Werte + Gewichte aus einer Result-Liste
// ─────────────────────────────────────────────────────────────
type DistanceKey = 'min_distance' | 'mean_distance' | 'max_distance';

function extractValuesAndWeights(
  items: SimilarityResult[],
  field: DistanceKey,
  stage2Active: boolean,
): { values: number[]; rawWeights: number[] } {
  const values: number[] = [];
  const rawWeights: number[] = [];

  for (const item of items) {
    const val = item[field];
    if (val != null) {
      if (stage2Active) {
        const dtw = item.dtw_distance;
        if (dtw != null) {
          values.push(val);
          rawWeights.push(1 / (dtw + 1e-6));
        }
      } else {
        const rrf = item.similarity_score;
        if (rrf != null) {
          values.push(val);
          rawWeights.push(rrf);
        }
      }
    }
  }

  return { values, rawWeights };
}

// ─────────────────────────────────────────────────────────────
// HELPER: Prognosis für alle 3 Felder auf einer Result-Liste
// ─────────────────────────────────────────────────────────────
function computeAllFields(
  items: SimilarityResult[],
  stage2Active: boolean,
): {
  min: { simple: number | null; weighted: number | null };
  mean: { simple: number | null; weighted: number | null };
  max: { simple: number | null; weighted: number | null };
} {
  const fields: DistanceKey[] = [
    'min_distance',
    'mean_distance',
    'max_distance',
  ];
  const results = fields.map((field) => {
    const { values, rawWeights } = extractValuesAndWeights(
      items,
      field,
      stage2Active,
    );
    return simpleAndWeighted(values, rawWeights);
  });

  return {
    min: results[0],
    mean: results[1],
    max: results[2],
  };
}

// ─────────────────────────────────────────────────────────────
// HELPER: Rohgewichte aus einer Result-Liste extrahieren
// ─────────────────────────────────────────────────────────────
function extractRawWeights(
  items: SimilarityResult[],
  stage2Active: boolean,
): number[] {
  const rawWeights: number[] = [];
  for (const item of items) {
    if (stage2Active) {
      const dtw = item.dtw_distance;
      if (dtw != null) rawWeights.push(1 / (dtw + 1e-6));
    } else {
      const rrf = item.similarity_score;
      if (rrf != null) rawWeights.push(rrf);
    }
  }
  return rawWeights;
}

// ─────────────────────────────────────────────────────────────
// HELPER: Konfidenz für eine Result-Liste (computeConfidence)
// Proximity: normalisierte Entropie der Gewichte
// Cohesion:  gewichteter CV der mean_distance Werte
// ─────────────────────────────────────────────────────────────
function computeConfidence(
  items: SimilarityResult[],
  stage2Active: boolean,
): number | null {
  if (items.length < 2) return null;

  const rawWeights = extractRawWeights(items, stage2Active);
  const perfValues = items
    .map((item) => item.mean_distance)
    .filter((v): v is number => v != null);

  if (rawWeights.length < 2 || perfValues.length < 2) return null;

  // Normalisierte Gewichte
  const totalW = rawWeights.reduce((a, b) => a + b, 0);
  const weightsNorm = rawWeights.map((w) => w / totalW);

  // 1. Proximity: 1 - normalisierte Entropie
  const H = -weightsNorm.reduce((sum, w) => sum + w * Math.log(w + 1e-15), 0);
  const Hmax = Math.log(weightsNorm.length);
  const Hnorm = Hmax > 1e-10 ? H / Hmax : 0;

  // 2. Cohesion: 1 / (1 + CV) der Performance-Werte
  const weightedMean = weightsNorm.reduce(
    (sum, w, i) => sum + w * (perfValues[i] ?? 0),
    0,
  );
  const weightedVar = weightsNorm.reduce(
    (sum, w, i) => sum + w * ((perfValues[i] ?? 0) - weightedMean) ** 2,
    0,
  );
  const cv = weightedMean > 1e-10 ? Math.sqrt(weightedVar) / weightedMean : 0;
  const cohesionScore = 1 / (1 + cv);

  // 3. Kombination
  const proximityPenalty = Hnorm * (1 - cohesionScore);
  return cohesionScore * (1 - proximityPenalty);
}

// ─────────────────────────────────────────────────────────────
// HELPER: Trajektorie-Konfidenz aus Segment-Konfidenzen
// ─────────────────────────────────────────────────────────────
function computeTrajectoryConfidence(
  segConfidences: (number | null)[],
  segDurations: number[],
): {
  weightedMean: number | null;
  minimum: number | null;
  harmonicMean: number | null;
} {
  const valid = segConfidences
    .map((c, i) => (c != null && c > 0 ? { c, d: segDurations[i] } : null))
    .filter((v): v is { c: number; d: number } => v != null);

  if (valid.length === 0) {
    return { weightedMean: null, minimum: null, harmonicMean: null };
  }

  const totalDur = valid.reduce((sum, v) => sum + v.d, 0);
  const weightedMean = valid.reduce((sum, v) => sum + v.c * v.d, 0) / totalDur;
  const minimum = Math.min(...valid.map((v) => v.c));
  const harmonicMean =
    valid.length / valid.reduce((sum, v) => sum + 1 / Math.max(v.c, 1e-10), 0);

  return { weightedMean, minimum, harmonicMean };
}

// ─────────────────────────────────────────────────────────────
// MAIN: computePrognosis
// ─────────────────────────────────────────────────────────────
export function computePrognosis(
  trajResults: SimilarityResult[],
  segmentGroups: SegmentGroup[],
  targetTrajFeatures: TargetFeatures | undefined,
  stage2Active: boolean,
): PrognosisResult {
  // ── Ground Truth ──────────────────────────────────────────
  const groundTruth = {
    min: targetTrajFeatures?.min_distance ?? null,
    mean: targetTrajFeatures?.mean_distance ?? null,
    max: targetTrajFeatures?.max_distance ?? null,
  };

  // ── Direct ────────────────────────────────────────────────
  const direct = computeAllFields(trajResults, stage2Active);
  const directConfidence = computeConfidence(trajResults, stage2Active);

  // ── Decomposed ────────────────────────────────────────────
  const segMin: number[] = [];
  const segMean: number[] = [];
  const segMax: number[] = [];
  const segMinW: number[] = [];
  const segMeanW: number[] = [];
  const segMaxW: number[] = [];
  const segDurations: number[] = [];
  const segConfidences: (number | null)[] = [];

  for (const group of segmentGroups) {
    const duration = group.target_segment_features?.duration;
    if (duration != null) {
      const fields = computeAllFields(group.results, stage2Active);
      const conf = computeConfidence(group.results, stage2Active);
      if (
        fields.min.simple != null &&
        fields.mean.simple != null &&
        fields.max.simple != null
      ) {
        segMin.push(fields.min.simple);
        segMean.push(fields.mean.simple);
        segMax.push(fields.max.simple);
        segMinW.push(fields.min.weighted ?? 0);
        segMeanW.push(fields.mean.weighted ?? 0);
        segMaxW.push(fields.max.weighted ?? 0);
        segDurations.push(duration);
        segConfidences.push(conf);
      }
    }
  }

  let decomposed: PrognosisResult['decomposed'] = {
    min: { simple: null, weighted: null },
    mean: { simple: null, weighted: null },
    max: { simple: null, weighted: null },
  };

  if (segDurations.length > 0) {
    const totalDur = segDurations.reduce((a, b) => a + b, 0);
    const wavg = (vals: number[]) =>
      vals.reduce((sum, v, i) => sum + v * segDurations[i], 0) / totalDur;

    decomposed = {
      min: { simple: wavg(segMin), weighted: wavg(segMinW) },
      mean: { simple: wavg(segMean), weighted: wavg(segMeanW) },
      max: { simple: wavg(segMax), weighted: wavg(segMaxW) },
    };
  }

  const decomposedConfidence = computeTrajectoryConfidence(
    segConfidences,
    segDurations,
  );

  return {
    direct,
    decomposed,
    groundTruth,
    confidence: {
      direct: directConfidence,
      decomposed: decomposedConfidence,
    },
  };
}
