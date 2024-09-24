import React from 'react';

import { TrajectorySegmentAnalyzer } from '@/src/app/segments/components/TrajectorySegmentAnalyzer';
import { Typography } from '@/src/components/Typography';

export default function SegmentAnalyzerPage() {
  return (
    <div>
      <Typography as="h1" className="mb-4 text-3xl font-bold">
        Bahnsegment-Analysator
      </Typography>
      <Typography as="p" className="mb-6">
        Du kannst eine Aufzeichnungsdatei auswählen und dann bestimmte Segmente markieren, die du dir im Detail anschauen möchtest.
      </Typography>
      <TrajectorySegmentAnalyzer />
    </div>
  );
}
