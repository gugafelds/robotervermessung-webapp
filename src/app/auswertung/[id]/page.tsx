import { AuswertungDetails } from '@/src/app/auswertung/components/AuswertungDetails';

export default function AuswertungDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <AuswertungDetails bahnId={params.id} />;
}
