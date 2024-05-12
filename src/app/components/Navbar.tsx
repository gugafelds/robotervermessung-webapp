'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const pathname = usePathname();
  return (
    <header className="h-mobilenavbarheight bg-gray-200 md:h-navbarheight lg:h-navbarheight">
      <div className="flex flex-row flex-wrap items-center px-6 py-4 sm:space-x-2 md:space-x-8 lg:space-x-16">
        <Link href="/">
          <div className="items-center rounded-md p-2">
            <Typography as="h1">robotervermessung</Typography>
          </div>
        </Link>
        <Link href="/dashboard">
          <div className="my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300">
            <Typography as="h2">dashboard</Typography>
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
        <Link href="https://www.lps.ruhr-uni-bochum.de/lps/index.html.de">
          <div className="my-0  items-center rounded-md p-1">
            <Image
              className="m-2"
              src="/lps.png"
              width={70}
              height={70}
              alt="LPS-Logo"
            />
          </div>
        </Link>
      </div>
    </header>
  );
};
