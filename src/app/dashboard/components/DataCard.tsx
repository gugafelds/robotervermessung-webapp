import { Typography } from '@/src/components/Typography';

interface DataCardProps {
  componentName: string;
  value?: number;
}

export function DataCard({ componentName, value = 0 }: DataCardProps) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-md">
      <Typography as="h5">{componentName}</Typography>
      <Typography as="h3" className="mt-2 text-primary">
        {value.toLocaleString('de-DE')}
      </Typography>
    </div>
  );
}
