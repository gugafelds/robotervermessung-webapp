import { usePathname } from 'next/navigation';
import { CSVLink } from 'react-csv';

import SlideOver from '@/src/components/SlideOver';
import { Typography } from '@/src/components/Typography';
import { useApp } from '@/src/providers/app.provider';


type AddListSlideOverProps = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

export const SettingsSlideOver = ({ setOpen, open }: AddListSlideOverProps) => {
  const { trajectories } = useApp();
  const { currentTrajectory } = useApp();
  const pathname = usePathname();
  const searchedIndex = pathname.substring(1, pathname.length);

  const currentTrajectoryIndex = trajectories.findIndex(
    (item) => item.dataId === searchedIndex,
  );
  
  const currentTrajectoryData = trajectories[currentTrajectoryIndex];

  console.log(currentTrajectory)

  // final das contas eu consegui é fazer quase porra nenhuma do .csv
  // minha ideia era que eu pudesse ler o Index da atual trajetória e poder gerar automaticamente os headers do .csv
  // com isso, eu iria imprimir todos os valores que eu tenho dos arquivos .json em .csv de posição e orientação do robô


  const data = [['robot_name', trajectories[searchedIndex]]];

  return (
    <SlideOver title="options" open={open} onClose={() => setOpen(false)}>
      <div className="cursor-pointer p-5 betterhover:hover:bg-gray-200">
        <CSVLink data={data}>save to .csv</CSVLink>
      </div>
    </SlideOver>
  );
};
