'use client';

import React, { useState } from 'react';

import { applyEuclideanDistance } from '@/src/actions/methods.service';
import { Spinner } from '@/src/components/Spinner';
import type { TrajectoryData, TrajectoryEuclideanMetrics } from '@/types/main';

type Props = {
  currentTrajectory: TrajectoryData;
  currentEuclideanMetrics: TrajectoryEuclideanMetrics;
  setEuclidean: any;
  visibleEuclidean: boolean;
  euclideanDistances: any;
  showEuclideanPlot: any;
};

export const ApplyEuclideanButton = ({
  currentTrajectory,
  euclideanDistances,
  setEuclidean,
  visibleEuclidean,
  showEuclideanPlot,
  currentEuclideanMetrics,
}: Props) => {
  const [loading, setLoading] = useState(false);

  return (
    <div className="mb-5 flex flex-wrap gap-3 rounded-3xl bg-stone-200">
      <div className="mt-3 text-lg font-bold text-primary">
        euclidean distances
      </div>

      {!currentEuclideanMetrics.euclideanIntersections && (
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl p-2 text-lg font-normal text-primary shadow-md transition-colors duration-200 ease-in betterhover:hover:bg-gray-200"
          onClick={async () => {
            if (euclideanDistances?.length > 0) {
              setEuclidean([]);
              return;
            }
            try {
              setLoading(true);
              const euclidean = await applyEuclideanDistance(currentTrajectory);
              setLoading(false);
              setEuclidean(euclidean);
            } catch {
              setLoading(false);
            }
          }}
        >
          generate {loading && <Spinner />}
        </button>
      )}

      {currentEuclideanMetrics.euclideanIntersections && (
        <button
          type="button"
          className={`
       flex items-center gap-2 rounded-xl p-2 text-lg text-primary shadow-md transition-colors duration-200 ease-in
      ${visibleEuclidean ? 'bg-stone-300 font-bold' : 'font-normal betterhover:hover:bg-gray-200'}`}
          onClick={() => {
            showEuclideanPlot(!visibleEuclidean);
          }}
        >
          view 3D
        </button>
      )}
    </div>
  );
};
