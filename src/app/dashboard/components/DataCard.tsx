import { Typography } from '@/src/components/Typography';

type Props = {
  value: number;
  componentName?: string;
  size?: number;
};

const formatNumber = (num: number) => {
  // Prüfe ob der Wert eine gültige Zahl ist
  if (num === undefined || num === null || Number.isNaN(num)) {
    return '0';
  }
  try {
    return new Intl.NumberFormat('de-DE').format(Number(num));
  } catch {
    return '0';
  }
};

const formatSize = (size: number) => {
  // Prüfe ob der Größenwert eine gültige Zahl ist
  if (size === undefined || size === null || Number.isNaN(size)) {
    return '(0.00 MB)';
  }
  try {
    const safeSize = Number(size);
    return `(${safeSize.toFixed(2)} MB)`;
  } catch {
    return '(0.00 MB)';
  }
};

export const DataCard = ({ value = 0, componentName = '', size }: Props) => {
  return (
    <div className="rounded-lg bg-primary p-5">
      <Typography as="h2" className="text-white">
        {formatNumber(value)}{' '}
        {size !== undefined && (
          <span className="text-sm">{formatSize(size)}</span>
        )}
      </Typography>
      <Typography as="h5" className="font-light text-white">
        {componentName}
      </Typography>
    </div>
  );
};
