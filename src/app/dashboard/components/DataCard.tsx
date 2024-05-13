import { Typography } from '@/src/components/Typography';

type Props = {
  value: number;
  title: string;
};

export const DataCard = ({ value, title }: Props) => {
  return (
    <div className="rounded-lg bg-primary p-5">
      <Typography as="h1" className="text-white">
        {value}
      </Typography>
      <Typography as="h2" className="text-white">
        {title}
      </Typography>
    </div>
  );
};
