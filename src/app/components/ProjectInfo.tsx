'use client';

import Link from 'next/link';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <div className="flex-col text-balance sm:p-5 md:p-20 lg:p-40">
      <Typography as="h1">projektinfo</Typography>

      <Typography as="h4">
        Autonome Messung und effiziente Speicherung von
        Industrieroboterbewegungsdaten
      </Typography>
      <div className="my-2 flex w-fit flex-row rounded-lg bg-gray-50 p-4">
        Deutsche Forschungsgemeinschaft - DFG-47-1
        <span className="mx-10 inline-flex">
          Projektnummer:
          <span className="mx-2 inline-flex">
            <Link
              href="https://gepris.dfg.de/gepris/projekt/515675259"
              className="font-extrabold"
            >
              515675259
            </Link>
          </span>
        </span>
      </div>
      <Typography as="h3">
        In diesem Projekt soll die Grundlage für eine
        Robotervermessungsdatenbank geschaffen werden, in der aufgezeichnete
        Bewegungsdaten von Industrierobotern gespeichert werden können. Mit
        einer umfänglichen Datenbank, die stets durch neue Messdaten erweitert
        werden kann, können verschiedenste Anwendungen und Anwendungsszenarien
        unterstützt werden, in denen dann zeit- und kostenintensive individuelle
        Vermessungen vermieden werden.
      </Typography>
      <Typography as="h3">
        Diese Website dient als Remote-Anwendung mit direkter Visualisierung der
        Daten, die in der MongoDB-Atlas-Datenbank gespeichert sind.
      </Typography>
    </div>
  );
};
