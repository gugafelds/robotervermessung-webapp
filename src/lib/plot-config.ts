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
    l: 1,
    r: 1,
    b: 1,
    t: 1,
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

export const plotLayout2DConfig: Partial<Layout> = {
  title: { text: "TCP-Geschwindigkeit",
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
  margin: {
    l: 1,
    r: 1,
    b: 1,
    t: 1,
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
  xaxis: { title: 't [s]', automargin: true, showgrid: true},
  yaxis: { title: 'v [mm/s]', automargin: true, showgrid: true},
};

export const heatMapLayoutConfig: Partial<Layout> = {
  title: { text: "Kostenmatrix",
    yref: 'paper',
    font: {
      size: 20,
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
    l: 1,
    r: 1,
    b: 1,
    t: 1,
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
  xaxis: { title: 'Pfad X [Soll-Punkte]', automargin: true},
  yaxis: { title: 'Pfad Y [Ist-Punkte]', automargin: true},
};
