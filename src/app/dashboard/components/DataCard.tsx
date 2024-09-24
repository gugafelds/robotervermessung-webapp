import { Typography } from '@/src/components/Typography';

type Props = {
  value: number;
  componentName?: string; // New optional prop
};

export const DataCard = ({ value, componentName }: Props) => {
  return (
    <div className="rounded-lg bg-primary p-5">
      <Typography as="h1" className="text-white">
        {value}
      </Typography>
      <Typography as="h2" className="text-white">
        {componentName}
      </Typography>
    </div>
  );
};
