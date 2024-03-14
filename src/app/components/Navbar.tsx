'use client';

import BarsIcon from '@heroicons/react/16/solid/Bars4Icon';
import Link from 'next/link';
import { useState } from 'react';

import { TrajectoriesSlideOver } from '@/src/app/components/TrajectoriesSlideOver';
import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const [open, setOpen] = useState(false);

  return (
    <header className="bg-gray-200">
      <div className="mx-auto my-0 flex -0 flex-row items-center px-6 py-3 ">
        <Link href="/">
          <Typography as="h1" className="text-xl font-semibold text-primary">
            robotervermessung // dfg 47-1
          </Typography>
        </Link>
        <button
          type="button"
          className="ml-auto rounded-full px-3 py-0.5 text-base
          text-primary transition hover:bg-gray-200"
          onClick={() => setOpen(!open)}
        >
          <BarsIcon aria-label="bars" className="size-6" />
        </button>
      </div>
      <TrajectoriesSlideOver open={open} setOpen={setOpen} />
    </header>
  );
};
