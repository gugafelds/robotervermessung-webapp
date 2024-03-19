'use client';

import { usePathname } from 'next/navigation';
import { CSVLink } from 'react-csv';
import SlideOver from '@/src/components/SlideOver';
import { Typography } from '@/src/components/Typography';
import { useApp } from '@/src/providers/app.provider';
import { json } from '@/src/lib/functions';

type AddListSlideOverProps = {
  open: boolean;
  setOpen: (open: boolean) => void;

};

export const SettingsSlideOver = ({ setOpen, open}: AddListSlideOverProps) => { 
  const { trajectoriesHeader, trajectoriesData } = useApp();
  const pathname = usePathname();
  const searchedIndex = pathname.substring(1, pathname.length);

  const currentTrajectoryIndex = trajectoriesHeader.findIndex(
    (item) => item.dataId === searchedIndex,
  );
  
  const currentTrajectoryHeader = trajectoriesHeader[currentTrajectoryIndex];
  const currentTrajectoryData = trajectoriesData[currentTrajectoryIndex];

  const headerKeys = Object.keys(currentTrajectoryHeader).filter(
    (key) => !key.includes('_'),
  );

  const dataKeys = Object.keys(currentTrajectoryData).filter(
    (key) => !key.includes('_'),
  );

  const createHeaderArray = (keys: any[]) => {
    return keys.map(key => ({ label: String(key), key }));
  };

  const combinedHeaders = [...createHeaderArray(headerKeys), ...createHeaderArray(dataKeys)];

  const csvData = [combinedHeaders];


  return (
    <SlideOver title="options" open={open} onClose={() => setOpen(false)}>
      <div className="cursor-pointer p-5 betterhover:hover:bg-gray-200">
        <CSVLink data={json(csvData)}>save to .csv</CSVLink>
      </div>
    </SlideOver>
  );
};
