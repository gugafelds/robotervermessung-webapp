import { redirect } from 'next/navigation';

import { getAllAuswertungInfo } from '@/src/actions/auswertung.service';

export default async function AuswertungPage() {
  const auswertungInfo = await getAllAuswertungInfo();

  if (auswertungInfo.bahn_info && auswertungInfo.bahn_info.length > 0) {
    redirect(`/auswertung/${auswertungInfo.bahn_info[0].bahnID}`);
  }

  return <div>Keine Auswertungsdaten verfügbar</div>;
}
