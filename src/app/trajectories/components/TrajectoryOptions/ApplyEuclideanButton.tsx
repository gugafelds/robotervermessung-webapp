'use client';

import React, { useState } from 'react';

import { applyEuclideanDistance } from '@/src/actions/methods.service';
import { Spinner } from '@/src/components/Spinner';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const ApplyEuclideanButton = () => {
  const [loading, setLoading] = useState(false);
  const {
    currentTrajectory,
    currentEuclidean,
    setCurrentEuclidean,
    visibleEuclidean,
    showEuclideanPlot,
  } = useTrajectory();

  return (
    <div className="mb-5 flex flex-wrap gap-3 rounded-3xl bg-stone-200">
      <div className="mt-3 text-lg font-bold text-primary">
        euclidean distances
      </div>

      {!currentEuclidean.euclideanIntersections && (
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl p-2 text-lg font-normal text-primary shadow-md transition-colors duration-200 ease-in betterhover:hover:bg-gray-200"
          onClick={async () => {
            if (currentEuclidean?.length > 0) {
              setCurrentEuclidean([]);
              return;
            }
            try {
              setLoading(true);
              const euclidean = await applyEuclideanDistance(currentTrajectory);
              setLoading(false);
              setCurrentEuclidean(euclidean);
            } catch {
              setLoading(false);
            }
          }}
        >
          generate {loading && <Spinner />}
        </button>
      )}

      {currentEuclidean.euclideanIntersections && (
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
