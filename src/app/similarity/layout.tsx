import React from 'react';

import { getTrajInfo } from '@/src/actions/motion.service';
import { MetadataUpload } from '@/src/app/similarity/components/MetaDataUpload';
import { TrajectoryProvider } from '@/src/providers/trajectory.provider';

interface SimilarityLayoutProps {
  children: React.ReactNode;
}

export default async function SimilarityLayout({
  children,
}: SimilarityLayoutProps) {
  // Lade Trajdaten für den TrajectoryProvider
  const { bahnInfo: initialTrajInfo, pagination: initialPagination } =
    await getTrajInfo({
      page: 1,
      pageSize: 15, // Mehr Bahnen für besseren Similarity
    });

  return (
    <TrajectoryProvider
      initialTrajInfo={initialTrajInfo}
      initialPagination={initialPagination}
    >
      <main className="flex flex-col lg:flex-row">
        <div className="h-fullscreen w-fit space-y-2 overflow-y-auto bg-gray-100 p-4">
          <div className="space-y-2">
            <MetadataUpload />
          </div>
        </div>

        <div className="h-fullscreen flex-1 overflow-y-auto">{children}</div>
      </main>
    </TrajectoryProvider>
  );
}
