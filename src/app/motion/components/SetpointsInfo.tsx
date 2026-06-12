/* eslint-disable react/no-array-index-key */
import { formatNumber, quaternionToEuler } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const SetpointsInfo: React.FC = () => {
  const { currentTrajSetpoints } = useTrajectory();

  const setpointsWithEuler = currentTrajSetpoints.map((sp) => ({
    ...sp,
    eulerReached: quaternionToEuler(
      sp.qxReached,
      sp.qyReached,
      sp.qzReached,
      sp.qwReached,
    ),
    eulerSupport: quaternionToEuler(
      sp.qxSupport,
      sp.qySupport,
      sp.qzSupport,
      sp.qwSupport,
    ),
  }));

  const fmtEuler = (val: number) => (val === 0 ? '-' : formatNumber(val));

  if (!currentTrajSetpoints?.length) return null;

  return (
    <div className="mb-2 rounded-lg border-gray-200 bg-white">
      <h3 className="mb-2 text-lg font-semibold uppercase tracking-wide text-primary">
        Setpoints
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-center text-sm">
          <thead>
            <tr className="border-b border-gray-400 text-sm text-primary">
              <th className="pb-1">#</th>
              <th className="pb-1">
                X<sub>set</sub>
              </th>
              <th className="pb-1">
                Y<sub>set</sub>
              </th>
              <th className="pb-1">
                Z<sub>set</sub>
              </th>
              <th className="pb-1">
                Roll<sub>set</sub>
              </th>
              <th className="pb-1">
                Pitch<sub>set</sub>
              </th>
              <th className="pb-1">
                Yaw<sub>set</sub>
              </th>
              <th className="pb-1">
                Vel<sub>set</sub>
              </th>
              <th className="pb-1">
                X<sub>sup</sub>
              </th>
              <th className="pb-1">
                Y<sub>sup</sub>
              </th>
              <th className="pb-1">
                Z<sub>sup</sub>
              </th>
              <th className="pb-1">
                Roll<sub>sup</sub>
              </th>
              <th className="pb-1">
                Pitch<sub>sup</sub>
              </th>
              <th className="pb-1">
                Yaw<sub>sup</sub>
              </th>
              <th className="pb-1">Stop-Point</th>
            </tr>
          </thead>
          <tbody>
            {setpointsWithEuler.map((sp, i) => (
              <tr key={i} className="border-b border-gray-200 hover:bg-gray-50">
                <td className="px-2 py-1.5 text-primary">{i + 1}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.xReached)}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.yReached)}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.zReached)}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerReached[0])}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerReached[1])}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerReached[2])}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.velocitySet)}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.xSupport)}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.ySupport)}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.zSupport)}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerSupport[0])}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerSupport[1])}</td>
                <td className="px-2 py-1.5">{fmtEuler(sp.eulerSupport[2])}</td>
                <td className="px-2 py-1.5">{formatNumber(sp.stopPoint)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
