'use client';

import Link from 'next/link';

// import { ContactCard } from '@/src/app/components/ContactCard';
import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-auto mt-8 max-w-2xl text-balance px-8 md:max-w-2xl xl:max-w-4xl">
      <div className="mb-2 flex flex-col gap-3">
        <Typography as="h1">projektinfo</Typography>
        <Typography as="h2" className="break-words">
          Autonome Messung und effiziente Speicherung von
          Industrieroboterbewegungsdaten
        </Typography>
      </div>
      <div className="flex flex-col rounded-lg bg-gray-50 p-4 xl:flex-row xl:space-x-52">
        <Typography as="h6" className="block">
          Deutsche Forschungsgemeinschaft - DFG-47-1
        </Typography>
        <Typography as="h6" className="block">
          Projektnummer:{' '}
          <Link
            href="https://gepris.dfg.de/gepris/projekt/515675259"
            className="font-extrabold"
          >
            515675259
          </Link>
        </Typography>
      </div>
      <div className="mt-2">
        <Typography as="p" className="text-justify">
          In diesem Projekt soll die Grundlage für eine
          Robotervermessungsdatenbank geschaffen werden, in der aufgezeichnete
          Bewegungsdaten von Industrierobotern gespeichert werden können. Mit
          einer umfänglichen Datenbank, die stets durch neue Messdaten erweitert
          werden kann, können verschiedenste Anwendungen und Anwendungsszenarien
          unterstützt werden, in denen dann zeit- und kostenintensive
          individuelle Vermessungen vermieden werden.
        </Typography>
        <Typography as="p" className="mt-4">
          Diese Website dient als Remote-Anwendung mit direkter Visualisierung
          der Daten, die in der MongoDB-Atlas-Datenbank gespeichert sind.
        </Typography>
      </div>
    </section>
  );
};
