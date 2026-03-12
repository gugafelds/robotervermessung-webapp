'use client';

import Image from 'next/image';
import Link from 'next/link';

import { Typography } from '@/src/components/Typography';

export const ContactCard = () => {
  return (
    <section className="mx-auto my-8 h-fit max-w-lg flex-row items-start text-balance rounded-lg bg-gray-100 text-justify shadow-md">
      <div className="p-4">
        <Typography as="h1">Contact</Typography>

        <div className="mt-2 text-xl font-extrabold">
          Gustavo Barros, M.Sc. <br />
        </div>

        <Typography as="h5">
          Chair of Production Systems <br />
          Ruhr University Bochum <br />
          Industriestraße 38C Room 02/38 <br />
        </Typography>
      </div>

      <div className="flex flex-row sm:ml-auto">
        <Link
          className="items-center rounded-bl-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300"
          href="https://www.lps.ruhr-uni-bochum.de/lps/profil/team/gustavobarros.html.de"
        >
          <Image
            className="m-2 w-auto"
            src="/lps.png"
            width={60}
            height={60}
            alt="LPS Logo"
          />
        </Link>

        <Link
          className="items-center p-1 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300"
          href="https://github.com/gugafelds"
        >
          <Image
            className="m-2 w-auto"
            src="/github.png"
            width={35}
            height={30}
            alt="GitHub Logo"
          />
        </Link>
      </div>
    </section>
  );
};