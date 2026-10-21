'use client';

import React, { useEffect, useState } from 'react';

import {
  getAccApproachById,
  getAccPositionById,
} from '@/src/actions/evaluation.service';
import { AccApproachPlot } from '@/src/app/evaluation/components/AccApproachPlot';
import { Typography } from '@/src/components/Typography';
import { formatNumber } from '@/src/lib/functions';
import type { AccApproach, AccPosition } from '@/types/evaluation.types';

// a rest phase shorter than this is shown greyed out (only a brief stop, e.g. stop point 5)
const SHORT_REST_MS = 50;

interface AccPositionInfoProps {
  trajID: string;
  selectedSegment: string; // 'total' or a segment id, shared with MetricsPanel
}

// positioning errors are a few hundredths of a mm: three decimals
const mm3 = (v: number | null) => (v == null ? '-' : v.toFixed(3));
const deg3 = (v: number | null) => (v == null ? '-' : v.toFixed(3));

export const AccPositionInfo: React.FC<AccPositionInfoProps> = ({
  trajID,
  selectedSegment,
}) => {
  const [rows, setRows] = useState<AccPosition[]>([]);
  const [approach, setApproach] = useState<AccApproach[]>([]);

  useEffect(() => {
    if (!trajID) return;
    getAccPositionById(trajID).then(setRows);
    getAccApproachById(trajID).then(setApproach);
  }, [trajID]);

  if (!rows.length) return null;

  // segment rows first, the whole-trajectory row (segment_id = traj_id) last as 'All'
  const segments = rows.filter((r) => r.posMode !== 'all');
  const ordered = [...segments, ...rows.filter((r) => r.posMode === 'all')];

  const cell = 'py-3 text-center';

  // tinted frame around everything that belongs to position accuracy (table + plot)
  return (
    <section className="mx-4 mb-4 rounded-xl border border-gray-500 bg-blue-50 p-3">
      <div className="h-fit rounded-lg border border-gray-500 bg-white p-6">
        <Typography as="h2" className="mb-3">
          Position accuracy
        </Typography>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <th className="pb-2 text-left font-semibold text-primary">
                Segment
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Stop point
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Mode
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Δp [mm]
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Δθ [°]
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                Rest [ms]
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                v<sub>min</sub> [mm/s]
              </th>
              <th className="pb-2 text-center font-semibold text-primary">
                SIDTW at end [mm]
              </th>
            </thead>
            <tbody>
              {ordered.map((r) => {
                const shortRest =
                  r.posMode === 'rest' && (r.tRestMs ?? 0) < SHORT_REST_MS;
                const all = r.posMode === 'all';
                const selected = all
                  ? selectedSegment === 'total'
                  : r.segmentID === selectedSegment;
                return (
                  <tr
                    key={r.segmentID}
                    className={`border-t ${selected ? 'bg-blue-50' : ''} ${shortRest ? 'text-gray-400' : 'text-primary'} ${all ? 'font-semibold' : ''}`}
                  >
                    <td className="py-3 text-left">
                      {all ? 'All' : r.segmentID.split('_')[1]}
                    </td>
                    <td className={cell}>{formatNumber(r.stopPoint)}</td>
                    <td className={cell}>
                      {all ? (
                        '-'
                      ) : (
                        <span
                          title={
                            r.posMode === 'rest'
                              ? `mean of ${r.nRest} samples at rest`
                              : 'no rest phase: closest approach to the target'
                          }
                          className={`rounded px-2 py-0.5 text-xs ${r.posMode === 'rest' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}
                        >
                          {r.posMode === 'rest' ? 'Rest' : 'Nearest'}
                        </span>
                      )}
                    </td>
                    <td className={`${cell} font-semibold`}>{mm3(r.p)}</td>
                    <td className={cell}>{deg3(r.qDeg)}</td>
                    <td className={cell}>
                      {r.tRestMs != null ? Math.round(r.tRestMs) : '-'}
                    </td>
                    <td className={cell}>
                      {r.vMinMmS != null ? r.vMinMmS.toFixed(1) : '-'}
                    </td>
                    <td className={cell}>{mm3(r.p1SIDTW)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex justify-items-stretch space-x-2">
          <AccApproachPlot
            selectedSegment={selectedSegment}
            approach={approach}
            rows={segments}
          />
        </div>
        <p className="mt-3 text-xs text-gray-500">
          Δp, Δθ: measured minus programmed target. <b>Rest</b>: mean pose while
          the robot stands still (&lt; 5 mm/s), i.e. the positioning error;
          rests shorter than {SHORT_REST_MS} ms are greyed out. <b>Nearest</b>:
          no rest phase (loose stop point), closest approach to the target.
          SIDTW at end: path deviation at the last point of the segment. All:
          means over the segments (rest and nearest mixed), v<sub>min</sub> =
          minimum. Plot: distance to the programmed target around the segment
          end; ◆ = Δp of the table, ○ = measured point of the last SIDTW pair
          (the moment SIDTW at end refers to).
        </p>
      </div>
    </section>
  );
};
