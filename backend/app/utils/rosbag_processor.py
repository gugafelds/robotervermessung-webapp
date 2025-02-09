import rclpy
from rclpy.node import Node
import pandas as pd
import rosbag2_py
from rosidl_runtime_py.utilities import get_message
from rclpy.serialization import deserialize_message

from geometry_msgs.msg import Point, Pose, Quaternion, PoseStamped, AccelStamped, TwistStamped
from std_msgs.msg import Float64, UInt8, String, UInt16
from sensor_msgs.msg import JointState, Imu
import numpy as np
from pathlib import Path
import os

class RosbagProcessor(Node):
    def __init__(self):
        super().__init__('rosbag_processor')
        self.declare_parameter('topics', [
            '/vrpn_mocap/abb4400_tcp/pose',
            '/vrpn_mocap/abb4400_tcp/twist',
            '/vrpn_mocap/abb4400_tcp/accel',
            '/socket_data/position',
            '/socket_data/orientation',
            '/socket_data/tcp_speed',
            '/parameter_events',
            '/socket_data/joint_states',
            '/socket_data/achieved_position', '/socket_data/do_value', '/socket_data/weight',
            '/socket_data/movement_type', '/socket_data/velocity_picking', '/socket_data/velocity_handling', '/imu'
        ])
        self.topics = self.get_parameter('topics').get_parameter_value().string_array_value
        self.merged_output_directory = None
        self.bag_file = None

    def process_single_bag(self, bag_path: str, output_directory: str):
        """Process a single ROSBAG file"""
        try:
            self.merged_output_directory = output_directory
            self.bag_file = os.path.basename(bag_path).split('.')[0]  # Get filename without extension

            # Check if output directory exists, create if not
            os.makedirs(output_directory, exist_ok=True)

            merged_filename = os.path.join(self.merged_output_directory, f'{self.bag_file}_final.csv')

            # Check if merged CSV file already exists
            if os.path.exists(merged_filename):
                self.get_logger().info(f'Merged CSV file {merged_filename} already exists. Skipping processing.')
                return False

            self.process_bag(bag_path)
            return True

        except Exception as e:
            self.get_logger().error(f'Error processing bag file {bag_path}: {str(e)}')
            raise Exception(f'Failed to process {os.path.basename(bag_path)}: {str(e)}')

    def process_bag(self, bag_directory):
        storage_options = rosbag2_py.StorageOptions(uri=bag_directory, storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions(input_serialization_format='cdr',
                                                        output_serialization_format='cdr')
        reader = rosbag2_py.SequentialReader()
        reader.open(storage_options, converter_options)

        topic_type_map = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
        topic_data = {topic: [] for topic in self.topics}

        while reader.has_next():
            try:
                (topic, data, t) = reader.read_next()
                if topic in self.topics:
                    msg_type_str = topic_type_map[topic]
                    msg_type = get_message(msg_type_str)
                    msg = deserialize_message(data, msg_type)
                    topic_data[topic].append((t, msg))
            except Exception as e:
                self.get_logger().error(f'Error reading message from bag: {e}')
                break

        self.save_to_individual_csv(topic_data)

    def calculate_magnitude(self, x, y, z):
        return np.sqrt(x ** 2 + y ** 2 + z ** 2)

    def save_to_individual_csv(self, topic_data):
        for topic, data in topic_data.items():
            if data:
                parsed_data = []
                columns = []
                for t, msg in data:
                    if topic == "/socket_data/achieved_position":
                        if isinstance(msg, Point):

                            parsed_data.append([t, msg.x, msg.y, msg.z])
                            columns = ['timestamp', 'ap_x', 'ap_y', 'ap_z']
                        elif isinstance(msg, Pose):
                            parsed_data.append([
                                t,
                                msg.position.x, msg.position.y, msg.position.z,
                                msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w
                            ])
                            columns = ['timestamp', 'ap_x', 'ap_y', 'ap_z', 'aq_x', 'aq_y', 'aq_z', 'aq_w']
                    elif isinstance(msg, UInt8) and topic == '/socket_data/do_value':
                        parsed_data.append([t, msg.data])
                        columns = ['timestamp', 'DO_Signal']
                    elif isinstance(msg, String) and topic == '/socket_data/movement_type':
                        parsed_data.append([t, msg.data])
                        columns = ['timestamp', 'Movement Type']
                    elif isinstance(msg, Float64) and topic == '/socket_data/weight':
                        parsed_data.append([t, msg.data])
                        columns = ['timestamp', 'Weight']
                    elif isinstance(msg, UInt16) and topic == '/socket_data/velocity_picking':
                        parsed_data.append([t, msg.data])
                        columns = ['timestamp', 'Velocity Picking']
                    elif isinstance(msg, UInt16) and topic == '/socket_data/velocity_handling':
                        parsed_data.append([t, msg.data])
                        columns = ['timestamp', 'Velocity Handling']
                    elif isinstance(msg, Imu) and topic == '/imu':
                        acc_magnitude = self.calculate_magnitude(
                            msg.linear_acceleration.x,
                            msg.linear_acceleration.y,
                            msg.linear_acceleration.z
                        )
                        ang_vel_magnitude = self.calculate_magnitude(
                            msg.angular_velocity.x,
                            msg.angular_velocity.y,
                            msg.angular_velocity.z
                        )
                        parsed_data.append([
                            t,
                            acc_magnitude,
                            ang_vel_magnitude
                        ])
                        columns = ['timestamp', 'tcp_accel_pi', 'tcp_angular_vel_pi']
                    elif isinstance(msg, Point) and topic == "/socket_data/position":
                        parsed_data.append([t, msg.x, msg.y, msg.z])
                        columns = ['timestamp', 'ps_x', 'ps_y', 'ps_z']
                    elif isinstance(msg, Quaternion):
                        parsed_data.append([
                            t,
                            msg.x,
                            msg.y,
                            msg.z,
                            msg.w
                        ])
                        columns = ['timestamp', 'os_x', 'os_y', 'os_z', 'os_w']
                    elif isinstance(msg, Float64) and topic == '/socket_data/tcp_speed':
                        parsed_data.append([
                            t,
                            msg.data
                        ])
                        columns = ['timestamp', 'tcp_speeds']
                    elif isinstance(msg, JointState):
                        joint_positions = list(msg.position)

                        # Flatten the joint_positions if it contains nested lists
                        joint_positions_flat = []
                        for item in joint_positions:
                            if isinstance(item, list):
                                joint_positions_flat.extend(item)
                            else:
                                joint_positions_flat.append(item)

                        parsed_data.append([t] + joint_positions_flat[:6])  # Ensure only the first 6 positions are used
                        columns = ['timestamp'] + [f'joint_{i + 1}' for i in range(6)]

                        if len(parsed_data) == 13:
                            print("Debug Info: JointState Parsed Data with 13 columns")

                    elif isinstance(msg, PoseStamped):
                        parsed_data.append([
                            t,
                            msg.header.stamp.sec,
                            msg.header.stamp.nanosec,
                            msg.pose.position.x * 1000,
                            msg.pose.position.y * 1000,
                            msg.pose.position.z * 1000,
                            msg.pose.orientation.x,
                            msg.pose.orientation.y,
                            msg.pose.orientation.z,
                            msg.pose.orientation.w
                        ])
                        columns = [
                            'timestamp', 'sec', 'nanosec',
                            'pv_x', 'pv_y', 'pv_z', 'ov_x', 'ov_y', 'ov_z', 'ov_w'
                        ]

                    elif isinstance(msg, TwistStamped):
                        linear_velocity = self.calculate_magnitude(msg.twist.linear.x, msg.twist.linear.y,
                                                                   msg.twist.linear.z)
                        angular_velocity = self.calculate_magnitude(msg.twist.angular.x, msg.twist.angular.y,
                                                                    msg.twist.angular.z)
                        parsed_data.append([
                            t,
                            msg.header.stamp.sec,
                            msg.header.stamp.nanosec,
                            linear_velocity * 1000,
                            angular_velocity
                        ])
                        columns = [
                            'timestamp', 'sec', 'nanosec',
                            'tcp_speedv', 'tcp_angularv'
                        ]
                    elif isinstance(msg, AccelStamped):
                        linear_acceleration = self.calculate_magnitude(msg.accel.linear.x, msg.accel.linear.y,
                                                                       msg.accel.linear.z)
                        angular_acceleration = self.calculate_magnitude(msg.accel.angular.x, msg.accel.angular.y,
                                                                        msg.accel.angular.z)
                        parsed_data.append([
                            t,
                            msg.header.stamp.sec,
                            msg.header.stamp.nanosec,
                            linear_acceleration,
                            angular_acceleration
                        ])
                        columns = [
                            'timestamp', 'sec', 'nanosec',
                            'tcp_accelv',
                            'tcp_accelv_angular'
                        ]

                if parsed_data and columns:
                    df = pd.DataFrame(parsed_data, columns=columns)
                    csv_file = os.path.join(self.merged_output_directory,
                                            self.bag_file + f'{topic.replace("/", "_")}.csv')
                    df.to_csv(csv_file, index=False)
                    self.get_logger().info(f'Saved topic {topic} data to {csv_file}.')

        self.merge_csv_files()

    def merge_csv_files(self):
        mocap_topics = ['/vrpn_mocap/abb4400_tcp/pose', '/vrpn_mocap/abb4400_tcp/twist',
                        '/vrpn_mocap/abb4400_tcp/accel']
        websocket_topics = ['/socket_data/position', '/socket_data/orientation', '/socket_data/tcp_speed',
                            '/socket_data/joint_states', '/socket_data/achieved_position', '/socket_data/do_value',
                            '/socket_data/weight', '/socket_data/movement_type', '/socket_data/velocity_picking',
                            '/socket_data/velocity_handling', '/imu']
        both_topics = mocap_topics + websocket_topics

        # Separate merge logic for mocap and websocket data
        self.merge_individual_csv_files(mocap_topics, "mocap")
        self.merge_individual_csv_files(websocket_topics, "websocket")
        self.merge_individual_csv_files(both_topics, "mocap+websocket")

    def merge_individual_csv_files(self, topics, data_type):
        # Collect all CSV files for the specified topics
        all_csv_files = []
        for topic in topics:
            csv_file_path = os.path.join(self.merged_output_directory, self.bag_file + f'{topic.replace("/", "_")}.csv')
            if os.path.exists(csv_file_path):
                all_csv_files.append(csv_file_path)

        # Load all dataframes from the collected CSV files
        dataframes = []
        for file in all_csv_files:
            df = pd.read_csv(file)
            df['source'] = os.path.basename(file)  # Add a column to indicate the source file
            dataframes.append(df)

        if dataframes:
            merged_df = pd.concat(dataframes, ignore_index=True).sort_values(by=['timestamp']).reset_index(drop=True)

            # Remove the 'source' column
            merged_df.drop(columns=['source'], inplace=True)

            # Define base columns for each data type
            if data_type == "mocap":
                all_columns = [
                    'timestamp', 'sec', 'nanosec',
                    'pv_x', 'pv_y', 'pv_z', 'ov_x', 'ov_y', 'ov_z', 'ov_w',
                    'tcp_speedv', 'tcp_angularv',
                    'tcp_accelv',
                    'tcp_accelv_angular'
                ]
            elif data_type == "websocket":
                all_columns = [
                                  'timestamp', 'ps_x', 'ps_y', 'ps_z',
                                  'os_x', 'os_y', 'os_z', 'os_w'
                              ] + [f'joint_{i + 1}' for i in range(6)] + ['ap_x', 'ap_y', 'ap_z',
                                                                          'tcp_speeds', 'DO_Signal', 'Movement Type',
                                                                          'Weight', 'Velocity Picking',
                                                                          'Velocity Handling', 'tcp_accel_pi',
                                                                          'tcp_angular_vel_pi']
            elif data_type == "mocap+websocket":
                all_columns = [
                                  'timestamp', 'sec', 'nanosec',
                                  'pv_x', 'pv_y', 'pv_z', 'ov_x', 'ov_y', 'ov_z', 'ov_w',
                                  'tcp_speedv', 'tcp_angularv',
                                  'tcp_accelv',
                                  'tcp_accelv_angular',
                                  'ps_x', 'ps_y', 'ps_z',
                                  'os_x', 'os_y', 'os_z', 'os_w',
                                  'tcp_speeds'
                              ] + [f'joint_{i + 1}' for i in range(6)] + [
                                  'ap_x', 'ap_y', 'ap_z'
                              ]

                # Add orientation columns if they exist in any of the dataframes
                if any('aq_x' in df.columns for df in dataframes):
                    all_columns.extend(['aq_x', 'aq_y', 'aq_z', 'aq_w'])

                # Add remaining columns
                all_columns.extend([
                    'DO_Signal', 'Movement Type', 'Weight',
                    'Velocity Picking', 'Velocity Handling', 'tcp_accel_pi', 'tcp_angular_vel_pi'
                ])

            # Ensure that the columns that don't exist in certain dataframes are filled with NaN
            for col in all_columns:
                if col not in merged_df.columns:
                    merged_df[col] = np.nan

            # Reorder columns
            merged_df = merged_df[all_columns]

            # Save the merged CSV file
            merged_filename = os.path.join(self.merged_output_directory, f'{self.bag_file}_final.csv')
            merged_df.to_csv(merged_filename, index=False)
            self.get_logger().info(f'Merged individual {data_type} CSV files into {merged_filename}.')
        else:
            self.get_logger().info(f'No {data_type} CSV files found to merge.')


def main(args=None):
    rclpy.init(args=args)
    rosbag_processor = RosbagProcessor()
    rclpy.spin(rosbag_processor)
    rosbag_processor.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()