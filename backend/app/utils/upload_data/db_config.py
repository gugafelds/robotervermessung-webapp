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
    'ACCEL_ACT_MAPPING': {
        'tcp_accelv': 'tcp_accel_act',
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
        'pv_x': 'x_act_raw',
        'pv_y': 'y_act_raw',
        'pv_z': 'z_act_raw',
        'ov_x': 'qx_act_raw',
        'ov_y': 'qy_act_raw',
        'ov_z': 'qz_act_raw',
        'ov_w': 'qw_act_raw'
    },
    'RAPID_SETPOINTS_MAPPING': {
        'ap_x': 'x_reached',
        'ap_y': 'y_reached',
        'ap_z': 'z_reached',
        'aq_x': 'qx_reached',
        'aq_y': 'qy_reached',
        'aq_z': 'qz_reached',
        'aq_w': 'qw_reached',
    },
    'ORIENTATION_CMD_MAPPING': {
        'os_x': 'qx_cmd',
        'os_y': 'qy_cmd',
        'os_z': 'qz_cmd',
        'os_w': 'qw_cmd'
    },
    'POSITION_CMD_MAPPING': {
        'ps_x': 'x_cmd',
        'ps_y': 'y_cmd',
        'ps_z': 'z_cmd',
    },
    'VEL_ACT_MAPPING': {
        'tcp_speedv': 'tcp_vel_act',
    },
    'VEL_CMD_MAPPING': {
        'tcp_speedbs': 'tcp_vel_cmd'
    },
    'ACCEL_CMD_MAPPING': {
        'tcp_accelbs': 'tcp_accel_cmd'
    },
    'TRANSFORM_MAPPING': {
        'pt_x': 'x_act',
        'pt_y': 'y_act',
        'pt_z': 'z_act',
        'ot_x': 'qx_act',
        'ot_y': 'qy_act',
        'ot_z': 'qz_act',
        'ot_w': 'qw_act'
    }
}