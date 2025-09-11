// src/app/bahn-vergleich/page.tsx
import React from 'react';

import { MetadataUpload } from '@/src/app/vergleich/components/MetaDataUpload';
import { MetaValuesCalculator } from '@/src/app/vergleich/components/MetaValueCalculator';

export default function BahnVergleichPage() {
  return (
    <div className="min-h-screen">
      <div className="container mx-auto py-8">
        <MetaValuesCalculator />
        <MetadataUpload />
      </div>
    </div>
  );
}
