'use client';

import Link from 'next/link';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-auto mt-8 max-w-xl text-pretty px-8 md:max-w-2xl xl:max-w-4xl">
      <div className="mb-2 flex flex-col gap-3">
        <Typography as="h1">projektinfo</Typography>
        <Typography as="h2">
          Autonome Messung und effiziente Speicherung von
          Industrieroboterbewegungsdaten
        </Typography>
      </div>
      <div className="mt-2">
        <Typography as="p" className="mt-4">
          Ziel dieses Projektes ist es, die Grundlagen für eine
          Robotermessdatenbank zu schaffen, in der Bewegungsdaten von
          Industrierobotern gespeichert werden können. Durch den Aufbau einer
          umfassenden Datenbank, die kontinuierlich mit neuen Messdaten
          angereichert werden kann, können verschiedene Anwendungen und
          Szenarien unterstützt werden. Dadurch entfällt die Notwendigkeit von
          zeitaufwändigen und teuren Einzelmessungen.
        </Typography>
        <Typography as="p" className="mt-4">
          Das Projekt startet im September 2023 und umfasst vier Meilensteine:
          <li className="mt-4">
            Entwicklung einer Methode für den Vergleich von Robotertrajektorien
            unter Berücksichtigung von Abweichungen in der Position, der
            Orientierung, der Geschwindigkeit und der Beschleunigung bei
            verschiedenen Konfigurationen von Roboterarmen und unterschiedlichen
            Abtastraten.
          </li>
          <li className="mt-2">
            Aufbau einer Datenbank zur Speicherung und Bereitstellung von
            Transaktionsdaten mit Schwerpunkt auf schnellem Datenzugriff und der
            Möglichkeit, nach Teilsequenzen zu suchen.
          </li>
          <li className="mt-2">
            Entwicklung einer Methode zur sequentiellen Versuchsplanung für
            Roboterbahnmessungen, einschließlich der automatischen Generierung
            von Roboterprogrammen für autonome Messungen.
          </li>
          <li className="mt-2">
            Erfolgreiche Datengenerierung für die entwickelten Methoden und
            Algorithmen zur autonomen Messung sowie Speicherung und
            Bereitstellung der Messdaten
          </li>
        </Typography>
        <Typography as="p" className="mt-5">
          Diese Webseite dient als Remote-Anwendung mit direkter Visualisierung
          der Daten, die in der MongoDB-Datenbank gespeichert sind.
        </Typography>
      </div>

      <div className="mt-8 flex flex-col rounded-lg bg-gray-100 p-4">
        <Typography as="h6" className="block">
          Das Forschungsprojekt wird von der Deutschen Forschungsgemeinschaft
          (DFG) unter der Projektnummer{' '}
          <Link
            href="https://gepris.dfg.de/gepris/projekt/515675259"
            className="border-b-2 border-dotted border-b-black font-extrabold"
          >
            515675259
          </Link>{' '}
          gefördert.
        </Typography>
      </div>
    </section>
  );
};
