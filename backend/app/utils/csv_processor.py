# csv_processor.py
import csv
import os
import re
from datetime import datetime, timedelta
from tqdm import tqdm
from .db_config import MAPPINGS

class CSVProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mappings = MAPPINGS

    def process_csv(self, upload_database, robot_model, bahnplanung, source_data_ist, source_data_soll, record_filename):
        """Process the CSV file and prepare data for database insertion."""
        try:
            with open(self.file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)  # Convert the reader to a list to process in reverse order

                # Find the first and last appearances of 'ap_x'
                first_ap_x_index = next((i for i, row in enumerate(rows) if row.get('ap_x', '').strip()), None)
                last_ap_x_index = next((i for i, row in enumerate(reversed(rows)) if row.get('ap_x', '').strip()), None)

                if first_ap_x_index is None or last_ap_x_index is None:
                    # If 'ap_x' is not found, use the entire dataset
                    first_timestamp = self.convert_timestamp(rows[0]['timestamp'])
                    last_timestamp = self.convert_timestamp(rows[-1]['timestamp'])
                else:
                    # Calculate the actual last index from the end of the list
                    last_ap_x_index = len(rows) - 1 - last_ap_x_index

                    # Get timestamps for the first and last 'ap_x' appearances
                    first_ap_x_timestamp = self.convert_timestamp(rows[first_ap_x_index]['timestamp'])
                    last_ap_x_timestamp = self.convert_timestamp(rows[last_ap_x_index]['timestamp'])

                    # Extend the range by 1 second on both sides
                    first_timestamp = first_ap_x_timestamp - timedelta(seconds=1)
                    last_timestamp = last_ap_x_timestamp + timedelta(seconds=1)

                # Find the indices for the extended range
                start_index = next(
                    (i for i, row in enumerate(rows) if self.convert_timestamp(row['timestamp']) >= first_timestamp), 0)
                end_index = next((i for i in range(len(rows) - 1, -1, -1) if
                                  self.convert_timestamp(rows[i]['timestamp']) <= last_timestamp), len(rows) - 1)

                filtered_rows = rows[start_index:end_index + 1]

                recording_date = self.convert_timestamp(rows[0]['timestamp'])
                start_time = self.convert_timestamp(filtered_rows[0]['timestamp'])
                end_time = self.convert_timestamp(filtered_rows[-1]['timestamp'])

                print(f"Recording Date: {recording_date}")
                print(f"Start Time: {start_time}")
                print(f"End Time: {end_time}")

                total_rows = len(filtered_rows)
                processed_data = {key: [] for key in self.mappings.keys()}
                processed_data['bahn_info_data'] = []

                bahn_id = None
                segment_counter = 0
                current_segment_id = None

                record_filename = self.extract_record_part(record_filename)

                rows_processed = {key: 0 for key in self.mappings.keys()}
                calibration_run = "calibration_run" in self.file_path

                point_counts = {
                    'np_ereignisse': 0,
                    'np_pose_ist': 0,
                    'np_twist_ist': 0,
                    'np_accel_ist': 0,
                    'np_pos_soll': 0,
                    'np_orient_soll': 0,
                    'np_twist_soll': 0,
                    'np_jointstates': 0
                }

                for row in tqdm(filtered_rows, total=total_rows, desc="Processing CSV", unit="row"):
                    timestamp = row['timestamp']
                    if bahn_id is None:
                        bahn_id = timestamp[:9]
                        current_segment_id = f"{bahn_id}_{segment_counter}"

                    if row.get('ap_x', '').strip():
                        point_counts['np_ereignisse'] += 1
                        segment_counter += 1
                        current_segment_id = f"{bahn_id}_{segment_counter}"

                    for mapping_name, mapping in self.mappings.items():
                        processed_data[mapping_name], rows_processed[mapping_name], point_counts = self.process_mapping(
                            row, mapping, bahn_id, current_segment_id, timestamp,
                            source_data_ist if mapping_name in ['ACCEL_MAPPING', 'POSE_MAPPING',
                                                                'TWIST_IST_MAPPING'] else source_data_soll,
                            processed_data[mapping_name], rows_processed[mapping_name],
                            mapping_name, point_counts
                        )

                frequencies = {
                    f"frequency_{key.lower().replace('_mapping', '')}": self.calculate_frequencies(filtered_rows,
                                                                                                   mapping)
                    for key, mapping in self.mappings.items()
                }

                if frequencies['frequency_pose'] == 0 or rows_processed['POSE_MAPPING'] == 0:
                    source_data_ist = "abb_websocket"

                bahn_info_data = (
                    bahn_id,
                    robot_model,
                    bahnplanung,
                    recording_date,
                    start_time,
                    end_time,
                    source_data_ist,
                    source_data_soll,
                    record_filename,
                    point_counts['np_ereignisse'],
                    frequencies['frequency_pose'],
                    frequencies['frequency_position_soll'],
                    frequencies['frequency_orientation_soll'],
                    frequencies['frequency_twist_ist'],
                    frequencies['frequency_twist_soll'],
                    frequencies['frequency_accel'],
                    frequencies['frequency_joint'],
                    calibration_run,
                    point_counts['np_pose_ist'],
                    point_counts['np_twist_ist'],
                    point_counts['np_accel_ist'],
                    point_counts['np_pos_soll'],
                    point_counts['np_orient_soll'],
                    point_counts['np_twist_soll'],
                    point_counts['np_jointstates']
                )

                processed_data['bahn_info_data'] = bahn_info_data

                self.print_processing_stats(total_rows, rows_processed, point_counts)

                return processed_data

        except Exception as e:
            print(f"An error occurred while processing the CSV: {e}")
        return None

    def process_mapping(self, row, mapping, bahn_id, current_segment_id, timestamp, source_data, data_list,
                            rows_processed, mapping_name, point_counts):
            if mapping_name == 'RAPID_EVENTS_MAPPING':
                if any(row.get(csv_col, '').strip() for csv_col in mapping):
                    data_row = [bahn_id, current_segment_id, timestamp]
                    for csv_col in mapping:
                        value = row.get(csv_col, '').strip()
                        data_row.append(value if value else None)
                    data_row.append(source_data)
                    data_list.append(data_row)
                    rows_processed += 1
            else:
                if all(row.get(csv_col, '').strip() for csv_col in mapping):
                    data_row = [bahn_id, current_segment_id, timestamp]
                    data_row.extend([row[csv_col] for csv_col in mapping])
                    data_row.append(source_data)
                    data_list.append(data_row)
                    rows_processed += 1

                    # Update point counts
                    if mapping_name == 'POSE_MAPPING':
                        point_counts['np_pose_ist'] += 1
                    elif mapping_name == 'TWIST_IST_MAPPING':
                        point_counts['np_twist_ist'] += 1
                    elif mapping_name == 'ACCEL_MAPPING':
                        point_counts['np_accel_ist'] += 1
                    elif mapping_name == 'POSITION_SOLL_MAPPING':
                        point_counts['np_pos_soll'] += 1
                    elif mapping_name == 'ORIENTATION_SOLL_MAPPING':
                        point_counts['np_orient_soll'] += 1
                    elif mapping_name == 'TWIST_SOLL_MAPPING':
                        point_counts['np_twist_soll'] += 1
                    elif mapping_name == 'JOINT_MAPPING':
                        point_counts['np_jointstates'] += 1

            return data_list, rows_processed, point_counts
    @staticmethod
    def convert_timestamp(ts):
        try:
            timestamp_seconds = int(ts) / 1_000_000_000.0
            return datetime.fromtimestamp(timestamp_seconds)
        except ValueError as e:
            print(f"Error converting timestamp {ts}: {e}")
            return None

    def calculate_frequencies(self, rows, column_mapping):
        timestamps = [self.convert_timestamp(row['timestamp']) for row in rows if row.get(list(column_mapping.keys())[0])]
        if not timestamps:
            return 0.0
        diffs = [(timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        return 1 / avg_diff if avg_diff > 0 else 0.0

    def extract_record_part(self, record_filename):
        if 'record' in record_filename:
            match = re.search(r'(record_\d{8}_\d{6})', record_filename)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def print_processing_stats(total_rows, rows_processed, point_counts):
        print(f"\nTotal rows processed in range: {total_rows}")
        for key, value in rows_processed.items():
            print(f"Rows processed for {key}: {value}")
            print(f"Rows skipped for {key}: {total_rows - value}")

        print("\nPoint counts:")
        for key, value in point_counts.items():
            print(f"{key}: {value}")