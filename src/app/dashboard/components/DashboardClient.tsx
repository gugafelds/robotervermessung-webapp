/* eslint-disable no-console */

'use client';

import React from 'react';

import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { Typography } from '@/src/components/Typography';

interface DashboardClientProps {
  filenamesCount: number;
  bahnenCount: number;
  componentCounts: {
    bahnPoseIst: number;
    bahnTwistIst: number;
    bahnTwistSoll: number;
    bahnAccelIst: number;
    bahnPositionSoll: number;
    bahnOrientationSoll: number;
    bahnJointStates: number;
    bahnEvents: number;
    bahnPoseTrans: number;
  };
  analysisCounts?: {
    infoDFD: number;
    infoDTW: number;
    infoEA: number;
    infoLCSS: number;
    infoSIDTW: number;
  };
}

export default function DashboardClient({
  filenamesCount,
  bahnenCount,
  componentCounts,
  analysisCounts,
}: DashboardClientProps) {
  console.log(analysisCounts);
  return (
    <div className="justify-center p-6">
      <Typography as="h2">Bewegungsdaten</Typography>

      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <DataCard componentName="Roboterbahnen insgesamt" value={bahnenCount} />
        <DataCard
          componentName="Aufnahmendateien insgesamt"
          value={filenamesCount}
        />
      </div>

      <div className="mb-8">
        <Typography as="h4">Bahndaten</Typography>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DataCard
            componentName="Roboterpose (Ist)"
            value={componentCounts.bahnPoseIst}
          />
          <DataCard
            componentName="Roboterpose (Transf.)"
            value={componentCounts.bahnPoseTrans}
          />
          <DataCard
            componentName="Robotergeschwindigkeit (Ist)"
            value={componentCounts.bahnTwistIst}
          />
          <DataCard
            componentName="Robotergeschwindigkeit (Soll)"
            value={componentCounts.bahnTwistSoll}
          />
          <DataCard
            componentName="Roboterbeschleunigung (Ist)"
            value={componentCounts.bahnAccelIst}
          />
          <DataCard
            componentName="Roboterposition (Soll)"
            value={componentCounts.bahnPositionSoll}
          />
          <DataCard
            componentName="Roboterorientierung (Soll)"
            value={componentCounts.bahnOrientationSoll}
          />
          <DataCard
            componentName="Gelenkzustände"
            value={componentCounts.bahnJointStates}
          />
          <DataCard
            componentName="Bahn-Zielpunkte"
            value={componentCounts.bahnEvents}
          />
        </div>
      </div>

      {analysisCounts && (
        <div className="mb-8">
          <Typography as="h4">Auswertungsdaten</Typography>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <DataCard
              componentName="Euklidischer Abstand"
              value={analysisCounts.infoEA}
            />
            <DataCard
              componentName="SIDTW-Analyse"
              value={analysisCounts.infoSIDTW}
            />
            <DataCard
              componentName="DTW-Analyse"
              value={analysisCounts.infoDTW}
            />
            <DataCard
              componentName="DFD-Analyse"
              value={analysisCounts.infoDFD}
            />

            <DataCard
              componentName="LCSS-Analyse"
              value={analysisCounts.infoLCSS}
            />
          </div>
        </div>
      )}
    </div>
  );
}
