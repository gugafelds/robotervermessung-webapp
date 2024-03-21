'use client';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-10 mt-8 flex h-screen flex-col items-start text-justify">
      <Typography as="h1" className="py-5">
        projektinfo
      </Typography>

      <Typography as="h4">
        Autonome Messung und effiziente Speicherung von
        Industrieroboterbewegungsdaten{' '}
      </Typography>
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
        Daten, die in der MongoDB-Atlas-Datenbank gespeichert sind.{' '}
      </Typography>
    </section>
  );
};
