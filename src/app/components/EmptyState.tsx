'use client';

import Image from 'next/image';

import { Typography } from '@/src/components/Typography';

export const EmptyState = () => {
  return (
    <section className="mt-12 flex h-screen flex-col items-center">
      <div className="max-w-44">
        <Image
          src="/empty-state-icon.svg"
          alt="Empty State"
          layout="responsive"
          width={500}
          height={500}
        />
      </div>
      <Typography
        as="h1"
        className="mt-4 max-w-sm text-center text-lg text-gray-600"
      >
        Bitte wählen Sie Ihren Roboter im Hamburger-Menü oben aus.
      </Typography>
    </section>
  );
};
