// src/app/bahn-vergleich/page.tsx
import React from 'react';

import BahnComparison from '@/src/app/vergleich/components/MetaDataUpload';

export default function BahnVergleichPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <BahnComparison />
      </div>
    </div>
  );
}
