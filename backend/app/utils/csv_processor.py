# csv_processor.py
import csv
import math
import re
from datetime import datetime, timedelta
from .db_config import MAPPINGS

class CSVProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mappings = MAPPINGS

    def find_path_cycles(self, rows, filename, segmentation_method='home', num_segments=1):
        """
        Find segments based on the specified method:
        - 'home': Home position detection
        - 'fixed': Fixed number of segments
        - 'pickplace': Pick and place operation segments
        """
        # First check if this is a special type of run
        is_calibration = "calibration_run" in filename
        is_pickplace = "pickplace" in filename

        if is_calibration:
            return self.create_calibration_segment(rows)
        elif is_pickplace:
            segments, modified_rows = self.create_pickplace_segments(rows)
            # Store modified rows for later use
            self.rows = modified_rows  # Add this line
            return segments
        else:
            return self.create_home_position_segments(rows)
    
    def create_calibration_segment(self, rows):
        """Creates a single segment for calibration runs."""
        # Find first and last AP coordinates
        first_ap_idx = None
        first_ap_time = None
        last_ap_idx = None
        last_ap_time = None

        for i, row in enumerate(rows):
            if all(row.get(f'ap_{coord}', '').strip() for coord in ['x', 'y', 'z']):
                if first_ap_idx is None:
                    first_ap_idx = i
                    first_ap_time = self.convert_timestamp(row['timestamp'])
                last_ap_idx = i
                last_ap_time = self.convert_timestamp(row['timestamp'])

        if first_ap_idx is None:
            return [(0, len(rows)-1)]

        # Add buffer
        buffer_start = first_ap_time - timedelta(seconds=0.02)
        buffer_end = last_ap_time + timedelta(seconds=0.02)

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

        return [(actual_start, actual_end)]

    def create_fixed_segments(self, rows, segments_per_group):
        """Creates fixed-size groups of segments."""
        # First, find all AP coordinates
        ap_indices = []
        for i, row in enumerate(rows):
            if all(row.get(f'ap_{coord}', '').strip() for coord in ['x', 'y', 'z']):
                ap_indices.append(i)

        if not ap_indices:
            return [(0, len(rows)-1)]

        # Create groups of segments
        groups = []
        current_group = []
        
        for i, idx in enumerate(ap_indices):
            current_group.append(idx)
            
            # When we reach the desired size or it's the last element
            if len(current_group) == segments_per_group or i == len(ap_indices) - 1:
                # If this is the last group and it only has one segment
                if i == len(ap_indices) - 1 and len(current_group) == 1 and groups:
                    # Add it to the previous group
                    groups[-1].extend(current_group)
                else:
                    groups.append(current_group)
                current_group = []

        # Convert groups to segments with buffers
        segments = []
        for group in groups:
            start_idx = group[0]
            end_idx = group[-1]
            
            start_time = self.convert_timestamp(rows[start_idx]['timestamp'])
            end_time = self.convert_timestamp(rows[end_idx]['timestamp'])
            
            buffer_start = start_time - timedelta(seconds=0.02)
            buffer_end = end_time + timedelta(seconds=0.02)
            
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

        return segments

    def create_home_position_segments(self, rows):
        """Original method that creates segments based on home position detection."""
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
                last_ap_idx = i
                last_ap_time = self.convert_timestamp(row['timestamp'])

        if first_ap_idx is None:
            return [(0, len(rows)-1)]

        # Find all occurrences of home position
        reference_coords = (
            float(rows[first_ap_idx]['ap_x']),
            float(rows[first_ap_idx]['ap_y']),
            float(rows[first_ap_idx]['ap_z'])
        )
        segment_starts = [(first_ap_idx, first_ap_time)]
        
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

        # Create segments
        segments = []
        for i in range(len(segment_starts)):
            start_idx, start_time = segment_starts[i]
            
            if i < len(segment_starts) - 1:
                end_idx = segment_starts[i + 1][0]
                end_time = self.convert_timestamp(rows[end_idx]['timestamp'])
            else:
                end_idx = last_ap_idx
                end_time = last_ap_time

            buffer_start = start_time - timedelta(seconds=0.02)
            buffer_end = end_time + timedelta(seconds=0.02)

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

        return segments

    def create_pickplace_segments(self, rows):
        total_rows = len(rows)
        modified_rows = rows.copy()

        #print("\n=== Starting Pick & Place Segment Analysis ===")
        #print(f"Total rows: {total_rows}")

        # Find all 1.0 signal positions but group consecutive ones
        one_signal_groups = []
        current_group = []
        #print("\n--- Finding Signal Groups ---")
        for i, row in enumerate(rows):
            if row.get('DO_Signal', '').strip() == '1.0':
                if not current_group or i - current_group[-1] < 30:
                    current_group.append(i)
                else:
                    if current_group:
                        #print(f"Found signal group at indices: {current_group}")
                        one_signal_groups.append(current_group)
                    current_group = [i]
        if current_group:
            one_signal_groups.append(current_group)
            #print(f"Found final signal group at indices: {current_group}")

        #print(f"\nTotal signal groups found: {len(one_signal_groups)}")

        # Process only the first 1.0 signal of each group
        #print("\n--- Processing AP/AQ Values ---")
        for group in one_signal_groups:
            first_index = group[0]
            #print(f"\nProcessing group starting at index {first_index}")

            # Look backwards for last AP/AQ values
            last_ap_aq = None
            for i in range(first_index - 1, -1, -1):
                row = rows[i]
                if all(row.get(col, '').strip() for col in
                       ['ap_x', 'ap_y', 'ap_z', 'aq_x', 'aq_y', 'aq_z', 'aq_w']):
                    last_ap_aq = {
                        'ap_x': row['ap_x'],
                        'ap_y': row['ap_y'],
                        'ap_z': row['ap_z'],
                        'aq_x': row['aq_x'],
                        'aq_y': row['aq_y'],
                        'aq_z': row['aq_z'],
                        'aq_w': row['aq_w']
                    }
                    #print(f"Found AP/AQ values at index {i}:")
                    #print(last_ap_aq)
                    break

            if last_ap_aq:
                #print(f"Updating modified_rows at index {first_index} with AP/AQ values")
                modified_rows[first_index].update(last_ap_aq)
            else:
                print(f"WARNING: No AP/AQ values found before index {first_index}")

        # Create segments
        # print("\n--- Creating Segments ---")
        segments = []
        current_position = 0

        while current_position < total_rows:
            #print(f"\nLooking for next segment starting at position {current_position}")

            # Find next 1.0 signal
            close_idx = next((i for i in range(current_position, total_rows)
                              if modified_rows[i].get('DO_Signal', '').strip() == '1.0'), None)
            if close_idx is None:
                #print("No more 1.0 signals found")
                break

            # Find next 0.0 signal
            open_idx = next((i for i in range(close_idx + 1, total_rows)
                             if modified_rows[i].get('DO_Signal', '').strip() == '0.0'), None)
            if open_idx is None:
                #print(f"No matching 0.0 signal found after 1.0 signal at {close_idx}")
                break

            #print(f"Found potential segment: 1.0 at {close_idx} to 0.0 at {open_idx}")

            # Calculate segment with buffers
            start_time = self.convert_timestamp(modified_rows[close_idx]['timestamp'])
            end_time = self.convert_timestamp(modified_rows[open_idx]['timestamp'])

            buffer_start = start_time - timedelta(seconds=0.02)
            buffer_end = end_time + timedelta(seconds=0.02)

            search_range_start = max(0, close_idx - int(1.0 * 1000))
            search_range_end = min(total_rows, open_idx + int(1.0 * 1000))

            actual_start = next(
                (j for j in range(search_range_start, close_idx + 1)
                 if self.convert_timestamp(rows[j]['timestamp']) >= buffer_start),
                close_idx
            )

            actual_end = next(
                (j for j in range(open_idx, search_range_end)
                 if self.convert_timestamp(rows[j]['timestamp']) > buffer_end),
                min(total_rows, open_idx + 1000) - 1
            )

            #print(f"Final segment boundaries: {actual_start} to {actual_end}")

            # Check for AP coordinates in segment
            ap_coords = []
            for i in range(actual_start, actual_end + 1):
                if all(modified_rows[i].get(f'ap_{coord}', '').strip() for coord in ['x', 'y', 'z']):
                    ap_coords.append(i)
            #print(f"AP coordinates found at indices: {ap_coords}")

            segments.append((actual_start, actual_end))
            current_position = open_idx + 1

        #print("\n=== Segment Analysis Complete ===")
        #print(f"Total segments created: {len(segments)}")
        if len(segments) != 4:
            print("WARNING: Number of segments is not 4!")
            print(f"Found {len(segments)} segments: {segments}")

        return segments, modified_rows

    def process_csv(self, upload_database, robot_model, bahnplanung, source_data_ist,
                    source_data_soll, record_filename, segmentation_method='home', num_segments=1):
        """Process the CSV file and prepare data for database insertion."""

        print('Processing CSV file: ' + record_filename + '!')
        try:
            with open(self.file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

                # Initialize pick and place specific variables
                weight = None
                velocity_picking = None
                velocity_handling = None
                is_pickplace = "pickplace" in record_filename
                self.record_filename = record_filename

                # Pick and place position variables
                x_start_pos = None
                y_start_pos = None
                z_start_pos = None
                x_end_pos = None
                y_end_pos = None
                z_end_pos = None
                handling_height = None
                # Quaternion variables
                qx_start = None
                qy_start = None
                qz_start = None
                qw_start = None
                qx_end = None
                qy_end = None
                qz_end = None
                qw_end = None

                if is_pickplace:
                    for row in rows:
                        if velocity_picking is None and row.get('Velocity Picking', '').strip():
                            try:
                                velocity_picking = float(row['Velocity Picking'])
                            except ValueError:
                                print(f"Warning: Could not convert Velocity Picking value: {row['Velocity Picking']}")

                        if velocity_handling is None and row.get('Velocity Handling', '').strip():
                            try:
                                velocity_handling = float(row['Velocity Handling'])
                            except ValueError:
                                print(f"Warning: Could not convert Velocity Handling value: {row['Velocity Handling']}")

                        if weight is None and row.get('Weight', '').strip():
                            try:
                                weight = float(row['Weight'])
                            except ValueError:
                                print(f"Warning: Could not convert weight value: {row['Weight']}")

                        # Break if we found all values
                        if all(v is not None for v in [velocity_picking, velocity_handling, weight]):
                            break

                    # Debug output to verify values
                    # print(f"Found values: velocity_picking={velocity_picking}, "
                    #      f"velocity_handling={velocity_handling}, weight={weight}")

                # Find path cycles based on reference coordinates
                paths = self.find_path_cycles(rows, record_filename,
                                              segmentation_method, num_segments)
                all_processed_data = []

                for path_idx, (start_index, end_index) in enumerate(paths):
                    # Reset position tracking for each path when doing pick and place
                    if is_pickplace:
                        segment_state = 0  # Track which segment we're in (0, 1, or 2)
                        x_start_pos = None
                        y_start_pos = None
                        z_start_pos = None
                        x_end_pos = None
                        y_end_pos = None
                        z_end_pos = None
                        handling_height = None
                        qx_start = None
                        qy_start = None
                        qz_start = None
                        qw_start = None
                        qx_end = None
                        qy_end = None
                        qz_end = None
                        qw_end = None

                    filtered_rows = self.rows[start_index:end_index + 1] if hasattr(self, 'rows') else rows[start_index:end_index + 1]
                    movement_types = {}


                    first_ap_timestamp = next(
                        (row['timestamp'] for row in filtered_rows if row.get('ap_x', '').strip()),
                        filtered_rows[0]['timestamp']
                    )
                    bahn_id = str(first_ap_timestamp[:10])

                    recording_date = str(self.convert_timestamp(filtered_rows[0]['timestamp']))
                    start_time = str(self.convert_timestamp(filtered_rows[0]['timestamp']))
                    end_time = str(self.convert_timestamp(filtered_rows[-1]['timestamp']))

                    processed_data = {key: [] for key in self.mappings.keys()}
                    processed_data['bahn_info_data'] = []

                    segment_counter = 0
                    current_segment_id = f"{bahn_id}_{segment_counter}"

                    rows_processed = {key: 0 for key in self.mappings.keys()}
                    calibration_run = "calibration_run" in record_filename

                    if "pickplace" in record_filename:
                        segment_counter = 0
                        for row in filtered_rows:
                            if row.get('ap_x', '').strip():
                                segment_counter += 1
                                segment_id = f"{bahn_id}_{segment_counter}"

                                # Determine movement type based on segment position
                                if segment_counter % 4 == 0:  # Approach
                                    movement_types[segment_id] = "linear"
                                    #print(f"Segment {segment_id}: Setting linear (approach)")
                                elif segment_counter % 4 == 1:  # Pick
                                    movement_types[segment_id] = "linear"
                                    #print(f"Segment {segment_id}: Setting linear (pick)")
                                elif segment_counter % 4 == 2:  # Handling movement
                                    try:
                                        # This segment represents the movement between points 2 and 3
                                        # where z-height is constant (1046.7 in your example)
                                        movement_type = self.calculate_direction(filtered_rows)
                                        movement_types[segment_id] = movement_type
                                        #print(f"Segment {segment_id}: Calculated {movement_type} (handling)")
                                    except Exception as e:
                                        print(f"Error calculating direction for segment {segment_id}: {e}")
                                        movement_types[segment_id] = None
                                else:  # Place (segment_counter % 4 == 0)
                                    movement_types[segment_id] = "linear"
                                    #print(f"Segment {segment_id}: Setting linear (place)")


                    # Reset segment counter again for the main processing
                    segment_counter = 0

                    point_counts = {
                        'np_ereignisse': 0,
                        'np_pose_ist': 0,
                        'np_twist_ist': 0,
                        'np_accel_ist': 0,
                        'np_pos_soll': 0,
                        'np_orient_soll': 0,
                        'np_twist_soll': 0,
                        'np_jointstates': 0,
                        'np_imu': 0
                    }

                    # Process each row
                    for row in filtered_rows:
                        timestamp = row['timestamp']

                        if row.get('ap_x', '').strip():
                            if is_pickplace:
                                # Track positions for pick and place operations
                                if segment_state == 0:  # First position
                                    x_start_pos = float(row['ap_x'])
                                    y_start_pos = float(row['ap_y'])
                                    qx_start = float(row['aq_x'])
                                    qy_start = float(row['aq_y'])
                                    qz_start = float(row['aq_z'])
                                    qw_start = float(row['aq_w'])
                                elif segment_state == 1:  # Handling height
                                    handling_height = float(row['ap_z'])
                                    z_start_pos = float(row['ap_z'])
                                elif segment_state == 2:  # End position
                                    x_end_pos = float(row['ap_x'])
                                    y_end_pos = float(row['ap_y'])
                                    z_end_pos = float(row['ap_z'])
                                    qx_end = float(row['aq_x'])
                                    qy_end = float(row['aq_y'])
                                    qz_end = float(row['aq_z'])
                                    qw_end = float(row['aq_w'])
                                segment_state += 1

                            point_counts['np_ereignisse'] += 1
                            segment_counter += 1
                            current_segment_id = f"{bahn_id}_{segment_counter}"

                        for mapping_name, mapping in self.mappings.items():
                            processed_data[mapping_name], rows_processed[
                                mapping_name], point_counts = self.process_mapping(
                                row, mapping, bahn_id, current_segment_id, timestamp,
                                source_data_ist if mapping_name in ['ACCEL_MAPPING', 'POSE_MAPPING',
                                                                    'TWIST_IST_MAPPING'] else source_data_soll,
                                processed_data[mapping_name], rows_processed[mapping_name],
                                mapping_name, point_counts, movement_types  # Add movement_types here
                            )


                    frequencies = {
                        f"frequency_{key.lower().replace('_mapping', '')}": self.calculate_frequencies(filtered_rows,
                                                                                                       mapping)
                        for key, mapping in self.mappings.items()
                    }

                    if frequencies['frequency_pose'] == 0 or rows_processed['POSE_MAPPING'] == 0:
                        source_data_ist = "abb_websocket"

                    # Create base bahn_info_data tuple
                    base_info = [
                        bahn_id,
                        robot_model,
                        bahnplanung,
                        recording_date,
                        start_time,
                        end_time,
                        source_data_ist,
                        source_data_soll,
                        self.extract_record_part(record_filename),
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
                        point_counts['np_jointstates'],
                    ]

                    # Add pick and place specific data if applicable
                    if is_pickplace:
                        bahn_info_data = tuple(base_info + [
                            weight,
                            x_start_pos,
                            y_start_pos,
                            z_start_pos,
                            x_end_pos,
                            y_end_pos,
                            z_end_pos,
                            handling_height,
                            qx_start,
                            qy_start,
                            qz_start,
                            qw_start,
                            qx_end,
                            qy_end,
                            qz_end,
                            qw_end,
                            velocity_handling,
                            velocity_picking,
                            frequencies['frequency_imu'],
                            is_pickplace,
                            point_counts['np_imu'],
                        ])
                    else:
                        bahn_info_data = tuple(base_info)

                    processed_data['bahn_info_data'] = bahn_info_data
                    #print(bahn_info_data)
                    all_processed_data.append(processed_data)

                    #self.print_processing_stats(len(filtered_rows), rows_processed, point_counts)

                return all_processed_data

        except Exception as e:
            print(f"An error occurred while processing the CSV: {e}")
            return None

    def process_mapping(self, row, mapping, bahn_id, current_segment_id, timestamp, source_data, data_list,
                        rows_processed, mapping_name, point_counts, movement_types=None):

        def convert_value(value):
            """Helper function to convert values, properly handling zeros"""
            if value.strip() == '0' or value.strip() == '0.0':
                return 0.0
            elif value.strip():
                try:
                    return float(value)
                except ValueError:
                    print(f"Warning: Could not convert value: {value}")
                    return None
            return None

        if mapping_name == 'RAPID_EVENTS_MAPPING':
            if any(row.get(csv_col, '').strip() for csv_col in mapping):
                data_row = [bahn_id, current_segment_id, timestamp]
                values = []

                # Process normal values (positions and orientations)
                for csv_col in mapping:
                    value = row.get(csv_col, '')
                    if any(x in csv_col for x in ['x_reached', 'y_reached', 'z_reached',
                                                  'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached']):
                        values.append(convert_value(value))
                    else:
                        values.append(value.strip() if value.strip() else None)

                data_row.extend(values)  # Add position values
                data_row.append(source_data)  # Add source_data before movement_type

                # Add movement_type last
                if "pickplace" in self.record_filename and movement_types:
                    movement_type = movement_types.get(current_segment_id)
                    data_row.append(movement_type)
                else:
                    data_row.append(None)

                data_list.append(data_row)
                rows_processed += 1

        else:  # ACCEL_MAPPING, TWIST_IST_MAPPING, etc.
            if all(row.get(csv_col, '').strip() for csv_col in mapping):
                data_row = [bahn_id, current_segment_id, timestamp]
                values = []
                for csv_col in mapping:
                    value = row.get(csv_col, '')
                    converted_value = convert_value(value)
                    values.append(converted_value)

                data_row.extend(values)
                # Use 'sensehat' as source for IMU data
                if mapping_name == 'IMU_MAPPING':
                    data_row.append('sensehat')
                else:
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
                elif mapping_name == 'IMU_MAPPING':
                    point_counts['np_imu'] += 1

        # Make sure we always return these three values
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

    # Funktion zur Berechnung der Richtung
    def convert_to_float(self, value):
        """Hilfsfunktion zur Umwandlung eines Strings in einen float."""
        try:
            return float(value)
        except ValueError:
            return None  # Falls der Wert nicht in einen float umgewandelt werden kann, None zurückgeben

    def calculate_direction(self, bahn_rows):
        """
        Bestimmt die Richtung basierend auf allen Punkten zwischen Start und Ende in der Tabelle.
        :param bahn_rows: Liste von Dictionaries mit den Schlüsseln 'ps_x' und 'ps_y'
        :return: 'linear', 'circularleft' oder 'circularright'
        """
        # Schritt 1: Finde die maximale Z-Höhe (Handling-Höhe)
        handling_height = None
        for row in bahn_rows:
            ap_z = self.convert_to_float(row['ap_z'])
            if ap_z is not None:
                if handling_height is None or ap_z > handling_height:
                    handling_height = ap_z

        if handling_height is None:
            raise ValueError("Keine Z-Höhe gefunden.")

        #print(f"Found handling height: {handling_height}")

        # Schritt 2: Zweiter Punkt (ap_x, ap_y) mit maximaler Z-Höhe finden
        first_point = None
        start = None
        for index, row in enumerate(bahn_rows):
            ap_x = self.convert_to_float(row['ap_x'])
            ap_y = self.convert_to_float(row['ap_y'])
            ap_z = self.convert_to_float(row['ap_z'])
            if ap_x is not None and ap_y is not None and ap_z is not None:
                if abs(ap_z - handling_height) < 0.1:
                    first_point = (ap_x, ap_y)
                    start = index + 2
                    #print(f"Found first point: ({ap_x}, {ap_y}) at z={ap_z}")
                    break

        if not first_point:
            raise ValueError("Kein Punkt mit Handling-Höhe gefunden.")

        # Schritt 3: Dritter Punkt (ap_x, ap_y) mit gleicher Z-Höhe finden
        last_point = None
        end = None
        for index, row in enumerate(bahn_rows[start:]):
            ap_x = self.convert_to_float(row['ap_x'])
            ap_y = self.convert_to_float(row['ap_y'])
            ap_z = self.convert_to_float(row['ap_z'])
            if ap_x is not None and ap_y is not None and ap_z is not None:
                if abs(ap_z - handling_height) < 0.1:
                    if (ap_x, ap_y) != first_point:  # Ensure it's a different point
                        last_point = (ap_x, ap_y)
                        end = index + start
                        #print(f"Found last point: ({ap_x}, {ap_y}) at z={ap_z}")
                        break

        if not last_point:
            raise ValueError("Kein gültiger letzter Punkt gefunden.")

        # Schritt 3: Alle gültigen ps_x, ps_y Punkte zwischen Start und Ende sammeln
        points = []
        for row in bahn_rows[start:end]:
            ps_x = self.convert_to_float(row['ps_x'])
            ps_y = self.convert_to_float(row['ps_y'])
            if ps_x is not None and ps_y is not None:
                points.append((ps_x, ps_y))

        if not points:
            raise ValueError("Keine gültigen Punkte für die Kurvenbestimmung gefunden.")

        # Berechnung der Distanz zwischen dem ersten und letzten Punkt (Referenzgerade)
        x1, y1 = first_point  # Erster Punkt
        x2, y2 = last_point  # Letzter Punkt

        # Berechne die Distanz zwischen dem ersten und letzten Punkt
        p1p2_distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Funktion zur Bestimmung des kürzesten Abstands eines Punktes zur Linie
        def get_shortest_distance(xm, ym):
            # Geradengleichung: Ax + By + C = 0
            A = y2 - y1
            B = x1 - x2
            C = x2 * y1 - x1 * y2
            return abs(A * xm + B * ym + C) / math.sqrt(A ** 2 + B ** 2)

        # Bestimmung des besten Fits (linear oder circular)
        linear_points = []
        circular_left_points = []
        circular_right_points = []

        for (ps_x, ps_y) in points:
            shortest_distance = get_shortest_distance(ps_x, ps_y)
            if shortest_distance <= 0.1 * p1p2_distance:
                linear_points.append((ps_x, ps_y))
            else:
                # Bestimme, ob der Punkt links oder rechts der Linie liegt
                side_test = (x2 - x1) * (ps_y - y1) - (y2 - y1) * (ps_x - x1)
                if side_test > 0:
                    circular_left_points.append((ps_x, ps_y))
                else:
                    circular_right_points.append((ps_x, ps_y))

        # Entscheidung über die Kurve
        if len(linear_points) > len(circular_left_points) and len(linear_points) > len(circular_right_points):
            return "linear"
        elif len(circular_left_points) > len(circular_right_points):
            return "circularleft"
        else:
            return "circularright"