// File: app/api/trajectory/[id]/route.ts

import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import {
  getBahnAccelIstById,
  getBahnEventsById,
  getBahnInfoById,
  getBahnJointStatesById,
  getBahnOrientationSollById,
  getBahnPoseIstById,
  getBahnPoseTransById,
  getBahnPositionSollById,
  getBahnTwistIstById,
  getBahnTwistSollById,
} from '@/src/actions/bewegungsdaten.service';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const { id } = params;

  if (!id) {
    return NextResponse.json({ error: 'Invalid id' }, { status: 400 });
  }

  try {
    const [
      currentBahnInfo,
      currentBahnPoseIst,
      currentBahnTwistIst,
      currentBahnAccelIst,
      currentBahnPositionSoll,
      currentBahnOrientationSoll,
      currentBahnTwistSoll,
      currentBahnJointStates,
      currentBahnEvents,
      currentBahnPoseTrans,
    ] = await Promise.all([
      getBahnInfoById(id),
      getBahnPoseIstById(id),
      getBahnTwistIstById(id),
      getBahnAccelIstById(id),
      getBahnPositionSollById(id),
      getBahnOrientationSollById(id),
      getBahnTwistSollById(id),
      getBahnJointStatesById(id),
      getBahnEventsById(id),
      getBahnPoseTransById(id),
    ]);

    return NextResponse.json(
      {
        currentBahnInfo,
        currentBahnPoseIst,
        currentBahnTwistIst,
        currentBahnAccelIst,
        currentBahnPositionSoll,
        currentBahnOrientationSoll,
        currentBahnTwistSoll,
        currentBahnJointStates,
        currentBahnEvents,
        currentBahnPoseTrans,
      },
      {
        headers: {
          'Cache-Control': 'no-cache',
        },
      },
    );
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error fetching trajectory data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch trajectory data' },
      { status: 500 },
    );
  }
}
