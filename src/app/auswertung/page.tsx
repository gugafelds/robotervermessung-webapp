import { redirect } from 'next/navigation';

import { getAuswertungBahnIDs } from '@/src/actions/auswertung.service';

export default async function AuswertungPage() {
  // Lade die erste Seite mit Standardpaginierung
  const result = await getAuswertungBahnIDs({
    page: 1,
    pageSize: 20,
  });

  if (result.auswertungBahnIDs.bahn_info.length > 0) {
    redirect(`/auswertung/${result.auswertungBahnIDs.bahn_info[0].bahnID}`);
  }

  return <div>Keine Auswertungsdaten verfügbar</div>;
}
