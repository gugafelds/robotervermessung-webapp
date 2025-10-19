/* eslint-disable react/button-has-type */

'use client';

import { AccuracyCard } from '@/src/app/dashboard/components/AccuracyCard';
import { AccuracyTimeline } from '@/src/app/dashboard/components/AccuracyTimeline';
import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { DistributionCharts } from '@/src/app/dashboard/components/DistributionCharts';
import { ParameterCorrelation } from '@/src/app/dashboard/components/ParameterCorrelation';
import { PerformersTable } from '@/src/app/dashboard/components/PerformersTable';
import { WorkareaPlot } from '@/src/app/dashboard/components/WorkareaPlot';
import { Typography } from '@/src/components/Typography';
import type { PerformerData } from '@/types/dashboard.types';

interface DashboardClientProps {
  filenamesCount: number;
  bahnenCount: number;
  medianSIDTW?: number;
  meanSIDTW?: number;
  bestPerformers?: PerformerData[]; // NEU
  worstPerformers?: PerformerData[]; // NEU
}

export default function DashboardClient({
  filenamesCount,
  bahnenCount,
  medianSIDTW,
  meanSIDTW,
  bestPerformers,
  worstPerformers,
}: DashboardClientProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-1 lg:grid-cols-2">
      <div>
        <Typography as="h2">Bewegungsdaten</Typography>
        <div className="my-2 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <DataCard
            componentName="Roboterbahnen insgesamt"
            value={bahnenCount}
          />
          <DataCard
            componentName="Aufnahmendateien insgesamt"
            value={filenamesCount}
          />
          <AccuracyCard medianSIDTW={medianSIDTW} meanSIDTW={meanSIDTW} />
        </div>
        <DistributionCharts />
      </div>

      <PerformersTable
        bestPerformers={bestPerformers}
        worstPerformers={worstPerformers}
      />

      <ParameterCorrelation />

      <WorkareaPlot
        bestPerformers={bestPerformers}
        worstPerformers={worstPerformers}
      />

      <AccuracyTimeline />
    </div>
  );
}
