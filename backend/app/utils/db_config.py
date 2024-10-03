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
    'ACCEL_MAPPING': {
        'tcp_accelv__x': 'tcp_accel_x',
        'tcp_accelv__y': 'tcp_accel_y',
        'tcp_accelv__z': 'tcp_accel_z',
        'tcp_accelv': 'tcp_accel_ist',
        'tcp_accelv_angular_x': 'tcp_angular_accel_x',
        'tcp_accelv_angular_y': 'tcp_angular_accel_y',
        'tcp_accelv_angular_z': 'tcp_angular_accel_z',
        'tcp_accelv_angular': 'tcp_angular_accel_ist'
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
        'aq_w': 'qw_reached'
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
        'tcp_speedv_x': 'tcp_speed_x',
        'tcp_speedv_y': 'tcp_speed_y',
        'tcp_speedv_z': 'tcp_speed_z',
        'tcp_speedv': 'tcp_speed_ist',
        'tcp_angularv_x': 'tcp_angular_x',
        'tcp_angularv_y': 'tcp_angular_y',
        'tcp_angularv_z': 'tcp_angular_z',
        'tcp_angularv': 'tcp_angular_ist'
    },
    'TWIST_SOLL_MAPPING': {
        'tcp_speeds': 'tcp_speed_soll'
    }
}