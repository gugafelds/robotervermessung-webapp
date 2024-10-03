from pydantic import BaseModel
from typing import Optional

class BahnInfo(BaseModel):
    id: int
    bahn_id: Optional[str] = None
    robot_model: Optional[str] = None
    bahnplanung: Optional[str] = None
    recording_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    source_data_ist: Optional[str] = None
    source_data_soll: Optional[str] = None
    record_filename: Optional[str] = None
    np_ereignisse: Optional[int] = None
    frequency_pose_ist: Optional[float] = None
    frequency_position_soll: Optional[float] = None
    frequency_orientation_soll: Optional[float] = None
    frequency_twist_ist: Optional[float] = None
    frequency_twist_soll: Optional[float] = None
    frequency_accel_ist: Optional[float] = None
    frequency_joint_states: Optional[float] = None
    calibration_run: Optional[bool] = None
    np_pose_ist: Optional[int] = None
    np_twist_ist: Optional[int] = None
    np_accel_ist: Optional[int] = None
    np_pos_soll: Optional[int] = None
    np_orient_soll: Optional[int] = None
    np_twist_soll: Optional[int] = None
    np_jointstates: Optional[int] = None

    class Config:
        orm_mode = True

class BahnPoseIst(BaseModel):
    id: int
    bahnID: Optional[str] = None
    segmentID: Optional[str] = None
    timestamp: Optional[str] = None
    xIst: Optional[float] = None
    yIst: Optional[float] = None
    zIst: Optional[float] = None
    qxIst: Optional[float] = None
    qyIst: Optional[float] = None
    qzIst: Optional[float] = None
    qwIst: Optional[float] = None
    sourceDataIst: Optional[str] = None

    class Config:
        orm_mode = True

class BahnTwistIst(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    tcpSpeedX: Optional[float] = None
    tcpSpeedY: Optional[float] = None
    tcpSpeedZ: Optional[float] = None
    tcpSpeedIst: Optional[float] = None
    tcpAngularX: Optional[float] = None
    tcpAngularY: Optional[float] = None
    tcpAngularZ: Optional[float] = None
    tcpAngularIst: Optional[float] = None
    sourceDataIst: Optional[str] = None

    class Config:
        orm_mode = True

class BahnAccelIst(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    tcpAccelX: Optional[float] = None
    tcpAccelY: Optional[float] = None
    tcpAccelZ: Optional[float] = None
    tcpAccelIst: Optional[float] = None
    tcpAngularAccelX: Optional[float] = None
    tcpAngularAccelY: Optional[float] = None
    tcpAngularAccelZ: Optional[float] = None
    tcpAngularAccelIst: Optional[float] = None
    sourceDataIst: Optional[str] = None

    class Config:
        orm_mode = True

class BahnPositionSoll(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    xSoll: Optional[float] = None
    ySoll: Optional[float] = None
    zSoll: Optional[float] = None
    sourceDataSoll: Optional[str] = None

    class Config:
        orm_mode = True

class BahnOrientationSoll(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    qxSoll: Optional[float] = None
    qySoll: Optional[float] = None
    qzSoll: Optional[float] = None
    qwSoll: Optional[float] = None
    sourceDataSoll: Optional[str] = None

    class Config:
        orm_mode = True

class BahnTwistSoll(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    tcpSpeedSoll: Optional[float] = None
    sourceDataSoll: Optional[str] = None

    class Config:
        orm_mode = True

class BahnJointStates(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    joint1: Optional[float] = None
    joint2: Optional[float] = None
    joint3: Optional[float] = None
    joint4: Optional[float] = None
    joint5: Optional[float] = None
    joint6: Optional[float] = None
    sourceDataSoll: Optional[str] = None

    class Config:
        orm_mode = True

class BahnEvents(BaseModel):
    id: int
    bahnId: Optional[str] = None
    segmentId: Optional[str] = None
    timestamp: Optional[str] = None
    xReached: Optional[float] = None
    yReached: Optional[float] = None
    zReached: Optional[float] = None
    qxReached: Optional[float] = None
    qyReached: Optional[float] = None
    qzReached: Optional[float] = None
    qwReached: Optional[float] = None
    sourceDataSoll: Optional[str] = None

    class Config:
        orm_mode = True