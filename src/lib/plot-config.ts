import type { Layout, PlotData } from 'plotly.js';

export const dataPlotConfig = (name: string) =>
  ({
    name,
    mode: 'lines',
    type: 'scatter3d',
    line: {
      width: 6,
    },
  }) as Partial<PlotData>;

export const plotLayoutConfig: Partial<Layout> = {
  legend: {
    x: 0,
    y: 1,
    traceorder: 'normal',
    font: {
      family: 'sans-serif',
      size: 12,
      color: '#000',
    },
    bgcolor: '#E2E2E2',
    bordercolor: '#FFFFFF',
    borderwidth: 2,
  },
  width: 800,
  height: 600,
  scene: {
    xaxis: { title: 'X Axis' },
    yaxis: { title: 'Y Axis' },
    zaxis: { title: 'Z Axis' },
  },
};
