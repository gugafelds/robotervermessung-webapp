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
  title: {
    text: '3D position plot',
    yref: 'paper',
    font: {
      size: 30,
      family: 'Arial, sans-serif',
      color: '#003560',
    },
    pad: {
      r: 90,
    },
  },
  modebar: {
    orientation: 'v',
    color: '#E2E2E2',
  },
  hovermode: 'closest',
  margin: {
    l: 1,
    b: 1,
    r: 5,
  },
  legend: {
    x: 1,
    y: 0,
    traceorder: 'grouped',
    font: {
      family: 'Tahoma, sans-serif',
      size: 15,
    },
    bgcolor: '#E2E2E2',
    bordercolor: '#FFFFFF',
    borderwidth: 2,
  },
  width: 600,
  height: 600,
  scene: {
    xaxis: { title: 'x [m]' },
    yaxis: { title: 'y [m]' },
    zaxis: { title: 'z [m]' },
  },
};
