'use client';

import React from 'react';

import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { Typography } from '@/src/components/Typography';

import { FrequencyPanel } from './FrequencyPanel';

interface DashboardClientProps {
  filenamesCount: number;
  bahnenCount: number;
  componentCounts: {
    bahnPoseIst: number;
    bahnTwistIst: number;
    bahnAccelIst: number;
    bahnPositionSoll: number;
    bahnOrientationSoll: number;
    bahnJointStates: number;
    bahnEvents: number;
    bahnPoseTrans: number;
  };
  frequencyData: Record<string, string[]>;
  collectionSizes: {
    bahnPoseIst: number;
    bahnTwistIst: number;
    bahnAccelIst: number;
    bahnPositionSoll: number;
    bahnOrientationSoll: number;
    bahnJointStates: number;
    bahnEvents: number;
    bahnPoseTrans: number;
  };
}

export default function DashboardClient({
  filenamesCount,
  bahnenCount,
  componentCounts,
  frequencyData,
  collectionSizes,
}: DashboardClientProps) {
  const totalSize = Object.values(collectionSizes).reduce(
    (sum, size) => sum + size,
    0,
  );

  return (
    <div className="flex">
      <div className="flex-1 p-6">
        <Typography as="h2">Bewegungsdaten</Typography>

        <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <DataCard
            componentName="Roboterbahnen insgesamt"
            value={bahnenCount}
            size={totalSize}
          />
          <DataCard
            componentName="Aufnahmendateien insgesamt"
            value={filenamesCount}
            size={totalSize}
          />
        </div>

        <div className="mb-8">
          <Typography as="h4">Collections</Typography>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <DataCard
              componentName="Roboterpose (Ist)"
              value={componentCounts.bahnPoseIst}
              size={collectionSizes?.bahnPoseIst}
            />
            <DataCard
              componentName="Roboterpose (Transf.)"
              value={componentCounts.bahnPoseTrans}
              size={collectionSizes?.bahnPoseTrans}
            />
            <DataCard
              componentName="Robotergeschwindigkeit (Ist)"
              value={componentCounts.bahnTwistIst}
              size={collectionSizes?.bahnTwistIst}
            />
            <DataCard
              componentName="Roboterbeschleunigung (Ist)"
              value={componentCounts.bahnAccelIst}
              size={collectionSizes?.bahnAccelIst}
            />
            <DataCard
              componentName="Roboterposition (Soll)"
              value={componentCounts.bahnPositionSoll}
              size={collectionSizes?.bahnPositionSoll}
            />
            <DataCard
              componentName="Roboterorientierung (Soll)"
              value={componentCounts.bahnOrientationSoll}
              size={collectionSizes?.bahnOrientationSoll}
            />
            <DataCard
              componentName="Gelenkzustände"
              value={componentCounts.bahnJointStates}
              size={collectionSizes?.bahnJointStates}
            />
            <DataCard
              componentName="Bahn-Zielpunkte"
              value={componentCounts.bahnEvents}
              size={collectionSizes?.bahnEvents}
            />
          </div>
        </div>
      </div>

      <FrequencyPanel frequencyData={frequencyData} />
    </div>
  );
}
