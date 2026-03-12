import { redirect } from 'next/navigation';

import {getBahnInfo, getTrajInfo} from '@/src/actions/motion.service';

export default async function MotionPage() {
  // Lade nur die erste Seite mit Standard-Seitengröße
  const { trajInfo } = await getTrajInfo({ page: 1, pageSize: 20 });

  // Wenn Daten vorhanden sind, leite zum ersten Eintrag weiter
  if (trajInfo.length > 0) {
    redirect(`/motion/${trajInfo[0].trajID}`);
  }

  return <div>No trajectory data available</div>;
}
