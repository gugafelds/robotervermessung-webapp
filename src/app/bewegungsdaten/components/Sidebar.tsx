/* eslint-disable no-console */

'use client';

import LogoIcon from '@heroicons/react/20/solid/ListBulletIcon';
import classNames from 'classnames';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import type { SearchBahnParams } from '@/src/actions/bewegungsdaten.service';
import { searchBahnInfo } from '@/src/actions/bewegungsdaten.service';
import SearchFilter from '@/src/components/SearchFilter';
import { Typography } from '@/src/components/Typography';
import { formatDate } from '@/src/lib/functions';
import type { BahnInfo } from '@/types/bewegungsdaten.types';
import type { PaginationResult } from '@/types/pagination.types';

export const Sidebar = () => {
  const [bahnInfo, setBahnInfo] = useState<BahnInfo[]>([]);
  const [pagination, setPagination] = useState<PaginationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchParams, setSearchParams] = useState<SearchBahnParams>({
    page: 1,
    pageSize: 20,
  });

  const pathname = usePathname();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedItemRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const isLoadingNextPageRef = useRef(false); // Ref to track loading state between renders

  // Load bahnen with current search parameters
  const loadBahnen = useCallback(async (params: SearchBahnParams) => {
    if (params.page && params.page > 1) {
      isLoadingNextPageRef.current = true;
    }

    setIsLoading(true);
    try {
      const { bahnInfo: newBahnInfo, pagination: newPagination } =
        await searchBahnInfo(params);

      // Wenn page > 1, dann zur bestehenden Liste hinzufügen, sonst ersetzen
      if (params.page && params.page > 1) {
        // Prüfe auf Duplikate
        setBahnInfo((prev) => {
          const existingIds = new Set(
            prev.map((bahn) => bahn.bahnID?.toString()),
          );
          const uniqueNewBahnen = newBahnInfo.filter(
            (bahn) => !existingIds.has(bahn.bahnID?.toString()),
          );
          return [...prev, ...uniqueNewBahnen];
        });
      } else {
        setBahnInfo(newBahnInfo);
      }

      setPagination(newPagination);
      setCurrentPage(params.page || 1);
    } catch (error) {
      console.error('Failed to load bahn data:', error);
    } finally {
      setIsLoading(false);
      isLoadingNextPageRef.current = false;
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadBahnen(searchParams);
    // We want this to run only once, so we're ignoring the dependencies
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load next page for infinite scroll
  const loadNextPage = useCallback(() => {
    // Use ref to prevent multiple simultaneous calls
    if (pagination?.hasNext && !isLoading && !isLoadingNextPageRef.current) {
      const nextPageParams = { ...searchParams, page: currentPage + 1 };
      setSearchParams(nextPageParams);
      loadBahnen(nextPageParams);
    }
  }, [pagination, isLoading, currentPage, searchParams, loadBahnen]);

  // Ausgewählte Bahn-ID aus dem Pfad extrahieren
  useEffect(() => {
    const pathParts = pathname.split('/');
    const currentId = pathParts[pathParts.length - 1];
    setSelectedId(currentId);

    // Scroll zur ausgewählten Bahn nach kurzem Delay
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
    // Only set up observer if there's more to load and we're not already loading
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
        // Add a small delay to prevent accidental double-triggering
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
  const parseFilterToSearchParams = (filter: string): SearchBahnParams => {
    const params: SearchBahnParams = { page: 1, pageSize: 20 };

    if (!filter.trim()) {
      return params;
    }

    // Überprüfe, ob es eine numerische ID ist
    if (/^\d+$/.test(filter.trim())) {
      params.query = filter.trim();
      console.log('Suche nach ID:', params.query);
      return params;
    }

    if (filter.toLowerCase() === 'kalibrierung') {
      params.calibration = true;
      return params;
    }

    if (['pick', 'place', 'pick&place'].includes(filter.toLowerCase())) {
      params.pickPlace = true;
      return params;
    }

    const eventMatch = filter.match(/^(n|np)=(\d+)$/i);
    if (eventMatch) {
      const [, , count] = eventMatch;
      params.pointsEvents = parseInt(count, 10);
      return params;
    }

    const weightMatch = filter.match(/^(w|weight)=(\d*\.?\d+)$/i);
    if (weightMatch) {
      const [, , weight] = weightMatch;
      params.weight = parseFloat(weight);
      return params;
    }

    const velPPMatch = filter.match(/^(v|vp)=(\d+)$/i);
    if (velPPMatch) {
      const [, , velPP] = velPPMatch;
      params.velocity = parseInt(velPP, 10);
      return params;
    }

    // Default: Freitext-Suche
    params.query = filter.trim();
    console.log('Freitext-Suche:', params.query);
    return params;
  };

  const handleFilterChange = useCallback(
    (filter: string) => {
      // Filter in Suchparameter umwandeln
      const newSearchParams = parseFilterToSearchParams(filter);
      setSearchParams(newSearchParams);

      // Erste Seite mit neuen Suchparametern laden
      setBahnInfo([]); // Liste zurücksetzen
      loadBahnen(newSearchParams);
    },
    [loadBahnen],
  );

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
          {`${bahnInfo.length} ${
            bahnInfo.length === 1 ? 'Bahn' : 'Bahnen'
          }${pagination ? ` von ${pagination.total}` : ''}`}
        </div>
      </div>

      <div ref={scrollContainerRef} className="mt-4 overflow-scroll">
        {/* Zustand: Lädt initial */}
        {bahnInfo.length === 0 && isLoading && (
          <div className="flex justify-center py-4">
            <div className="size-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}

        {/* Zustand: Keine Daten gefunden */}
        {bahnInfo.length === 0 && !isLoading && (
          <div className="py-4 text-center text-gray-500">
            Keine Bahnen gefunden
          </div>
        )}

        {/* Zustand: Daten anzeigen */}
        {bahnInfo.length > 0 && (
          <>
            {bahnInfo.map((bahn) => (
              <div
                key={bahn.bahnID?.toString()}
                ref={
                  selectedId === bahn.bahnID?.toString()
                    ? selectedItemRef
                    : null
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
