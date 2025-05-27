import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Mappings of CSV columns to database columns
MAPPINGS = {
    'ACCEL_IST_MAPPING': {
        'tcp_accelv': 'tcp_accel_ist',
    },
    'JOINT_MAPPING': {
        'joint_1': 'joint_1',
        'joint_2': 'joint_2',
        'joint_3': 'joint_3',
        'joint_4': 'joint_4',
        'joint_5': 'joint_5',
        'joint_6': 'joint_6'
    },
    'POSE_MAPPING': {
        'pv_x': 'x_ist',
        'pv_y': 'y_ist',
        'pv_z': 'z_ist',
        'ov_x': 'qx_ist',
        'ov_y': 'qy_ist',
        'ov_z': 'qz_ist',
        'ov_w': 'qw_ist'
    },
    'RAPID_EVENTS_MAPPING': {
        'ap_x': 'x_reached',
        'ap_y': 'y_reached',
        'ap_z': 'z_reached',
        'aq_x': 'qx_reached',
        'aq_y': 'qy_reached',
        'aq_z': 'qz_reached',
        'aq_w': 'qw_reached',
    },
    'ORIENTATION_SOLL_MAPPING': {
        'os_x': 'qx_soll',
        'os_y': 'qy_soll',
        'os_z': 'qz_soll',
        'os_w': 'qw_soll'
    },
    'POSITION_SOLL_MAPPING': {
        'ps_x': 'x_soll',
        'ps_y': 'y_soll',
        'ps_z': 'z_soll',
    },
    'TWIST_IST_MAPPING': {
        'tcp_speedv': 'tcp_speed_ist',
    },
    'TWIST_SOLL_MAPPING': {
        'tcp_speedbs': 'tcp_speed_soll'
    },
    'ACCEL_SOLL_MAPPING': {
        'tcp_accelbs': 'tcp_accel_soll'
    },
    'IMU_MAPPING': {
        'tcp_accel_pi': 'tcp_accel_pi',
        'tcp_angular_vel_pi': 'tcp_angular_vel_pi',
    },
    'TRANSFORM_MAPPING': {
        'pt_x': 'x_trans',
        'pt_y': 'y_trans',
        'pt_z': 'z_trans',
        'ot_x': 'qx_trans',
        'ot_y': 'qy_trans',
        'ot_z': 'qz_trans',
        'ot_w': 'qw_trans'
    }
}