import { Typography } from '@/src/components/Typography';

type Props = {
  value: number;
  componentName?: string;
  size?: number;
};

const formatNumber = (num: number) => {
  return new Intl.NumberFormat('de-DE').format(num);
};

const formatSize = (size: number) => {
  return `(${size.toFixed(2)} MB)`;
};

export const DataCard = ({ value, componentName, size }: Props) => {
  return (
    <div className="rounded-lg bg-primary p-5">
      <Typography as="h2" className="text-white">
        {formatNumber(value)}{' '}
        {size && <span className="text-sm">{formatSize(size)}</span>}
      </Typography>
      <Typography as="h5" className="font-light text-white">
        {componentName}
      </Typography>
    </div>
  );
};
