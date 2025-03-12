import { redirect } from 'next/navigation';

import { getBahnInfo } from '@/src/actions/bewegungsdaten.service';

export default async function BewegungsdatenPage() {
  // Lade nur die erste Seite mit Standard-Seitengröße
  const { bahnInfo } = await getBahnInfo({ page: 1, pageSize: 20 });

  // Wenn Daten vorhanden sind, leite zum ersten Eintrag weiter
  if (bahnInfo.length > 0) {
    redirect(`/bewegungsdaten/${bahnInfo[0].bahnID}`);
  }

  return <div>Keine Bahndaten verfügbar</div>;
}
