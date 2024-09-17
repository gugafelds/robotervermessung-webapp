'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { filterBy, formatDate } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const Sidebar = () => {
  const { trajectoriesHeader, showEuclideanPlot, showDTWJohnenPlot, segmentsHeader, bahnInfo } =
    useTrajectory();
  const pathname = usePathname();

  const [filteredTrajectories, setFilteredTrajectories] =
    useState(bahnInfo);

  const [expandedTrajectory, setExpandedTrajectory] = useState<string | null>(null);

  const toggleExpand = (bahnID: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedTrajectory(expandedTrajectory === bahnID ? null : bahnID);
  };

  const handleFilterChange = (filter: string) => {
    const filtered = bahnInfo.filter((trajectory) =>
      filterBy(filter, [
        trajectory.robotModel,
        trajectory.bahnID,
        formatDate(trajectory.recordingDate),
      ]),
    );
    setFilteredTrajectories(filtered);
  };

  return (
    <div className="flex h-80 w-full flex-col bg-gray-100 px-4 py-2 lg:h-fullscreen lg:max-w-80">
      <div className="flex flex-col align-middle">
        <div className="relative flex items-center justify-between">
          <div className={classNames('flex items-end gap-4 pl-1')}>
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              trajektorien
            </span>
          </div>
        </div>
        <SearchFilter onFilterChange={handleFilterChange} />
      </div>

      <div className="mt-4 overflow-scroll">
        {filteredTrajectories.map((trajectory) => (
          <div key={trajectory.bahnID.toString()} className="mt-1 rounded-xl p-3 transition-colors duration-200 ease-in betterhover:hover:bg-gray-200">
            <div className="flex justify-between items-center">
              {segmentsHeader.some(segment => segment.trajectoryHeaderId === trajectory.bahnID) && (
                <span onClick={(e) => toggleExpand(trajectory.bahnID.toString(), e)} className="cursor-pointer text-primary">
                  {expandedTrajectory === trajectory.bahnID.toString() ? '▾' : '▸'}
                </span>
              )}
              <Link
                href={`/trajectories/${trajectory.bahnID.toString()}`}
                onClick={() => {
                  showEuclideanPlot(false);
                  showDTWJohnenPlot(false);
                }}
                className="ml-2 flex-1"
              >
                <div>
                  <Typography as="h6" className="font-extrabold text-primary">
                    {trajectory.recordFilename}
                  </Typography>
                  <Typography as="h6" className="font-semibold text-primary">
                    {`ID: ${trajectory.bahnID}`}
                  </Typography>
                  <Typography as="h6" className="text-primary">
                    {trajectory.startTime ? formatDate(trajectory.recordingDate) : 'n. a.'}
                  </Typography>
                </div>
              </Link>
            </div>

            {expandedTrajectory === trajectory.bahnID.toString() && (
              <div className="ml-6 mt-2">
                {Array.from(new Set(segmentsHeader
                  .filter(
                    (segment) => segment.trajectoryHeaderId === trajectory.bahnID
                  )
                  .map((segment) => segment.segmentId)
                )).map((segmentId) => (
                  <Link key={segmentId.toString()} href={`/trajectories/${segmentId.toString()}`}>
                    <div className="p-2 rounded bg-gray-100 betterhover:hover:bg-gray-200 cursor-pointer">
                      <Typography as="h6" className="text-primary">
                        {`Segment ID: ${segmentId}`}
                      </Typography>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
