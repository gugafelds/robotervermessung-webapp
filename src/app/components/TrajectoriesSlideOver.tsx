import Link from 'next/link';

import SlideOver from '@/src/components/SlideOver';
import { Typography } from '@/src/components/Typography';
import { formatDate } from '@/src/lib/functions';
import { useApp } from '@/src/providers/app.provider';

type AddListSlideOverProps = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

export const TrajectoriesSlideOver = ({
  setOpen,
  open,
}: AddListSlideOverProps) => {
  const { trajectories } = useApp();

  return (
    <SlideOver
      title="Wählen Sie Flugbahn"
      open={open}
      onClose={() => setOpen(false)}
    >
      {trajectories.map((trajectory) => (
        <Link
          key={trajectory._id.toString()}
          href={`/${trajectory._id.toString()}`}
          onClick={() => setOpen(false)}
        >
          <div className="p-5 betterhover:hover:bg-gray-200">
            <Typography as="h2" className="font-semibold">
              {trajectory.robotName}
            </Typography>
            <Typography as="h4">
              {formatDate(trajectory.recordingDate)}
            </Typography>
          </div>
        </Link>
      ))}
    </SlideOver>
  );
};
