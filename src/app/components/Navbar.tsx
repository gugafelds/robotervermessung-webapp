// src/app/components/Navbar.tsx

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const pathname = usePathname();

  return (
    <header className="h-fit border-b border-gray-500 bg-gray-200 md:h-fit lg:h-fit">
      <div className="flex flex-row flex-wrap items-center gap-10 px-6 py-4">
        <Link href="/">
          <div className="items-center rounded-md p-2">
            <Typography as="h1">RMPD</Typography>
          </div>
        </Link>

        <Link href="/dashboard">
          <Typography
            as="h2"
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.includes('dashboard') ? 'bg-gray-300' : ''
            }`}
          >
            Dashboard
          </Typography>
        </Link>

        <Link href="/motion">
          <Typography
            as="h2"
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.includes('motion') ? 'bg-gray-300' : ''
            }`}
          >
            Motion
          </Typography>
        </Link>

        <Link href="/evaluation">
          <Typography
            as="h2"
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.includes('evaluation') ? 'bg-gray-300' : ''
            }`}
          >
            Evaluation
          </Typography>
        </Link>

        <Link href="/similarity">
          <Typography
            as="h2"
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.includes('similarity') ? 'bg-gray-300' : ''
            }`}
          >
            Similarity Search
          </Typography>
        </Link>

        <Link href="/upload">
          <Typography
            as="h2"
            className={`my-0 items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname.includes('upload') ? 'bg-gray-300' : ''
            }`}
          >
            Upload
          </Typography>
        </Link>

        <Link
          className="ml-auto"
          href="https://www.lps.ruhr-uni-bochum.de/lps/index.html.de"
        >
          <Image
            className="my-0 items-center self-end rounded-md p-1"
            src="/lps.png"
            width={70}
            height={70}
            alt="LPS Logo"
          />
        </Link>
      </div>
    </header>
  );
};
