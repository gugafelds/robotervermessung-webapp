import dynamic from 'next/dynamic';

import { heatMapLayoutConfig } from '@/src/lib/plot-config';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export const Heatmap = () => {
  const data = [
    {
      z: [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
      ],
      type: 'heatmap',
    },
  ];

  return (
    <div>
      <Plot data={data} layout={heatMapLayoutConfig} />
    </div>
  );
};

export default Heatmap;
