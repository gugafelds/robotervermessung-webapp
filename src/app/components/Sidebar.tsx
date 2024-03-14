'use client';

import CollapseIcon from '@heroicons/react/20/solid/ChevronDoubleLeftIcon';
import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { redirect, usePathname } from 'next/navigation';
import { useState } from 'react';

import { Typography } from '@/src/components/Typography';
import { formatDate } from '@/src/lib/functions';
import { useApp } from '@/src/providers/app.provider';

export const Sidebar = () => {
  const { trajectories } = useApp();
  const pathname = usePathname();
  const [toggleCollapse, setToggleCollapse] = useState(false);
  const [isCollapsible, setIsCollapsible] = useState(false);

  if (pathname === '/') {
    redirect(`/${trajectories[0]._id}`);
  }

  const onMouseOver = () => {
    setIsCollapsible(!isCollapsible);
  };

  const wrapperClasses = classNames(
    'h-screen p-4 bg-gray-100 flex justify-between flex-col',
    {
      'w-80': !toggleCollapse,
      'w-20': toggleCollapse,
    },
  );

  const collapseIconClasses = classNames(
    'p-4 rounded bg-light-lighter absolute right-0 hover:bg-gray-100 transition-all',
    {
      'rotate-180': toggleCollapse,
    },
  );

  const handleSidebarToggle = () => {
    setToggleCollapse(!toggleCollapse);
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
      {!toggleCollapse && (
        <div className="mt-4">
          {trajectories.map((trajectory) => (
            <Link
              key={trajectory._id.toString()}
              href={`/${trajectory._id.toString()}`}
            >
              <div
                className={`mt-1 p-5 betterhover:hover:bg-gray-200 ${
                  pathname === `/${trajectory._id.toString()}`
                    ? 'bg-gray-200'
                    : ''
                }`}
              >
                <Typography as="h2" className="font-semibold text-primary">
                  {trajectory.robotName}
                </Typography>
                <Typography as="h4" className="text-primary">
                  {formatDate(trajectory.recordingDate)}
                </Typography>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
