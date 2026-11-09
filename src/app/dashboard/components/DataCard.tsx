import { Typography } from '@/src/components/Typography';

interface DataCardProps {
  componentName: string;
  value?: number;
  unit?: string;
  decimals?: number;
  note?: string; // small line under the value
}

export function DataCard({
  componentName,
  value = 0,
  unit,
  decimals = 0,
  note,
}: DataCardProps) {
  return (
    <div className="rounded-lg border border-gray-500 bg-white p-4">
      <Typography as="h5">{componentName}</Typography>
      <Typography as="h4" className="mt-2 text-primary">
        {value.toLocaleString('de-DE', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })}
        {unit && ` ${unit}`}
      </Typography>
      {note && <p className="mt-1 text-sm text-gray-600">{note}</p>}
    </div>
  );
}
