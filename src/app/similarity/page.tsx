import React from 'react';

import { getTrajInfo } from '@/src/actions/motion.service';
import SimilaritySearchWrapper from '@/src/app/similarity/components/SimilaritySearchWrapper';

const { trajInfo } = await getTrajInfo({ page: 1, pageSize: 15 });

export default function SimilarityPage() {
  return <SimilaritySearchWrapper trajInfo={trajInfo} />;
}
