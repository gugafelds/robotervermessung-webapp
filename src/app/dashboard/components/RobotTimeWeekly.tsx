'use client';

import dynamic from 'next/dynamic';

import { Typography } from '@/src/components/Typography';
import { displayName } from '@/src/lib/labels';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const COLORS = ['#003560', '#10b981', '#f59e0b', '#ef4444'];

interface Props {
  weekly: { week: string; robot: string; hours: number }[];
}

// measured robot time per calendar week, stacked by robot
export function RobotTimeWeekly({ weekly }: Props) {
  const robots = [...new Set(weekly.map((w) => w.robot))].sort();

  return (
    <div className="flex flex-col justify-center rounded-2xl border border-gray-500 bg-white p-6">
      <Typography as="h2" className="mb-2">
        Robot time per week
      </Typography>

      <div className="mb-4 text-sm text-gray-600">
        <p>
          Measured motion time per calendar week (start to end of each recorded
          trajectory), i.e. the progress of the data collection.
        </p>
      </div>

      {weekly.length === 0 ? (
        <div className="flex h-96 items-center justify-center text-gray-500">
          No data available
        </div>
      ) : (
        <Plot
          data={robots.map((robot, i) => {
            const rows = weekly.filter((w) => w.robot === robot);
            return {
              x: rows.map((w) => w.week),
              y: rows.map((w) => w.hours),
              type: 'bar',
              name: displayName(robot),
              marker: { color: COLORS[i % COLORS.length] },
              hovertemplate: `<b>${displayName(robot)}</b><br>Week of %{x|%d.%m.%Y}<br>%{y:.1f} h<extra></extra>`,
            };
          })}
          layout={{
            autosize: true,
            height: 400,
            barmode: 'stack',
            margin: { t: 20, r: 20, l: 80, b: 80 },
            xaxis: {
              title: { text: 'Calendar week' },
              type: 'date',
              tickformat: '%d.%m.%Y',
            },
            yaxis: { title: { text: 'Robot time [h]' }, rangemode: 'tozero' },
            showlegend: true,
            legend: { x: 0.02, y: 0.98, bgcolor: 'rgba(255,255,255,0.8)' },
          }}
          style={{ width: '100%' }}
          config={{
            responsive: true,
            displaylogo: false,
            modeBarButtonsToRemove: [
              'toImage',
              'lasso2d',
              'zoomIn2d',
              'zoomOut2d',
              'autoScale2d',
              'pan2d',
            ],
          }}
        />
      )}
    </div>
  );
}
