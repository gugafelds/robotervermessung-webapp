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

export const plotLayout2DConfigQuaternion: Partial<Layout> = {
  // Add any specific configuration you want for the quaternion plot
  // For example:
  autosize: true,
  height: 400,
  width: 600,
  margin: { l: 50, r: 50, b: 50, t: 50, pad: 4 },
  font: {
    size: 12,
    family: 'Arial, sans-serif',
    color: 'black',
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
    dtick: 5.0,
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
    dtick: 5.0,
  },
  yaxis: {
    title: 'a [mm²/s]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigEuclideanError: Partial<Layout> = {
  title: {
    text: 'Abw. [Euclidean]',
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
  showlegend: false,
  width: 400,
  height: 200,
  xaxis: {
    title: 'Punkte',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 100,
  },
  yaxis: {
    title: 'e [mm]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigDTWError: Partial<Layout> = {
  title: {
    text: 'Abw. [DTW Standard]',
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
  showlegend: false,
  width: 400,
  height: 200,
  xaxis: {
    title: 'Punkte',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 100,
  },
  yaxis: {
    title: 'e [mm]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigDTWJohnenError: Partial<Layout> = {
  title: {
    text: 'Abw. [DTW Johnen]',
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
  showlegend: false,
  width: 400,
  height: 200,
  xaxis: {
    title: 'Punkte',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 100,
  },
  yaxis: {
    title: 'e [mm]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigDFDError: Partial<Layout> = {
  title: {
    text: 'Abw. [DFD]',
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
  showlegend: false,
  width: 400,
  height: 200,
  xaxis: {
    title: 'Punkte',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 100,
  },
  yaxis: {
    title: 'e [mm]',
    automargin: true,
    showgrid: true,
    autorange: true,
    ticksuffix: '  ',
  },
};

export const plotLayout2DConfigLCSSError: Partial<Layout> = {
  title: {
    text: 'Abw. [LCSS]',
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
  showlegend: false,
  width: 400,
  height: 200,
  xaxis: {
    title: 'Punkte',
    automargin: true,
    autorange: true,
    showgrid: true,
    dtick: 100,
  },
  yaxis: {
    title: 'e [mm]',
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
