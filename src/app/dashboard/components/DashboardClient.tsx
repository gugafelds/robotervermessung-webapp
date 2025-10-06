/* eslint-disable react/button-has-type */

'use client';

import { AccuracyTimeline } from '@/src/app/dashboard/components/AccuracyTimeline';
import { DataCard } from '@/src/app/dashboard/components/DataCard';
import { DistributionCharts } from '@/src/app/dashboard/components/DistributionCharts';
import { ParameterCorrelation } from '@/src/app/dashboard/components/ParameterCorrelation';
import { WorkareaPlot } from '@/src/app/dashboard/components/WorkareaPlot';
import { Typography } from '@/src/components/Typography';

// Nur noch die Counts!
interface DashboardClientProps {
  filenamesCount: number;
  bahnenCount: number;
}

export default function DashboardClient({
  filenamesCount,
  bahnenCount,
}: DashboardClientProps) {
  return (
    <div className="justify-center p-6">
      <Typography as="h2" className="py-2">
        Bewegungsdaten
      </Typography>

      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        <DataCard componentName="Roboterbahnen insgesamt" value={bahnenCount} />
        <DataCard
          componentName="Aufnahmendateien insgesamt"
          value={filenamesCount}
        />
      </div>

      <Typography as="h2" className="py-2">
        Datenverteilung
      </Typography>

      {/* Charts laden jetzt SELBSTSTÄNDIG! */}
      <DistributionCharts />

      {/* Genauigkeit über Zeit */}
      <Typography as="h2" className="mt-8 py-2">
        Genauigkeitsentwicklung
      </Typography>
      <AccuracyTimeline />

      {/* NEU: Parameter-Korrelation */}
      <Typography as="h2" className="mt-8 py-2">
        Einflussfaktoren auf Genauigkeit
      </Typography>
      <ParameterCorrelation />

      {/* Arbeitsraum lädt auch SELBSTSTÄNDIG! */}
      <Typography as="h2" className="mt-8 py-2">
        Arbeitsraum
      </Typography>
      <WorkareaPlot />
    </div>
  );
}
