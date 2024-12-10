# csv_processor.py
import csv
import re
from datetime import datetime, timedelta
from tqdm import tqdm
from .db_config import MAPPINGS

class CSVProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mappings = MAPPINGS

    def find_path_cycles(self, rows, filename):
        """
        Find segments based on occurrences of initial AP coordinates.
        For calibration runs, creates one segment from first to last AP coordinates.
        For normal runs, creates segments between each occurrence of initial coordinates.
        Each segment includes a 0.02s buffer at start and end.
        """
        # First check if this is a calibration run
        is_calibration = "calibration_run" in filename
        
        # Find first and last AP coordinates
        first_ap_idx = None
        first_ap_time = None
        last_ap_idx = None
        last_ap_time = None

        # Find first AP coordinates
        for i, row in enumerate(rows):
            if all(row.get(f'ap_{coord}', '').strip() for coord in ['x', 'y', 'z']):
                if first_ap_idx is None:
                    first_ap_idx = i
                    first_ap_time = self.convert_timestamp(row['timestamp'])
                    print(f"First AP coordinates found at timestamp {row['timestamp']}")
                last_ap_idx = i
                last_ap_time = self.convert_timestamp(row['timestamp'])

        if first_ap_idx is None:
            return [(0, len(rows)-1)]

        print(f"Last AP coordinates found at timestamp {rows[last_ap_idx]['timestamp']}")

        if is_calibration:
            # For calibration runs, create single segment from first to last AP coordinates
            buffer_start = first_ap_time - timedelta(seconds=0.02)
            buffer_end = last_ap_time + timedelta(seconds=0.02)

            # Find actual indices with buffer
            actual_start = next(
                (j for j in range(max(0, first_ap_idx-1000), first_ap_idx + 1)
                if self.convert_timestamp(rows[j]['timestamp']) >= buffer_start),
                first_ap_idx
            )
            
            actual_end = next(
                (j for j in range(last_ap_idx, min(len(rows), last_ap_idx + 1000))
                if self.convert_timestamp(rows[j]['timestamp']) > buffer_end),
                min(len(rows), last_ap_idx + 1000) - 1
            )

            print("\nCalibration run detected - creating single segment")
            print(f"Segment with buffer: {buffer_start} to {buffer_end}")
            print(f"Final indices: {actual_start} to {actual_end}")

            return [(actual_start, actual_end)]

        else:
            # Original segmentation logic for non-calibration runs
            reference_coords = (
                float(rows[first_ap_idx]['ap_x']),
                float(rows[first_ap_idx]['ap_y']),
                float(rows[first_ap_idx]['ap_z'])
            )
            segment_starts = [(first_ap_idx, first_ap_time)]
            
            # Find all other occurrences of these coordinates
            for i in range(first_ap_idx + 1, len(rows)):
                row = rows[i]
                if all(row.get(f'ap_{coord}', '').strip() for coord in ['x', 'y', 'z']):
                    current_coords = (
                        float(row['ap_x']),
                        float(row['ap_y']),
                        float(row['ap_z'])
                    )
                    if current_coords == reference_coords:
                        segment_starts.append((i, self.convert_timestamp(row['timestamp'])))
                        print(f"Found matching coordinates at timestamp {row['timestamp']}")

            # Create segments with buffered timestamps
            segments = []
            for i in range(len(segment_starts)):
                start_idx, start_time = segment_starts[i]
                
                # Determine end point
                if i < len(segment_starts) - 1:
                    # For all segments except the last one
                    end_idx = segment_starts[i + 1][0]
                    end_time = self.convert_timestamp(rows[end_idx]['timestamp'])
                else:
                    # For the last segment: use the last AP coordinates
                    end_idx = last_ap_idx
                    end_time = last_ap_time

                # Calculate buffered timestamps
                buffer_start = start_time - timedelta(seconds=0.02)
                buffer_end = end_time + timedelta(seconds=0.02)

                # Find rows within buffered times
                actual_start = next(
                    (j for j in range(max(0, start_idx-1000), start_idx + 1)
                    if self.convert_timestamp(rows[j]['timestamp']) >= buffer_start),
                    start_idx
                )
                
                actual_end = next(
                    (j for j in range(end_idx, min(len(rows), end_idx + 1000))
                    if self.convert_timestamp(rows[j]['timestamp']) > buffer_end),
                    min(len(rows), end_idx + 1000) - 1
                )

                segments.append((actual_start, actual_end))
                
                print(f"\nSegment {i+1}:")
                if i == len(segment_starts) - 1:
                    print("Last segment - ending at last AP coordinates plus buffer")
                print(f"Reference point at index {start_idx}")
                print(f"Segment with buffer: {buffer_start} to {buffer_end}")
                print(f"Final indices: {actual_start} to {actual_end}")

            return segments

    def process_csv(self, upload_database, robot_model, bahnplanung, source_data_ist, source_data_soll, record_filename):
        """Process the CSV file and prepare data for database insertion."""
        try:
            with open(self.file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

                # Find path cycles based on reference coordinates
                filename = record_filename
                paths = self.find_path_cycles(rows, filename)
                all_processed_data = []

                for path_idx, (start_index, end_index) in enumerate(paths):
                    # Get rows for this segment (already includes buffer)
                    filtered_rows = rows[start_index:end_index+1]

                    # Get the reference point (first AP coordinates) for this segment
                    first_ap_timestamp = next(
                        (row['timestamp'] for row in filtered_rows if row.get('ap_x', '').strip()), 
                        filtered_rows[0]['timestamp']
                    )
                    bahn_id = str(first_ap_timestamp[:10])

                    recording_date = str(self.convert_timestamp(filtered_rows[0]['timestamp']))
                    start_time = str(self.convert_timestamp(filtered_rows[0]['timestamp']))
                    end_time = str(self.convert_timestamp(filtered_rows[-1]['timestamp']))

                    print(f"\nProcessing Path {path_idx + 1}")
                    print(f"Bahn ID: {bahn_id}")
                    print(f"Start Time: {start_time}")
                    print(f"End Time: {end_time}")
                    print(f"Number of rows in path: {len(filtered_rows)}")

                    # Initialize data structures for this path
                    processed_data = {key: [] for key in self.mappings.keys()}
                    processed_data['bahn_info_data'] = []

                    segment_counter = 0
                    current_segment_id = f"{bahn_id}_{segment_counter}"

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

                    # Process each row in this path
                    for row in filtered_rows:
                        timestamp = row['timestamp']

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
                    all_processed_data.append(processed_data)

                    self.print_processing_stats(len(filtered_rows), rows_processed, point_counts)

                # Moved outside the for loop
                return all_processed_data

        except Exception as e:
            print(f"An error occurred while processing the CSV: {e}")
            return None


    def process_mapping(self, row, mapping, bahn_id, current_segment_id, timestamp, source_data, data_list,
                            rows_processed, mapping_name, point_counts):
            if mapping_name == 'RAPID_EVENTS_MAPPING':
                if any(row.get(csv_col, '').strip() for csv_col in mapping):
                    data_row = [bahn_id, current_segment_id, timestamp]
                    # Convert numeric strings to float for RAPID_EVENTS_MAPPING
                    for csv_col in mapping:
                        value = row.get(csv_col, '').strip()
                        if value:
                            # Convert to float if the column is for coordinates or quaternions
                            if any(x in csv_col for x in ['x_reached', 'y_reached', 'z_reached', 
                                                        'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached']):
                                value = float(value)
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