import React from 'react';

import {
  getBahnAccelIstById,
  getBahnEventsById,
  getBahnInfoById,
  getBahnJointStatesById,
  getBahnOrientationSollById,
  getBahnPoseIstById,
  getBahnPositionSollById,
  getBahnTwistIstById,
  getBahnTwistSollById,
} from '@/src/actions/trajectory.service';
import { TrajectoryWrapper } from '@/src/app/trajectories/components/TrajectoryWrapper';
import { json } from '@/src/lib/functions';

type TrajectoryPageProps = {
  params: { id: string };
};

export default async function TrajectoryPage({ params }: TrajectoryPageProps) {
  const currentBahnInfo = await getBahnInfoById(params.id);
  const currentBahnPoseIst = await getBahnPoseIstById(params.id);
  const currentBahnTwistIst = await getBahnTwistIstById(params.id);
  const currentBahnAccelIst = await getBahnAccelIstById(params.id);
  const currentBahnPositionSoll = await getBahnPositionSollById(params.id);
  const currentBahnOrientationSoll = await getBahnOrientationSollById(
    params.id,
  );
  const currentBahnTwistSoll = await getBahnTwistSollById(params.id);
  const currentBahnJointStates = await getBahnJointStatesById(params.id);
  const currentBahnEvents = await getBahnEventsById(params.id);

  return (
    <TrajectoryWrapper
      currentBahnInfo={json(currentBahnInfo)}
      currentBahnPoseIst={json(currentBahnPoseIst)}
      currentBahnTwistIst={json(currentBahnTwistIst)}
      currentBahnAccelIst={json(currentBahnAccelIst)}
      currentBahnPositionSoll={json(currentBahnPositionSoll)}
      currentBahnOrientationSoll={json(currentBahnOrientationSoll)}
      currentBahnJointStates={json(currentBahnJointStates)}
      currentBahnTwistSoll={json(currentBahnTwistSoll)}
      currentBahnEvents={json(currentBahnEvents)}
    />
  );
}
