'use client';

import classNames from 'classnames';
import { useState } from 'react';

import { CollapseIcon } from '@/src/components/CollapseIcon';
import LogoIcon from '@/src/components/LogoIcon';

export const Sidebar = () => {
  const [toggleCollapse, setToggleCollapse] = useState(false);
  const [isCollapsible, setIsCollapsible] = useState(false);

  const onMouseOver = () => {
    setIsCollapsible(!isCollapsible);
  };

  const wrapperClasses = classNames(
    'h-screen px-4 pt-8 pb-4 bg-gray-100 flex justify-between flex-col',
    {
      'w-80': !toggleCollapse,
      'w-20': toggleCollapse,
    },
  );

  const collapseIconClasses = classNames(
    'p-4 rounded bg-light-lighter absolute right-0',
    {
      'rotate-180': toggleCollapse,
    },
  );

  const handleSidebarToggle = () => {
    setToggleCollapse(!toggleCollapse);
  };

  return (
    <div
      className={wrapperClasses}
      onMouseEnter={onMouseOver}
      onMouseLeave={onMouseOver}
      style={{ transition: 'width 300ms cubic-bezier(0.2, 0, 0, 1) 0s' }}
    >
      <div className="flex flex-col">
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4 pl-1">
            <LogoIcon />
            <span
              className={classNames('mt-2 text-lg font-medium text-text', {
                hidden: toggleCollapse,
              })}
            >
              trajectories
            </span>
          </div>
          {isCollapsible && (
            <button
              type="button"
              aria-label="collapse"
              className={collapseIconClasses}
              onClick={handleSidebarToggle}
            >
              <CollapseIcon />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
