import axios from 'axios';

import type { TrajectoryData } from '@/types/main';

// const CLOUD_FUNCTIONS_URI =
//   'https://europe-west3-dotted-forest-420514.cloudfunctions.net/euclidean_distance';

const CLOUD_FUNCTIONS_URI = 'http://localhost:8080';

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

  return response.data;
};
