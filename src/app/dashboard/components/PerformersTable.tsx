import Link from 'next/link';

import { Typography } from '@/src/components/Typography';
import type { PerformerData } from '@/types/dashboard.types';

interface PerformersTableProps {
  bestPerformers?: PerformerData[];
  worstPerformers?: PerformerData[];
}

export function PerformersTable({
  bestPerformers = [],
  worstPerformers = [],
}: PerformersTableProps) {
  const formatValue = (value: number | null | undefined, decimals = 2) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(decimals);
  };

  const renderTable = (
    data: PerformerData[],
    title: string,
    colorClass: string,
  ) => (
    <div className="">
      <Typography as="h4" className="mb-2">
        {title}
      </Typography>
      <div className="overflow-x-auto">
        <table className="w-full text-center text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-700">
            <tr>
              <th className="px-4 py-3">Traj-ID</th>
              <th className="px-4 py-3">SIDTW [mm]</th>
              <th className="px-4 py-3">Payload [kg]</th>
              <th className="px-4 py-3">Vel. [mm/s]</th>
              <th className="px-4 py-3">Accel. [mm/s²]</th>
              <th className="px-4 py-3">Setpoints</th>
              <th className="px-4 py-3">Stop [%]</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                  No data available
                </td>
              </tr>
            ) : (
              data.map((performer) => (
                <tr key={performer.traj_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/motion/${performer.traj_id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {performer.traj_id}
                    </Link>
                  </td>
                  <td className={`px-4 py-3 font-semibold ${colorClass}`}>
                    {formatValue(performer.sidtw_average_distance, 3)}
                  </td>
                  <td className="px-4 py-3">{performer.weight ?? 'N/A'}</td>
                  <td className="px-4 py-3">
                    {formatValue(performer.max_velocity, 0)}
                  </td>
                  <td className="px-4 py-3">
                    {formatValue(performer.max_acceleration, 0)}
                  </td>
                  <td className="px-4 py-3">{performer.waypoints ?? 'N/A'}</td>
                  <td className="px-4 py-3">{performer.stop_point ?? 'N/A'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col justify-center space-y-8 rounded-2xl border border-gray-500 bg-white p-6">
      {renderTable(bestPerformers, 'The 5 best', 'text-green-600')}
      {renderTable(worstPerformers, 'The 5 worst', 'text-red-600')}
    </div>
  );
}
