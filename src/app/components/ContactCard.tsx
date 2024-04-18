'use client';

import Image from 'next/image';
import Link from 'next/link';

import { Typography } from '@/src/components/Typography';

export const ContactCard = () => {
  return (
    <section className="my-8 flex h-full flex-row flex-wrap items-start text-balance rounded-lg bg-gray-100 p-4 text-justify shadow-md">
      <div>
        <Typography as="h3">kontakt</Typography>

        <div className="mt-2 text-xl font-extrabold">
          Gustavo Barros, M. Sc. <br />
        </div>

        <Typography as="h5">
          Lehrstuhl für Produktionssysteme <br />
          Ruhr-Universität Bochum <br />
          Industriestraße 38C Raum 02/38 <br />
        </Typography>
      </div>
      <div className="ml-0 flex flex-row flex-wrap sm:ml-auto sm:flex-col">
        <Link
          className="items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300"
          href="https://www.lps.ruhr-uni-bochum.de/lps/profil/team/gustavobarros.html.de"
        >
          <Image
            className="m-2"
            src="/lps.png"
            width={60}
            height={60}
            alt="LPS-Logo"
          />
        </Link>
        <Link
          className="items-center rounded-md p-2 transition-colors duration-200 ease-in betterhover:hover:bg-gray-300"
          href="https://github.com/gugafelds"
        >
          <Image
            className="m-2"
            src="/github.png"
            width={35}
            height={30}
            alt="Github-Logo"
          />
        </Link>
      </div>
    </section>
  );
};
