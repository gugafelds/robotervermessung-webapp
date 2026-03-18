'use client';

import Link from 'next/link';
import React from 'react';

import { Typography } from '@/src/components/Typography';

export const ProjectInfo = () => {
  return (
    <section className="mx-auto mb-12 mt-8 max-w-xl text-pretty px-8 md:max-w-2xl xl:max-w-4xl">
      <div className="mb-2 flex flex-col gap-3">
        <Typography as="h1">Info</Typography>
        <Typography as="h2">
          Autonomous Measurement and Efficient Storage of Industrial Robot
          Motion Data
        </Typography>
      </div>

      <div className="mt-2">
        <Typography as="p" className="mt-4">
          This research project develops the foundation for a comprehensive
          robot measurement database that systematically captures and provides
          motion data from industrial robots. By continuously expanding this
          database, a wide range of applications and scenarios can be
          efficiently supported.
        </Typography>

        <Typography as="p" className="mt-4">
          The database replaces time-consuming and costly individual
          measurements with a centralized data pool. It enables quantitative
          comparison of different robotic systems for specific application
          scenarios and provides a reliable basis for decision-making — for
          example, identifying the most precise robot for a process or the
          system with the shortest cycle time.
        </Typography>

        <Typography as="p" className="mt-4">
          The project, which started in September 2023, is structured into four
          main work packages:
        </Typography>

        <div className="mx-6 font-light text-primary">
          <li>
            Development of methods for comparing robot trajectories while
            considering deviations in position, orientation, velocity, and
            acceleration across different robot configurations and sampling
            rates.
          </li>
          <li>
            Construction of a high-performance database with a focus on fast
            data access and advanced search functions for trajectory
            subsequences.
          </li>
          <li>
            Development of a methodology for sequential experiment planning for
            robot trajectory measurements, including automatic generation of
            robot programs.
          </li>
          <li>
            Data generation and practical evaluation of the developed methods,
            as well as the establishment of the operational measurement and
            storage infrastructure.
          </li>
        </div>

        <Typography as="p" className="mt-5">
          This platform serves as a remote application with direct access to the
          PostgreSQL database and provides interactive visualization of the
          stored measurement data.
        </Typography>
      </div>

      <div className="mt-8 flex flex-col rounded-lg bg-gray-100 p-4">
        <Typography as="h6" className="block">
          The research project is funded by the German Research Foundation (DFG)
          under project number{' '}
          <Link
            href="https://gepris.dfg.de/gepris/projekt/515675259"
            className="border-b-2 border-dotted border-b-black font-extrabold"
          >
            515675259
          </Link>
          .
        </Typography>
      </div>
    </section>
  );
};
