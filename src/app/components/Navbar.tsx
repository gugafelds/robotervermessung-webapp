'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const pathname = usePathname();
  return (
    <header className="bg-gray-200">
      <div className="mx-auto my-0 flex flex-row items-center px-6 py-4">
        <Link href="/">
          <div
            className={`flex flex-row items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
              pathname === `/` ? 'bg-gray-300' : ''
            }`}
          >
            <Typography as="h1">robotervermessung // dfg 47-1</Typography>
          </div>
        </Link>
        <Link href="/trajectories">
          <div
            className={`mx-20 my-0 flex flex-row items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300 ${
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
