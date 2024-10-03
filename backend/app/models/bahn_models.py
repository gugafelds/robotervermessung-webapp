from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BahnInfoDB(Base):
    __tablename__ = 'bahn_info'
    __table_args__ = {'schema': 'bewegungsdaten'}

    id = Column(Integer, primary_key=True, nullable=False)
    bahn_id = Column(String(50))
    robot_model = Column(String(50))
    bahnplanung = Column(String(50))
    recording_date = Column(String(50))
    start_time = Column(String(50))
    end_time = Column(String(50))
    source_data_ist = Column(String(50))
    source_data_soll = Column(String(50))
    record_filename = Column(String(100))
    np_ereignisse = Column(Integer)
    frequency_pose_ist = Column(Float)
    frequency_position_soll = Column(Float)
    frequency_orientation_soll = Column(Float)
    frequency_twist_ist = Column(Float)
    frequency_twist_soll = Column(Float)
    frequency_accel_ist = Column(Float)
    frequency_joint_states = Column(Float)
    calibration_run = Column(Boolean)
    np_pose_ist = Column(Integer)
    np_twist_ist = Column(Integer)
    np_accel_ist = Column(Integer)
    np_pos_soll = Column(Integer)
    np_orient_soll = Column(Integer)
    np_twist_soll = Column(Integer)
    np_jointstates = Column(Integer)


class BahnPoseIstDB(Base):
    __tablename__ = "bahn_pose_ist"
    __table_args__ = {'schema': 'bewegungsdaten'}

    id = Column(Integer, primary_key=True, nullable=False)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    x_ist = Column(Float)
    y_ist = Column(Float)
    z_ist = Column(Float)
    qx_ist = Column(Float)
    qy_ist = Column(Float)
    qz_ist = Column(Float)
    qw_ist = Column(Float)
    source_data_ist = Column(String(50))

class BahnTwistIstDB(Base):
    __tablename__ = "bahn_twist_ist"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    tcp_speed_x = Column(Float)
    tcp_speed_y = Column(Float)
    tcp_speed_z = Column(Float)
    tcp_speed_ist = Column(Float)
    tcp_angular_x = Column(Float)
    tcp_angular_y = Column(Float)
    tcp_angular_z = Column(Float)
    tcp_angular_ist = Column(Float)
    source_data_ist = Column(String(50))

class BahnAccelIstDB(Base):
    __tablename__ = "bahn_accel_ist"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    tcp_accel_x = Column(Float)
    tcp_accel_y = Column(Float)
    tcp_accel_z = Column(Float)
    tcp_accel_ist = Column(Float)
    tcp_angular_accel_x = Column(Float)
    tcp_angular_accel_y = Column(Float)
    tcp_angular_accel_z = Column(Float)
    tcp_angular_accel_ist = Column(Float)
    source_data_ist = Column(String(50))

class BahnPositionSollDB(Base):
    __tablename__ = "bahn_position_soll"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    x_soll = Column(Float)
    y_soll = Column(Float)
    z_soll = Column(Float)
    source_data_soll = Column(String(50))

class BahnOrientationSollDB(Base):
    __tablename__ = "bahn_orientation_soll"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    qx_soll = Column(Float)
    qy_soll = Column(Float)
    qz_soll = Column(Float)
    qw_soll = Column(Float)
    source_data_soll = Column(String(50))

class BahnTwistSollDB(Base):
    __tablename__ = "bahn_twist_soll"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    tcp_speed_soll = Column(Float)
    source_data_soll = Column(String(50))

class BahnJointStatesDB(Base):
    __tablename__ = "bahn_joint_states"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    joint_1 = Column(Float)
    joint_2 = Column(Float)
    joint_3 = Column(Float)
    joint_4 = Column(Float)
    joint_5 = Column(Float)
    joint_6 = Column(Float)
    source_data_soll = Column(String(50))

class BahnEventsDB(Base):
    __tablename__ = "bahn_events"
    __table_args__ = {'schema': 'bewegungsdaten'}
    id = Column(Integer, primary_key=True, index=True)
    bahn_id = Column(String(50))
    segment_id = Column(String(50))
    timestamp = Column(String(50))
    x_reached = Column(Float)
    y_reached = Column(Float)
    z_reached = Column(Float)
    qx_reached = Column(Float)
    qy_reached = Column(Float)
    qz_reached = Column(Float)
    qw_reached = Column(Float)
    source_data_soll = Column(String(50))