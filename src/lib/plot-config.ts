import type { Layout, PlotData } from 'plotly.js';

export const dataPlotConfig = (
  mode: string,
  name: string,
  width: number,
  color = '',
  showlegend = true,
) =>
  ({
    name,
    mode,
    type: 'scatter3d',
    showlegend,
    line: {
      color,
      width,
    },
    marker: {
      opacity: 0.6,
      size: 4,
    },
  }) as Partial<PlotData>;

export const plotLayoutConfig: Partial<Layout> = {
  title: {
    yref: 'paper',
    font: {
      size: 30,
      family: 'Helvetica',
      color: '#003560',
    },
  },
  modebar: {
    orientation: 'v',
    color: '#E2E2E2',
  },
  hovermode: 'closest',
  margin: {
    l: 5,
    r: 5,
    b: 5,
    t: 5,
    pad: 1,
  },
  legend: {
    x: 1,
    y: 0,
    traceorder: 'grouped',
    font: {
      family: 'Arial, sans-serif',
      size: 15,
    },
    bgcolor: '#E2E2E2',
    bordercolor: '#FFFFFF',
    borderwidth: 2,
  },
  width: 500,
  height: 500,
  scene: {
    xaxis: { title: 'x [mm]' },
    yaxis: { title: 'y [mm]' },
    zaxis: { title: 'z [mm]' },
  },
};
