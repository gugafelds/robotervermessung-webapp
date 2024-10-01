import type { ObjectId } from 'mongodb';

import type { TrajectoryData } from '@/types/main';

interface CSVRow {
  [key: string]:
    | ObjectId
    | number[]
    | string
    | number
    | boolean
    | null
    | undefined;
}

export const getCSVData = (data: TrajectoryData): CSVRow[] => {
  const rows: CSVRow[] = [];

  Object.keys(data).forEach((key: string) => {
    if (!key.includes('_')) {
      if (Array.isArray(data[key as keyof TrajectoryData])) {
        const arr = data[key as keyof TrajectoryData] as never[];

        arr.forEach((item, index) => {
          if (!rows[index]) rows[index] = {};
          rows[index][key] = item;
        });
      }
    }
  });

  return rows;
};
