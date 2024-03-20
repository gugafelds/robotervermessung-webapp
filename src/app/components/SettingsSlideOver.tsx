import { usePathname } from 'next/navigation';
import { CSVLink } from 'react-csv';

import SlideOver from '@/src/components/SlideOver';
import { useApp } from '@/src/providers/app.provider';
import type { TrajectoryData } from '@/types/main';

type AddListSlideOverProps = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

type Row = {
  [key: string]: any;
};

export const SettingsSlideOver = ({ setOpen, open }: AddListSlideOverProps) => {
  const { trajectoriesData } = useApp();
  const searchedIndex = usePathname().substring(1);

  const trajectoryData: TrajectoryData[] = [];

  if (searchedIndex !== '') {
    const currentTrajectoryIndex = trajectoriesData.findIndex(
      (item) => item.trajectoryHeaderId === searchedIndex,
    );

    if (currentTrajectoryIndex !== -1) {
      trajectoryData.push(trajectoriesData[currentTrajectoryIndex]);
    }
  }

  // Encontrando o maior comprimento de array
  const maxArrayLength = Math.max(
    ...trajectoryData.flatMap((curr) =>
      Object.values(curr)
        .filter((val) => Array.isArray(val))
        .map((arr) => arr.length),
    ),
  );

  // Criando um conjunto para armazenar IDs únicos
  const uniqueIds = new Set();
  const uniqueHeaderIds = new Set();

  // Remodelando os dados para cada linha no CSV
  const csvData = trajectoryData.reduce((acc, curr) => {
    // Adicionando ID único ao conjunto
    uniqueIds.add(curr._id);
    uniqueHeaderIds.add(curr.trajectoryHeaderId);

    // Iterando sobre o comprimento máximo do array
    for (let i = 0; i < maxArrayLength; i += 1) {
      const row: Row = []; // Tipagem explícita para row

      // Adicionando cada valor correspondente ao objeto da linha
      Object.keys(curr).forEach((key) => {
        if (Array.isArray(curr[key as keyof TrajectoryData])) {
          // Usando o índice i para pegar o valor correspondente do array, ou vazio se não houver elemento
          row[key] = (curr[key as keyof TrajectoryData] as number[])[i] ?? '';
        } else if (!key.includes('_')) {
          // Adicionando o ID, trajectoryHeaderId ou keys sem underscore apenas uma vez
          row[key] = i === 0 ? curr[key as keyof TrajectoryData] : '';
        }
      });

      acc.push(); // Adicionando a linha remodelada ao acumulador
    }

    return acc;
  }, []);

  const headers = Object.keys(trajectoryData[0])
    .filter((key) => !key.includes('_'))
    .map((key) => ({
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
          save to .csv
        </CSVLink>
      </div>
    </SlideOver>
  );
};
