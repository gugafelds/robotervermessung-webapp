import { redirect } from 'next/navigation';

import { getEvaluationTrajIDs } from '@/src/actions/evaluation.service';

export default async function EvaluationPage() {
  const result = await getEvaluationTrajIDs({
    page: 1,
    pageSize: 20,
  });

  if (result.evaluationTrajIDs.traj_info.length > 0) {
    redirect(`/evaluation/${result.evaluationTrajIDs.traj_info[0].trajID}`);
  }

  return <div>No evaluation data available</div>;
}
