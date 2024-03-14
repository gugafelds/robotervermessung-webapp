import SlideOver from '@/src/components/SlideOver';
import { Typography } from '@/src/components/Typography';

type AddListSlideOverProps = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

export const SettingsSlideOver = ({ setOpen, open }: AddListSlideOverProps) => {
  return (
    <SlideOver title="options" open={open} onClose={() => setOpen(false)}>
      <div className="cursor-pointer p-5 betterhover:hover:bg-gray-200">
        <Typography as="h2" className="font-semibold">
          save to .csv
        </Typography>
      </div>
    </SlideOver>
  );
};
