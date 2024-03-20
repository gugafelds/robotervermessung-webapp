import type { ObjectId } from 'mongodb';
import { usePathname } from 'next/navigation';
import { CSVLink } from 'react-csv';

import SlideOver from '@/src/components/SlideOver';
import { useApp } from '@/src/providers/app.provider';
import type { TrajectoryData } from '@/types/main';

interface SettingsSlideOverProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

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

export const SettingsSlideOver = ({
  setOpen,
  open,
}: SettingsSlideOverProps) => {
  const { trajectoriesData } = useApp();
  const searchedIndex = usePathname().substring(1);

  const filterTrajectoriesData = (): TrajectoryData[] => {
    if (searchedIndex !== '') {
      return trajectoriesData.filter(
        (item: TrajectoryData) => item.trajectoryHeaderId === searchedIndex,
      );
    }
    return [];
  };

  const getCSVData = (data: TrajectoryData[]): CSVRow[] => {
    let maxLength = 0;

    // Encontrar o comprimento máximo de array em todos os cabeçalhos
    data.forEach((item: TrajectoryData) => {
      Object.keys(item).forEach((key: string) => {
        if (Array.isArray(item[key as keyof TrajectoryData])) {
          maxLength = Math.max(
            maxLength,
            (item[key as keyof TrajectoryData] as any[]).length,
          );
        }
      });
    });

    return data.reduce((acc: CSVRow[], curr: TrajectoryData) => {
      const rows: CSVRow[] = [];

      // Criar uma linha para cada elemento do array de maior comprimento
      for (let i = 0; i < maxLength; i += 1) {
        const row: CSVRow = {};

        Object.keys(curr).forEach((key: string) => {
          if (!key.includes('_')) {
            // Ignorar variáveis com sublinhados no nome
            if (Array.isArray(curr[key as keyof TrajectoryData])) {
              row[key] = (curr[key as keyof TrajectoryData] as any[])[i] ?? ''; // Usar o elemento correspondente do array
            } else {
              row[key] = curr[key as keyof TrajectoryData];
            }
          }
        });

        rows.push(row);
      }

      acc.push(...rows);
      return acc;
    }, []);
  };

  const trajectoryData: TrajectoryData[] = filterTrajectoriesData();
  const csvData: CSVRow[] = getCSVData(trajectoryData);

  const headers = Object.keys(csvData[0] || {}).map((key: string) => ({
    label: key,
    key,
  }));

  const csvTrajectory = {
    data: csvData,
    headers,
    filename: 'trajectory.csv',
  };

  return (
    <SlideOver title="options" open={open} onClose={() => setOpen(false)}>
      <div className="cursor-pointer p-5 betterhover:hover:bg-gray-300">
        <CSVLink {...csvTrajectory} separator=";">
          Save to .csv
        </CSVLink>
      </div>
    </SlideOver>
  );
};
