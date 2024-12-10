'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { filterBy, formatDate } from '@/src/lib/functions';
import { useAuswertung } from '@/src/providers/auswertung.provider';
import type { BahnInfo } from '@/types/bewegungsdaten.types';

export const Sidebar = () => {
  const { auswertungInfo } = useAuswertung();
  const [filteredBahnen, setFilteredBahnen] = useState<BahnInfo[]>([]);
  const pathname = usePathname();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (auswertungInfo?.bahn_info) {
      setFilteredBahnen(auswertungInfo.bahn_info);
    }
  }, [auswertungInfo]);

  useEffect(() => {
    const pathParts = pathname.split('/');
    const currentId = pathParts[pathParts.length - 1];
    setSelectedId(currentId);
  }, [pathname]);

  const handleFilterChange = (filter: string) => {
    if (!auswertungInfo?.bahn_info) return;

    const filtered = auswertungInfo.bahn_info.filter((bahn) =>
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
              Auswertungsdaten
            </span>
          </div>
        </div>
        <SearchFilter onFilterChange={handleFilterChange} />
      </div>

      <div className="mt-4 overflow-scroll">
        {filteredBahnen.length === 0 ? (
          <div>loading...</div>
        ) : (
          filteredBahnen.map((bahn) => {
            return (
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
                    href={`/auswertung/${bahn.bahnID?.toString()}`}
                    className="ml-2 flex-1"
                  >
                    <div>
                      <Typography
                        as="h6"
                        className="font-extrabold text-primary"
                      >
                        {`ID: ${bahn.bahnID}`}
                      </Typography>
                      <Typography
                        as="h6"
                        className="font-semibold text-primary"
                      >
                        {bahn.recordFilename || 'No filename'}
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
            );
          })
        )}
      </div>
    </div>
  );
};
