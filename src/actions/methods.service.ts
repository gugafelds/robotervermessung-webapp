import axios from 'axios';

import type { TrajectoryData } from '@/types/main';

const CLOUD_FUNCTIONS_URI =
  'https://europe-west3-dotted-forest-420514.cloudfunctions.net/euclidean_distance';

export const applyEuclideanDistance = async ({
  xIst: x_ist,
  yIst: y_ist,
  zIst: z_ist,
  xSoll: x_soll,
  ySoll: y_soll,
  zSoll: z_soll,
}: TrajectoryData) => {
  const response = await axios.post(CLOUD_FUNCTIONS_URI, {
    x_ist,
    y_ist,
    z_ist,
    x_soll,
    y_soll,
    z_soll,
  });

  alert(JSON.stringify(response.data));
  return response.data;
};
