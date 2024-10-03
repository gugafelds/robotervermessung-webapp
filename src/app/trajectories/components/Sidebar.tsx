'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { filterBy, formatDate } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const Sidebar = () => {
  const { bahnInfo } = useTrajectory();
  const [filteredBahnen, setFilteredBahnen] = useState(bahnInfo);
  const pathname = usePathname();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setFilteredBahnen(bahnInfo);
  }, [bahnInfo]);

  useEffect(() => {
    const pathParts = pathname.split('/');
    const currentId = pathParts[pathParts.length - 1];
    setSelectedId(currentId);
  }, [pathname]);

  const handleFilterChange = (filter: string) => {
    const filtered = bahnInfo.filter((bahn) =>
      filterBy(filter, [
        bahn.recordFilename || '',
        bahn.bahnID?.toString() || '',
        formatDate(bahn.recordingDate || ''),
      ]),
    );
    setFilteredBahnen(filtered);
  };

  return (
    <div className="flex h-80 w-full flex-col bg-gray-100 px-4 py-2 lg:h-fullscreen lg:max-w-80">
      <div className="flex flex-col align-middle">
        <div className="relative flex items-center justify-between">
          <div className={classNames('flex items-end gap-4 pl-1')}>
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              bewegungsdaten
            </span>
          </div>
        </div>
        <SearchFilter onFilterChange={handleFilterChange} />
      </div>

      <div className="mt-4 overflow-scroll">
        {filteredBahnen.length === 0 ? (
          <div>loading...</div>
        ) : (
          filteredBahnen.map((bahn) => (
            <div
              key={bahn.bahnID?.toString()}
              className={classNames(
                'mt-1 rounded-xl p-3 transition-colors duration-200 ease-in',
                {
                  'bg-gray-300': selectedId === bahn.bahnID?.toString(),
                  'hover:bg-gray-200': selectedId !== bahn.bahnID?.toString(),
                },
              )}
            >
              <div className="flex items-center justify-between">
                <Link
                  href={`/trajectories/${bahn.bahnID?.toString()}`}
                  className="ml-2 flex-1"
                >
                  <div>
                    <Typography as="h6" className="font-extrabold text-primary">
                      {bahn.recordFilename || 'No filename'}
                    </Typography>
                    <Typography as="h6" className="font-semibold text-primary">
                      {`ID: ${bahn.bahnID}`}
                    </Typography>
                    <Typography as="h6" className="text-primary">
                      {bahn.recordingDate
                        ? formatDate(bahn.recordingDate)
                        : 'n. a.'}
                    </Typography>
                  </div>
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
