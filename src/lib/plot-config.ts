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
      family: 'Arial, sans-serif',
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
      family: 'Tahoma, sans-serif',
      size: 15,
    },
    bgcolor: '#E2E2E2',
    bordercolor: '#FFFFFF',
    borderwidth: 2,
  },
  width: 500,
  height: 500,
  scene: {
    xaxis: { title: 'x [m]' },
    yaxis: { title: 'y [m]' },
    zaxis: { title: 'z [m]' },
  },
};

export const plotLayout2DConfigVelocity: Partial<Layout> = {
  title: {
    text: 'TCP-Geschwindigkeit',
    font: {
      size: 15,
      family: 'Arial, sans-serif',
      color: 'black',
    },
  },
  modebar: {
    orientation: 'v',
    color: '#E2E2E2',
  },
  margin: {
    l: 30,
    r: 30,
    b: 20,
    t: 50,
    pad: 1,
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
  width: 400,
  height: 200,
  xaxis: {
    title: 't [s]',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 1,
  },
  yaxis: {
    title: 'v [mm/s]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigAcceleration: Partial<Layout> = {
  title: {
    text: 'TCP-Beschleunigung',
    font: {
      size: 15,
      family: 'Arial, sans-serif',
      color: 'black',
    },
  },
  modebar: {
    orientation: 'v',
    color: '#E2E2E2',
  },
  margin: {
    l: 30,
    r: 30,
    b: 20,
    t: 50,
    pad: 1,
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
  width: 400,
  height: 200,
  xaxis: {
    title: 't [s]',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 1,
  },
  yaxis: {
    title: 'a [mm²/s]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const heatMapLayoutConfig: Partial<Layout> = {
  title: {
    text: 'DTW-Kostenmatrix',
    yref: 'paper',
    font: {
      size: 15,
      family: 'Arial, sans-serif',
      color: 'black',
    },
  },
  modebar: {
    orientation: 'v',
    color: '#E2E2E2',
  },
  hovermode: 'closest',
  margin: {
    l: 30,
    r: 30,
    b: 30,
    t: 50,
    pad: 1,
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
  width: 350,
  height: 350,
  xaxis: { title: 'Pfad X [Soll-Punkte]', automargin: true },
  yaxis: { title: 'Pfad Y [Ist-Punkte]', automargin: true },
};
