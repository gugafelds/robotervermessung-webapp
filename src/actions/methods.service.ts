import axios from 'axios';

import {
  transformDTWJohnenMetricResult,
  transformEuclideanMetricResult,
} from '@/src/lib/transformer';
import type { TrajectoryData } from '@/types/main';

const CLOUD_FUNCTIONS_URI =
  'https://europe-west3-dotted-forest-420514.cloudfunctions.net/euclidean_distance';

const CLOUD_FUNCTIONS_URI_DTW =
  'https://europe-west3-dotted-forest-420514.cloudfunctions.net/dtw_johnen';

export const applyEuclideanDistance = async ({
  trajectoryHeaderId: trajectory_header_id,
  xIst: x_ist,
  yIst: y_ist,
  zIst: z_ist,
  xSoll: x_soll,
  ySoll: y_soll,
  zSoll: z_soll,
}: TrajectoryData) => {
  const response = await axios.post(
    CLOUD_FUNCTIONS_URI,
    {
      trajectory_header_id,
      x_ist,
      y_ist,
      z_ist,
      x_soll,
      y_soll,
      z_soll,
    },
    { responseType: 'json' },
  );

  return transformEuclideanMetricResult(JSON.parse(response.data));
};

export const applyDTWJohnen = async ({
  trajectoryHeaderId: trajectory_header_id,
  xIst: x_ist,
  yIst: y_ist,
  zIst: z_ist,
  xSoll: x_soll,
  ySoll: y_soll,
  zSoll: z_soll,
  timestampIst: timestamp_ist,
  timestampSoll: timestamp_soll,
}: TrajectoryData) => {
  const responseDTW = await axios.post(CLOUD_FUNCTIONS_URI_DTW, {
    trajectory_header_id,
    timestamp_ist,
    x_ist,
    y_ist,
    z_ist,
    timestamp_soll,
    x_soll,
    y_soll,
    z_soll,
  });

  return transformDTWJohnenMetricResult(JSON.parse(responseDTW.data));
};
