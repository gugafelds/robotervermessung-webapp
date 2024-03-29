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
  const { trajectoriesHeader } = useTrajectory();
  const pathname = usePathname();

  const [filteredTrajectories, setFilteredTrajectories] =
    useState(trajectoriesHeader);

  const handleFilterChange = (filter: string) => {
    const filtered = trajectoriesHeader.filter((trajectory) =>
      filterBy(filter, [
        trajectory.trajectoryType,
        trajectory.robotName,
        formatDate(trajectory.recordingDate),
      ]),
    );
    setFilteredTrajectories(filtered);
  };

  return (
    <div className="flex flex-col overflow-scroll bg-gray-100 p-4 sm:h-80 sm:w-full md:h-screen md:w-80 lg:h-screen lg:w-80">
      <div className="flex flex-col align-middle">
        <div className="relative flex items-center justify-between">
          <div className={classNames('flex items-end gap-4 pl-1')}>
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              trajectories
            </span>
          </div>
        </div>
      </div>

      <SearchFilter onFilterChange={handleFilterChange} />

      <div className="mt-4">
        {filteredTrajectories.map((trajectory) => (
          <Link
            key={trajectory.dataId.toString()}
            href={`/trajectories/${trajectory.dataId.toString()}`}
          >
            <div
              className={` mt-1 rounded-xl p-3 transition-colors duration-200 ease-in betterhover:hover:bg-gray-200 ${
                pathname === `/trajectories/${trajectory.dataId.toString()}`
                  ? 'bg-gray-200'
                  : ''
              }`}
            >
              <Typography as="h6" className="font-extrabold text-primary">
                {trajectory.trajectoryType}
              </Typography>
              <Typography as="h6" className="font-semibold text-primary">
                {trajectory.robotModel}
              </Typography>
              <Typography as="h6" className="text-primary">
                {formatDate(trajectory.recordingDate)}
              </Typography>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};
