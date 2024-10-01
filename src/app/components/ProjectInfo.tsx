'use client';

import Link from 'next/link';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-auto mb-12 mt-8 max-w-xl text-pretty px-8 md:max-w-2xl xl:max-w-4xl">
      <div className="mb-2 flex flex-col gap-3">
        <Typography as="h1">projektinfo</Typography>
        <Typography as="h2">
          Autonome Messung und effiziente Speicherung von
          Industrieroboterbewegungsdaten
        </Typography>
      </div>
      <div className="mt-2">
        <Typography as="p" className="mt-4">
          Das Ziel dieses Forschungsprojektes ist die Schaffung der Grundlagen
          für eine Robotermessdatenbank, in der Bewegungsdaten von
          Industrierobotern gespeichert werden können. Der Aufbau einer
          umfassenden Datenbank, die kontinuierlich mit neuen Messdaten
          angereichert werden kann, ermöglicht die Unterstützung verschiedener
          Anwendungen und Szenarien.
        </Typography>
        <Typography as="p" className="mt-4">
          Dadurch entfällt die Notwendigkeit von zeitaufwändigen und
          kostenintensiven Einzelmessungen. Des Weiteren soll ein quantitativer
          Vergleich verschiedener Robotersysteme für ein spezifisches
          Anwendungsszenario möglich sein. Das Datenbanksystem soll
          beispielsweise den Roboter mit der höchsten Genauigkeit für den
          Prozess oder aber auch den Roboter mit der geringsten Zykluszeit
          liefern.
        </Typography>
        <Typography as="p" className="mt-4">
          Das Projekt hat im September 2023 gestartet und umfasst vier
          Meilensteine:
        </Typography>
        <div className="mx-6 font-light text-primary">
          <li>
            Entwicklung einer Methode für den Vergleich von Robotertrajektorien
            unter Berücksichtigung von Abweichungen in der Position, der
            Orientierung, der Geschwindigkeit und der Beschleunigung bei
            verschiedenen Konfigurationen von Roboterarmen und unterschiedlichen
            Abtastraten.
          </li>
          <li>
            Aufbau einer Datenbank zur Speicherung und Bereitstellung von
            Transaktionsdaten mit Schwerpunkt auf schnellem Datenzugriff und der
            Möglichkeit, nach Teilsequenzen zu suchen.
          </li>
          <li>
            Entwicklung einer Methode zur sequentiellen Versuchsplanung für
            Roboterbahnmessungen, einschließlich der automatischen Generierung
            von Roboterprogrammen für autonome Messungen.
          </li>
          <li>
            Erfolgreiche Datengenerierung für die entwickelten Methoden und
            Algorithmen zur autonomen Messung sowie Speicherung und
            Bereitstellung der Messdaten
          </li>
        </div>
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
