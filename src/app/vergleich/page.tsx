import React from 'react';

import { getBahnInfo } from '@/src/actions/motion.service';
import SimilaritySearchWrapper from '@/src/app/vergleich/components/SimilaritySearchWrapper';

const { bahnInfo } = await getBahnInfo({ page: 1, pageSize: 15 });

export default function VergleichPage() {
  return <SimilaritySearchWrapper bahnInfo={bahnInfo} />;
}
