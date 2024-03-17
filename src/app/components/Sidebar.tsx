'use client';

import CollapseIcon from '@heroicons/react/20/solid/ChevronDoubleLeftIcon';
import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { redirect, usePathname } from 'next/navigation';
import { useState } from 'react';

import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { formatDate } from '@/src/lib/functions';
import { useApp } from '@/src/providers/app.provider';

export const Sidebar = () => {
  const { trajectories } = useApp();
  const pathname = usePathname();
  const [toggleCollapse, setToggleCollapse] = useState(false);
  const [isCollapsible, setIsCollapsible] = useState(false);
  const [filteredTrajectories, setFilteredTrajectories] = useState(trajectories);

  if (pathname === '/') {
    redirect(`/${trajectories[0].dataId}`);
  }

  const onMouseOver = () => {
    setIsCollapsible(!isCollapsible);
  };

  const wrapperClasses = classNames('h-screen p-4 bg-gray-100 flex flex-col', {
    'w-80': !toggleCollapse,
    'w-20': toggleCollapse,
  });

  const collapseIconClasses = classNames(
    'p-3 rounded bg-light-lighter absolute right-0 hover:bg-gray-100 transition-all',
    {
      'rotate-180': toggleCollapse,
    },
  );

  const handleSidebarToggle = () => {
    setToggleCollapse(!toggleCollapse);
  };

  const handleFilterChange = (filter: string) => {
    const filtered = trajectories.filter((trajectory) =>
        trajectory.trajectoryType.toLowerCase().includes(filter.toLowerCase()) ||
        trajectory.robotName.toLowerCase().includes(filter.toLowerCase()) ||
        trajectory.recordingDate.toLowerCase().includes(filter.toLowerCase()),
        // to-do: add parameter robotType (Victor muss es noch ergänzen)
    );
    setFilteredTrajectories(filtered);
  };

  return (
    <div
      className={`${wrapperClasses} overflow-scroll`}
      onMouseEnter={onMouseOver}
      onMouseLeave={onMouseOver}
      style={{ transition: 'width 300ms cubic-bezier(0.2, 0, 0, 1) 0s' }}
    >
      <div className="flex flex-col align-middle">
        <div className="relative flex items-center justify-between">
          <div
            className={classNames('flex items-end gap-4 pl-1', {
              'opacity-0': toggleCollapse,
            })}
          >
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              trajectories
            </span>
          </div>
          {isCollapsible && (
            <button
              type="button"
              aria-label="collapse"
              className={`${collapseIconClasses} mt-2`}
              onClick={handleSidebarToggle}
            >
              <CollapseIcon width={30} color="#003560" />
            </button>
          )}
        </div>
      </div>
      {!toggleCollapse && <SearchFilter onFilterChange={handleFilterChange} />}
      {!toggleCollapse && (
        <div className="mt-4">
          {filteredTrajectories.map((trajectory) => (
            <Link
              key={trajectory.dataId.toString()}
              href={`/${trajectory.dataId.toString()}`}
            >
              <div
                className={`mt-1 p-3 betterhover:hover:bg-gray-200 ${
                  pathname === `/${trajectory.dataId.toString()}`
                    ? 'bg-gray-200'
                    : ''
                }`}
              >
                <Typography as="h1" className="font-extrabold text-primary">
                  type: {trajectory.trajectoryType}
                </Typography>
                <Typography as="h3" className="font-semibold text-primary">
                  robot name: {trajectory.robotName}
                </Typography>
                <Typography as="h5" className="text-primary">
                  date: {formatDate(trajectory.recordingDate)}
                </Typography>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};