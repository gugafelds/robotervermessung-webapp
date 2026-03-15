/* eslint-disable no-console */

'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import type { SearchTrajParams } from '@/src/actions/motion.service';
import { searchTrajInfo } from '@/src/actions/motion.service';
import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { formatDate } from '@/src/lib/functions';
import type { TrajInfo } from '@/types/motion.types';
import type { PaginationResult } from '@/types/pagination.types';

import SearchHelpTooltip from './SearchHelpTooltip';

export const Sidebar = () => {
  const [trajInfo, setTrajInfo] = useState<TrajInfo[]>([]);
  const [pagination, setPagination] = useState<PaginationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchParams, setSearchParams] = useState<SearchTrajParams>({
    page: 1,
    pageSize: 20,
  });

  const pathname = usePathname();
  const isAuswertungContext = pathname.startsWith('/evaluation');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedItemRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const isLoadingNextPageRef = useRef(false);

  // Load trajen with current search parameters
  const loadTrajs = useCallback(async (params: SearchTrajParams) => {
    if (params.page && params.page > 1) {
      isLoadingNextPageRef.current = true;
    }

    setIsLoading(true);
    try {
      const { trajInfo: newTrajInfo, pagination: newPagination } =
        await searchTrajInfo(params);

      // Wenn page > 1, dann zur bestehenden Liste hinzufügen, sonst ersetzen
      if (params.page && params.page > 1) {
        // Prüfe auf Duplikate
        setTrajInfo((prev) => {
          const existingIds = new Set(
            prev.map((traj) => traj.trajID?.toString()),
          );
          const uniqueNewTrajs = newTrajInfo.filter(
            (traj) => !existingIds.has(traj.trajID?.toString()),
          );
          return [...prev, ...uniqueNewTrajs];
        });
      } else {
        setTrajInfo(newTrajInfo);
      }

      setPagination(newPagination);
      setCurrentPage(params.page || 1);
    } catch (error) {
      console.error('Failed to load trajectory data:', error);
    } finally {
      setIsLoading(false);
      isLoadingNextPageRef.current = false;
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadTrajs(searchParams);
    // We want this to run only once, so we're ignoring the dependencies
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load next page for infinite scroll
  const loadNextPage = useCallback(() => {
    // Use ref to prevent multiple simultaneous calls
    if (pagination?.hasNext && !isLoading && !isLoadingNextPageRef.current) {
      const nextPageParams = { ...searchParams, page: currentPage + 1 };
      setSearchParams(nextPageParams);
      loadTrajs(nextPageParams);
    }
  }, [pagination, isLoading, currentPage, searchParams, loadTrajs]);

  useEffect(() => {
    const pathParts = pathname.split('/');
    const currentId = pathParts[pathParts.length - 1];
    setSelectedId(currentId);

    setTimeout(() => {
      if (selectedItemRef.current && scrollContainerRef.current) {
        selectedItemRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }
    }, 100);
  }, [pathname]);

  // Intersection Observer für Infinite Scrolling
  useEffect(() => {
    if (!pagination?.hasNext || isLoading) {
      return undefined; // Explicit return for consistent-return rule
    }

    const handleIntersection = (entries: any) => {
      const [entry] = entries;
      if (
        entry.isIntersecting &&
        pagination?.hasNext &&
        !isLoadingNextPageRef.current
      ) {
        setTimeout(() => {
          loadNextPage();
        }, 100);
      }
    };

    const observer = new IntersectionObserver(handleIntersection, {
      threshold: 0.1,
      rootMargin: '0px 0px 200px 0px', // Trigger a bit before reaching the bottom
    });

    const currentLoadMoreRef = loadMoreRef.current;
    if (currentLoadMoreRef) {
      observer.observe(currentLoadMoreRef);
    }

    return () => {
      observer.disconnect();
    };
  }, [pagination?.hasNext, isLoading, loadNextPage]);

  // Parse filter string to search parameters
  const parseFilterToSearchParams = (filter: string): SearchTrajParams => {
    const params: SearchTrajParams = { page: 1, pageSize: 20 };

    if (!filter.trim()) {
      return params;
    }

    const filterParts = filter.trim().split(/\s+/);

    for (const part of filterParts) {
      // Numerische ID
      if (/^\d+$/.test(part)) {
        params.query = part;
      } else {
        // Alle Pattern gleichzeitig prüfen
        const eventMatch = part.match(/^(n|np)=(\d+)$/i);
        const weightMatch = part.match(/^(w|weight)=(\d*\.?\d+)$/i);
        const velMatch = part.match(/^(v|velocity)=(\d*\.?\d+)$/i);
        const dateMatch = part.match(/^d=(.+)$/i);
        const sidtwMatch = part.match(/^(s|sidtw)=(\d*\.?\d+)$/i);

        if (eventMatch) {
          const [, , count] = eventMatch;
          params.pointsEvents = parseInt(count, 10);
        } else if (weightMatch) {
          const [, , weight] = weightMatch;
          params.weight = parseFloat(weight);
        } else if (velMatch) {
          const [, , velocity] = velMatch;
          params.settedVelocity = parseFloat(velocity);
        } else if (dateMatch) {
          const [, dateValue] = dateMatch;
          params.recordingDate = dateValue;
        } else if (sidtwMatch) {
          const [, , distance] = sidtwMatch;
          params.sidtwDistance = parseFloat(distance);
        } else if (!params.query) {
          params.query = part;
        }
      }
    }

    return params;
  };

  const handleFilterChange = useCallback(
    (filter: string) => {
      // Filter in Suchparameter umwandeln
      const newSearchParams = parseFilterToSearchParams(filter);
      setSearchParams(newSearchParams);

      // Erste Seite mit neuen Suchparametern laden
      setTrajInfo([]); // Liste zurücksetzen
      loadTrajs(newSearchParams);
    },
    [loadTrajs],
  );

  return (
    <div className="flex h-80 w-full flex-col border-r border-gray-500 bg-gray-100 px-4 py-2 lg:h-fullscreen lg:max-w-72">
      <div className="flex-col align-middle">
        <div className="relative items-center justify-between">
          <div className={classNames('flex items-end gap-4 pl-1')}>
            <LogoIcon width={30} color="#003560" />
            <span className="mt-2 text-2xl font-semibold text-primary">
              Motion data
            </span>
          </div>
        </div>
        <div className="relative flex place-items-end">
          <SearchFilter onFilterChange={handleFilterChange} />
          <SearchHelpTooltip />
        </div>
        {!isLoading && (
          <div className="mt-2 pl-1 text-sm text-gray-600">
            {`${trajInfo.length} ${
              trajInfo.length === 1 ? 'Traj.' : ''
            }${pagination ? ` of ${pagination.total} trajectories` : ''}`}
          </div>
        )}
      </div>

      <div ref={scrollContainerRef} className="mt-4 overflow-scroll">
        {trajInfo.length === 0 && isLoading && (
          <div className="flex justify-center py-4">
            <div className="size-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}

        {trajInfo.length === 0 && !isLoading && (
          <div className="py-4 text-center text-gray-500">
            No trajectories found
          </div>
        )}

        {trajInfo.length > 0 && (
          <>
            {trajInfo.map((traj) => (
              <div
                key={traj.trajID?.toString()}
                ref={
                  selectedId === traj.trajID?.toString()
                    ? selectedItemRef
                    : null
                }
                className={classNames(
                  'mt-1 rounded-xl p-1 transition-colors duration-200 ease-in',
                  {
                    'bg-gray-300': selectedId === traj.trajID?.toString(),
                    'hover:bg-gray-200': selectedId !== traj.trajID?.toString(),
                  },
                )}
              >
                <div className="flex items-center justify-between">
                  <Link
                    href={
                      isAuswertungContext
                        ? `/evaluation/${traj.trajID}`
                        : `/motion/${traj.trajID}`
                    }
                    className="ml-1"
                  >
                    <div>
                      <Typography
                        as="h6"
                        className="font-extrabold text-primary"
                      >
                        {`ID: ${traj.trajID}`}
                      </Typography>
                      <Typography
                        as="h6"
                        className="font-semibold text-primary"
                      >
                        {traj.recordFilename || 'No filename'}
                      </Typography>
                      <Typography as="h6" className="text-primary">
                        {traj.recordingDate
                          ? formatDate(traj.recordingDate)
                          : 'n. a.'}
                      </Typography>
                    </div>
                  </Link>
                </div>
              </div>
            ))}

            {/* Invisible loader element at the bottom for infinite scroll */}
            {pagination?.hasNext && (
              <div ref={loadMoreRef} className="py-4">
                {isLoading && (
                  <div className="flex justify-center">
                    <div className="size-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
