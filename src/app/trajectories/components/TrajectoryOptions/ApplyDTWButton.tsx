'use client';

import React, { useState } from 'react';

import { applyDTWJohnen } from '@/src/actions/methods.service';
import { Spinner } from '@/src/components/Spinner';

type Props = {
  currentDTWJohnenMetrics: any;
  euclideanDistances: any;
  setEuclidean: any;
  currentTrajectory: any;
  visibleDTWJohnen: any;
  showDTWJohnenPlot: any;
};

export const ApplyDTWButton = ({
  currentTrajectory,
  showDTWJohnenPlot,
  visibleDTWJohnen,
  currentDTWJohnenMetrics,
  euclideanDistances,
  setEuclidean,
}: Props) => {
  const [loading, setLoading] = useState(false);

  return (
    <div className="mb-5 flex flex-wrap gap-3 rounded-3xl bg-stone-200">
      <div className="mt-3 text-lg font-bold text-primary">dtw johnen</div>

      {!currentDTWJohnenMetrics.dtwPath && (
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
              const dtwJohnen = await applyDTWJohnen(currentTrajectory);
              setLoading(false);
              setEuclidean(dtwJohnen.intersection);
            } catch {
              setLoading(false);
            }
          }}
        >
          generate {loading && <Spinner />}
        </button>
      )}

      {currentDTWJohnenMetrics.dtwPath && (
        <button
          type="button"
          className={`
       flex items-center gap-2 rounded-xl p-2 text-lg text-primary shadow-md transition-colors duration-200 ease-in
      ${visibleDTWJohnen ? 'bg-stone-300 font-bold' : 'font-normal betterhover:hover:bg-gray-200'}`}
          onClick={() => {
            showDTWJohnenPlot(!visibleDTWJohnen);
          }}
        >
          view 3D
        </button>
      )}
    </div>
  );
};
