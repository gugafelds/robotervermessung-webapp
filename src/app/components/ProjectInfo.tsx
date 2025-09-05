'use client';

import Link from 'next/link';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-auto mb-12 mt-8 max-w-xl text-pretty px-8 md:max-w-2xl xl:max-w-4xl">
      <div className="mb-2 flex flex-col gap-3">
        <Typography as="h1">Projektinfo</Typography>
        <Typography as="h2">
          Autonome Messung und effiziente Speicherung von
          Industrieroboterbewegungsdaten
        </Typography>
      </div>
      <div className="mt-2">
        <Typography as="p" className="mt-4">
          Dieses Forschungsprojekt entwickelt die Grundlagen für eine umfassende
          Robotermessdatenbank, die Bewegungsdaten von Industrierobotern
          systematisch erfasst und bereitstellt. Durch den kontinuierlichen
          Aufbau dieser Datenbank können verschiedene Anwendungen und Szenarien
          effizient unterstützt werden.
        </Typography>
        <Typography as="p" className="mt-4">
          Die Datenbank ersetzt zeitaufwändige und kostenintensive
          Einzelmessungen durch einen zentralen Datenpool. Sie ermöglicht den
          quantitativen Vergleich verschiedener Robotersysteme für spezifische
          Anwendungsszenarien und liefert fundierte Entscheidungsgrundlagen -
          beispielsweise zur Identifikation des präzisesten Roboters für einen
          Prozess oder des Systems mit der geringsten Zykluszeit.
        </Typography>
        <Typography as="p" className="mt-4">
          Das im September 2023 gestartete Projekt gliedert sich in vier
          zentrale Arbeitspakete:
        </Typography>
        <div className="mx-6 font-light text-primary">
          <li>
            Entwicklung von Verfahren zum Vergleich von Robotertrajektorien
            unter Berücksichtigung von Abweichungen in Position, Orientierung,
            Geschwindigkeit und Beschleunigung bei verschiedenen
            Roboterkonfigurationen und Abtastraten.
          </li>
          <li>
            Aufbau einer leistungsfähigen Datenbank mit Fokus auf schnellem
            Datenzugriff und erweiterten Suchfunktionen für Teilsequenzen.
          </li>
          <li>
            Entwicklung einer Methodik zur sequentiellen Versuchsplanung für
            Roboterbahnmessungen, einschließlich automatischer Generierung von
            Roboterprogrammen.
          </li>
          <li>
            Datengenerierung und praktische Erprobung der entwickelten Methoden
            sowie Aufbau der operativen Mess- und Speicherinfrastruktur.
          </li>
        </div>
        <Typography as="p" className="mt-5">
          Diese Plattform dient als Remote-Anwendung mit direkter Anbindung an
          die PostgreSQL-Datenbank und bietet interaktive Visualisierung der
          gespeicherten Messdaten.
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
