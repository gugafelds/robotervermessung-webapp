'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const pathname = usePathname();
  return (
    <header className="bg-gray-200">
      <div className="flex flex-row items-center px-6 py-4 sm:space-x-2 md:space-x-8 lg:space-x-16">
        <Link href="/">
          <div className="items-center rounded-md p-2">
            <Typography as="h1">robotervermessung</Typography>
          </div>
        </Link>
        <Link href="/info">
          <div
            className={`items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname === `/info` ? 'bg-gray-300' : ''
            }`}
          >
            <Typography as="h2">info</Typography>
          </div>
        </Link>
        <Link href="/trajectories">
          <div
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.slice(1, 13) === `trajectories` ? 'bg-gray-300' : ''
            }`}
          >
            <Typography as="h2">trajectories</Typography>
          </div>
        </Link>
      </div>
    </header>
  );
};
