import { redirect } from 'next/navigation';

import { getAllBahnInfo } from '@/src/actions/bewegungsdaten.service';

export default async function BewegungsdatenPage() {
  const bahnInfo = await getAllBahnInfo();

  if (bahnInfo.length > 0) {
    redirect(`/bewegungsdaten/${bahnInfo[0].bahnID}`);
  }

  return <div>Keine Bahndaten verfügbar</div>;
}
