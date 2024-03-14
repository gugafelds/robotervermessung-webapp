'use client';

import SettingsIcon from '@heroicons/react/16/solid/CogIcon';
import Link from 'next/link';
import { useState } from 'react';

import { SettingsSlideOver } from '@/src/app/components/SettingsSlideOver';
import { Typography } from '@/src/components/Typography';

export const Navbar = () => {
  const [open, setOpen] = useState(false);

  return (
    <header className="bg-gray-200">
      <div className="mx-auto my-0 flex flex-row items-center px-6 py-3 ">
        <Link href="/">
          <Typography as="h1" className="text-xl font-semibold text-primary">
            robotervermessung // dfg 47-1
          </Typography>
        </Link>
        <button
          type="button"
          className="ml-auto rounded-full px-3 py-0.5 text-base
          text-primary transition hover:bg-gray-300"
          onClick={() => setOpen(!open)}
        >
          <SettingsIcon aria-label="bars" className="size-6" />
        </button>
      </div>
      <SettingsSlideOver open={open} setOpen={setOpen} />
    </header>
  );
};
