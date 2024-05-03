import axios from 'axios';

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
  const response = await axios.post(CLOUD_FUNCTIONS_URI, {
    trajectory_header_id,
    x_ist,
    y_ist,
    z_ist,
    x_soll,
    y_soll,
    z_soll,
  });

  return response.data;
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
  q1Ist: q1_ist,
  q2Ist: q2_ist,
  q3Ist: q3_ist,
  q4Ist: q4_ist,
  q1Soll: q1_soll,
  q2Soll: q2_soll,
  q3Soll: q3_soll,
  q4Soll: q4_soll,
}: TrajectoryData) => {
  const responseDTW = await axios.post(CLOUD_FUNCTIONS_URI_DTW, {
    trajectory_header_id,
    timestamp_ist,
    x_ist,
    y_ist,
    z_ist,
    q1_ist,
    q2_ist,
    q3_ist,
    q4_ist,
    timestamp_soll,
    x_soll,
    y_soll,
    z_soll,
    q1_soll,
    q2_soll,
    q3_soll,
    q4_soll,
  });

  return responseDTW.data;
};
