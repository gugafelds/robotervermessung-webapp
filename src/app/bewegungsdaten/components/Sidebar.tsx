'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useEffect, useRef, useState } from 'react';

import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { filterBy, formatDate } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

export const Sidebar = () => {
  const { bahnInfo } = useTrajectory();
  const [filteredBahnen, setFilteredBahnen] = useState(bahnInfo);
  const pathname = usePathname();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedItemRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setFilteredBahnen(bahnInfo);
  }, [bahnInfo]);

  useEffect(() => {
    const pathParts = pathname.split('/');
    const currentId = pathParts[pathParts.length - 1];
    setSelectedId(currentId);

    // Scroll zur ausgewählten Bahn nach kurzem Delay
    // (um sicherzustellen, dass das Element gerendert wurde)
    setTimeout(() => {
      if (selectedItemRef.current && scrollContainerRef.current) {
        selectedItemRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }, 100);
  }, [pathname]);

  const handleFilterChange = (filter: string) => {
    const filtered = bahnInfo.filter((bahn) => {
      if (filter.toLowerCase() === 'kalibrierung') {
        return bahn.calibrationRun;
      }
      if (['pick', 'place', 'pick&place'].includes(filter.toLowerCase())) {
        return bahn.pickAndPlaceRun;
      }

      const eventMatch = filter.match(/^(n?p)=(\d+)$/i);
      if (eventMatch) {
        const [, eventType, count] = eventMatch;
        const searchCount = parseInt(count, 10); // Radix parameter hinzugefügt

        if (eventType.toLowerCase() === 'p') {
          return bahn.numberPointsEvents === searchCount;
        }
        if (eventType.toLowerCase() === 'np') {
          return bahn.numberPointsEvents === searchCount;
        }
      }

      const weightMatch = filter.match(/^(w|weight)=(\d*\.?\d+)$/i);
      if (weightMatch) {
        const [, , weight] = weightMatch; // Erstes und zweites Element überspringen
        return bahn.weight === parseFloat(weight);
      }

      const velPPMatch = filter.match(/^(v|vp)=(\d+)$/i);
      if (velPPMatch) {
        const [, , velPP] = velPPMatch; // Erstes und zweites Element überspringen
        return bahn.velocityHandling === velPP;
      }

      return filterBy(filter, [
        bahn.recordFilename || '',
        bahn.bahnID?.toString() || '',
        formatDate(bahn.recordingDate || ''),
      ]);
    });
    setFilteredBahnen(filtered);
  };

  return (
    <div className="flex h-80 w-full flex-col bg-gray-100 px-4 py-2 lg:h-fullscreen lg:max-w-72">
      <div className="flex-col align-middle">
        <div className="relative items-center justify-between">
          <div className={classNames('flex items-end gap-4 pl-1')}>
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              Bewegungsdaten
            </span>
          </div>
        </div>
        <SearchFilter onFilterChange={handleFilterChange} />
        <div className="mt-2 pl-1 text-sm text-gray-600">
          {`${filteredBahnen.length} ${
            filteredBahnen.length === 1 ? 'Bahn' : 'Bahnen'
          }`}
        </div>
      </div>

      <div ref={scrollContainerRef} className="mt-4 overflow-scroll">
        {filteredBahnen.length === 0 ? (
          <div>loading...</div>
        ) : (
          filteredBahnen.map((bahn) => (
            <div
              key={bahn.bahnID?.toString()}
              ref={
                selectedId === bahn.bahnID?.toString() ? selectedItemRef : null
              }
              className={classNames(
                'mt-1 rounded-xl p-1 transition-colors duration-200 ease-in',
                {
                  'bg-gray-300': selectedId === bahn.bahnID?.toString(),
                  'hover:bg-gray-200': selectedId !== bahn.bahnID?.toString(),
                },
              )}
            >
              <div className="flex items-center justify-between">
                <Link
                  href={`/bewegungsdaten/${bahn.bahnID?.toString()}`}
                  className="ml-1"
                >
                  <div>
                    <Typography as="h6" className="font-extrabold text-primary">
                      {`ID: ${bahn.bahnID}`}
                    </Typography>
                    <Typography as="h6" className="font-semibold text-primary">
                      {bahn.recordFilename || 'No filename'}
                    </Typography>
                    <Typography as="h6" className="text-primary">
                      {bahn.recordingDate
                        ? formatDate(bahn.recordingDate)
                        : 'n. a.'}
                    </Typography>
                    <div className="flex">
                      {bahn.pickAndPlaceRun ? (
                        <div className="mx-1 w-fit rounded bg-green-200 px-1">
                          <Typography as="small" className="text-green-950">
                            Pick&Place
                          </Typography>
                        </div>
                      ) : null}
                      {bahn.calibrationRun ? (
                        <div className="w-fit rounded bg-red-200 px-1">
                          <Typography as="small" className="text-red-950">
                            Kalibrierung
                          </Typography>
                        </div>
                      ) : null}
                    </div>
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
