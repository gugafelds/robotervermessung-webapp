from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from .csv_processor import CSVProcessor
from .db_operations import DatabaseOperations
from .db_config import DB_PARAMS


class BatchProcessor:
    """Class to handle batch processing of CSV files with optimized database operations"""

    def __init__(self):
        pass

    async def process_csv_batch(
            self,
            files_and_paths,
            robot_model,
            path_planning,
            source_data_act,
            source_data_cmd,
            upload_database,
            segmentation_method,
            num_segments,
            conn,
            reference_position=None  # Tuple mit (x, y, z)
    ):
        """Process multiple CSV files in a batch and upload them at once"""

        start_time = datetime.now()
        logger.info(f"Starting batch processing of {len(files_and_paths)} files at {start_time}")

        # Log segmentation parameters
        logger.info(f"Segmentation method: {segmentation_method}")
        if segmentation_method == "reference_position" and reference_position is not None:
            logger.info(
                f"Using reference position: x={reference_position[0]}, y={reference_position[1]}, z={reference_position[2]}")

        # Collect all data
        all_processed_data = []
        file_results = []

        for file_info in files_and_paths:
            try:
                csv_processor = CSVProcessor(file_info['path'])
                processed_data_list = csv_processor.process_csv(
                    robot_model,
                    path_planning,
                    source_data_act,
                    source_data_cmd,
                    file_info['filename'],
                    segmentation_method,
                    num_segments,
                    reference_position
                )


                if processed_data_list:
                    all_processed_data.extend(processed_data_list)
                    file_results.append({
                        "filename": file_info['filename'],
                        "segmentsFound": len(processed_data_list),
                        "success": True
                    })
                    logger.info(
                        f"Processed {file_info['filename']} successfully, found {len(processed_data_list)} trajectories")
                else:
                    file_results.append({
                        "filename": file_info['filename'],
                        "segmentsFound": 0,
                        "success": False,
                        "error": "No segments found"
                    })
                    logger.warning(f"No data processed from {file_info['filename']}")
            except Exception as e:
                file_results.append({
                    "filename": file_info['filename'],
                    "segmentsFound": 0,
                    "success": False,
                    "error": str(e)
                })
                logger.error(f"Error processing {file_info['filename']}: {str(e)}")

        # If not uploading to database, return early
        if not upload_database:
            return file_results

        # Group data by type for batch insertion
        if all_processed_data:
            db_ops = DatabaseOperations(DB_PARAMS)

            # If no connection was passed, create a new one
            close_conn = False
            if conn is None:
                conn = await db_ops.connect_to_db()
                close_conn = True

            try:
                # Collect data by type and extract all traj_ids
                traj_info_data = []
                pose_data = []
                position_cmd_data = []
                orientation_cmd_data = []
                vel_act_data = []
                vel_cmd_data = []
                accel_act_data = []
                accel_cmd_data = []
                rapid_setpoints_data = []
                joint_data = []
                transf_data = []

                all_traj_ids = []

                # Group all data by type and collect traj_ids
                for data_set in all_processed_data:
                    traj_id = data_set['traj_info_data'][0]
                    all_traj_ids.append(traj_id)

                    traj_info_data.append(data_set['traj_info_data'])
                    pose_data.extend(data_set.get('POSE_MAPPING', []))
                    position_cmd_data.extend(data_set.get('POSITION_CMD_MAPPING', []))
                    orientation_cmd_data.extend(data_set.get('ORIENTATION_CMD_MAPPING', []))
                    vel_act_data.extend(data_set.get('VEL_ACT_MAPPING', []))
                    vel_cmd_data.extend(data_set.get('VEL_CMD_MAPPING', []))
                    accel_act_data.extend(data_set.get('ACCEL_ACT_MAPPING', []))
                    accel_cmd_data.extend(data_set.get('ACCEL_CMD_MAPPING', []))
                    rapid_setpoints_data.extend(data_set.get('RAPID_SETPOINTS_MAPPING', []))
                    joint_data.extend(data_set.get('JOINT_MAPPING', []))
                    transf_data.extend(data_set.get('TRANSFORM_MAPPING', []))

                # First check which traj_ids already exist in each table
                # This avoids checking each record individually
                tables = [
                    'traj_info',
                    'traj_pose_act_raw',
                    'traj_position_cmd',
                    'traj_orientation_cmd',
                    'traj_vel_act',
                    'traj_vel_cmd',
                    'traj_accel_act',
                    'traj_accel_cmd',
                    'traj_setpoints',
                    'traj_joint_states',
                    'traj_pose_act',
                ]

                existing_traj_ids = {}
                for table in tables:
                    # Query for all traj_ids in this table in one go
                    query = f"""
                    SELECT DISTINCT traj_id FROM motion.{table} 
                    WHERE traj_id = ANY($1::text[])
                    """
                    rows = await conn.fetch(query, all_traj_ids)
                    existing_traj_ids[table] = {row['traj_id'] for row in rows}

                    existing_count = len(existing_traj_ids[table])
                    if existing_count > 0:
                        logger.info(f"Found {existing_count} existing traj_ids in {table}")

                # Filter out records that already exist in each table
                filtered_traj_info = [
                    record for record in traj_info_data
                    if record[0] not in existing_traj_ids['traj_info']
                ]

                filtered_pose = [
                    record for record in pose_data
                    if record[0] not in existing_traj_ids['traj_pose_act_raw']
                ]

                filtered_transf = [
                    record for record in transf_data
                    if record[0] not in existing_traj_ids['traj_pose_act']
                ]

                filtered_position_cmd = [
                    record for record in position_cmd_data
                    if record[0] not in existing_traj_ids['traj_position_cmd']
                ]

                filtered_orientation_cmd = [
                    record for record in orientation_cmd_data
                    if record[0] not in existing_traj_ids['traj_orientation_cmd']
                ]

                filtered_vel_act = [
                    record for record in vel_act_data
                    if record[0] not in existing_traj_ids['traj_vel_act']
                ]

                filtered_vel_cmd = [
                    record for record in vel_cmd_data
                    if record[0] not in existing_traj_ids['traj_vel_cmd']
                ]

                filtered_accel_act = [
                    record for record in accel_act_data
                    if record[0] not in existing_traj_ids['traj_accel_act']
                ]

                filtered_accel_cmd = [
                    record for record in accel_cmd_data
                    if record[0] not in existing_traj_ids['traj_accel_cmd']
                ]

                filtered_setpoints = [
                    record for record in rapid_setpoints_data
                    if record[0] not in existing_traj_ids['traj_setpoints']
                ]

                filtered_joint = [
                    record for record in joint_data
                    if record[0] not in existing_traj_ids['traj_joint_states']
                ]


                # Now insert all filtered data in a single transaction
                try:
                    async with conn.transaction():
                        # First insert traj_info (metadata)
                        if filtered_traj_info:
                            columns = [
                                'traj_id', 'robot_model', 'path_planning', 'recording_date', 'start_time',
                                'end_time', 'source_data_act', 'source_data_cmd', 'record_filename',
                                'number_setpoints', 'freq_pose_act', 'freq_position_cmd',
                                'freq_orientation_cmd', 'freq_vel_act', 'freq_vel_cmd',
                                'freq_accel_act', 'freq_joint_states',
                                'number_pose_act', 'number_vel_act', 'number_accel_act', 'number_position_cmd', 'number_orientation_cmd',
                                'number_vel_cmd', 'number_joint_states', 'weight',
                                'transformation_matrix',
                                'number_accel_cmd', 'freq_accel_cmd', 'setted_velocity', 'stop_point', 'wait_time'
                            ]

                            # Ensure all records have proper length
                            padded_records = []
                            for record in filtered_traj_info:
                                if len(record) < 46:
                                    padded_record = list(record)
                                    padded_record.extend([None] * (46 - len(padded_record)))
                                    padded_records.append(tuple(padded_record))
                                else:
                                    padded_records.append(record)

                            await db_ops.copy_data_to_table(conn, 'traj_info', padded_records, columns)
                            logger.info(f"Inserted {len(padded_records)} new traj_info records in batch")
                        else:
                            logger.info("No new traj_info records to insert")

                        # Define data mappings for other tables
                        data_mappings = [
                            (filtered_pose, 'traj_pose_act_raw',
                             ['traj_id', 'seg_id', 'timestamp', 'x_act_raw', 'y_act_raw', 'z_act_raw', 'qx_act_raw', 'qy_act_raw',
                              'qz_act_raw', 'qw_act_raw']),
                            (filtered_transf, 'traj_pose_act',
                             ['traj_id', 'seg_id', 'timestamp', 'x_act', 'y_act', 'z_act', 'qx_act', 'qy_act',
                              'qz_act', 'qw_act']),
                            (filtered_position_cmd, 'traj_position_cmd',
                             ['traj_id', 'seg_id', 'timestamp', 'x_cmd', 'y_cmd', 'z_cmd']),
                            (filtered_orientation_cmd, 'traj_orientation_cmd',
                             ['traj_id', 'seg_id', 'timestamp', 'qx_cmd', 'qy_cmd', 'qz_cmd', 'qw_cmd']),
                            (filtered_vel_act, 'traj_vel_act',
                             ['traj_id', 'seg_id', 'timestamp', 'tcp_vel_act']),
                            (filtered_vel_cmd, 'traj_vel_cmd',
                             ['traj_id', 'seg_id', 'timestamp', 'tcp_vel_cmd']),
                            (filtered_accel_act, 'traj_accel_act',
                             ['traj_id', 'seg_id', 'timestamp', 'tcp_accel_act']),
                            (filtered_accel_cmd, 'traj_accel_cmd',
                             ['traj_id', 'seg_id', 'timestamp', 'tcp_accel_cmd']),
                            (filtered_setpoints, 'traj_setpoints',
                             ['traj_id', 'seg_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached', 'qx_reached',
                              'qy_reached', 'qz_reached', 'qw_reached']),
                            (filtered_joint, 'traj_joint_states',
                             ['traj_id', 'seg_id', 'timestamp', 'joint_1', 'joint_2', 'joint_3', 'joint_4',
                              'joint_5', 'joint_6']),
                        ]

                        # Insert each type of data
                        for data_array, table_name, columns in data_mappings:
                            if data_array:
                                await db_ops.copy_data_to_table(conn, table_name, data_array, columns)
                                logger.info(f"Inserted {len(data_array)} new records into {table_name}")
                            else:
                                logger.info(f"No new records to insert into {table_name}")

                    logger.info(f"Successfully inserted all batch data")
                except Exception as e:
                    logger.error(f"Error during batch database insertion: {str(e)}")
                    # Mark files as unsuccessful
                    for result in file_results:
                        if result['success']:
                            result['success'] = False
                            result['error'] = f"Database error: {str(e)}"
            except Exception as e:
                logger.error(f"Error in batch processing: {str(e)}")
                for result in file_results:
                    if result['success']:
                        result['success'] = False
                        result['error'] = f"Processing error: {str(e)}"
            finally:
                if close_conn and conn:
                    await conn.close()

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Batch processing completed in {processing_time:.2f} seconds")

        return file_results

    # Die übrigen Methoden bleiben unverändert
    async def batch_insert_traj_info(self, db_ops, conn, data_list):
        """Insert multiple traj_info records at once"""
        # Methode bleibt unverändert
        try:
            # Filter out records that already exist
            new_records = []
            for record in data_list:
                traj_id = record[0]
                exists = await db_ops.check_traj_id_exists(conn, 'traj_info', traj_id)
                if not exists:
                    new_records.append(record)

            if not new_records:
                logger.info("No new traj_info records to insert")
                return

            columns = [
                'traj_id', 'robot_model', 'path_planning', 'recording_date', 'start_time',
                'end_time', 'source_data_act', 'source_data_cmd', 'record_filename',
                'number_setpoints', 'freq_pose_act', 'freq_position_cmd',
                'freq_orientation_cmd', 'freq_vel_act', 'freq_vel_cmd',
                'freq_accel_act', 'freq_joint_states',
                'number_pose_act', 'number_vel_act', 'number_accel_act', 'number_position_cmd', 'number_orientation_cmd',
                'number_vel_cmd', 'number_joint_states', 'weight',
                'transformation_matrix',
                'number_accel_cmd', 'freq_accel_cmd', 'setted_velocity', 'stop_point', 'wait_time'
            ]

            # Ensure all records have proper length
            padded_records = []
            for record in new_records:
                if len(record) < 46:
                    padded_record = list(record)
                    padded_record.extend([None] * (46 - len(padded_record)))
                    padded_records.append(tuple(padded_record))
                else:
                    padded_records.append(record)

            await db_ops.copy_data_to_table(conn, 'traj_info', padded_records, columns)
            logger.info(f"Inserted {len(padded_records)} traj_info records in batch")
        except Exception as e:
            logger.error(f"Error in batch_insert_traj_info: {str(e)}")
            raise

    # Helper methods for each data type insertion
    async def batch_insert_data(self, db_ops, conn, table_name, data, columns=None):
        """Generic batch insert for any table with uniqueness check on traj_id"""
        # Methode bleibt unverändert
        if not data:
            logger.info(f"No {table_name} data to insert")
            return

        try:
            # Group data by traj_id
            traj_id_groups = {}
            for row in data:
                traj_id = row[0]  # Assuming traj_id is always the first column
                if traj_id not in traj_id_groups:
                    traj_id_groups[traj_id] = []
                traj_id_groups[traj_id].append(row)

            # Check which traj_ids already exist
            for traj_id, rows in list(traj_id_groups.items()):
                exists = await db_ops.check_traj_id_exists(conn, table_name, traj_id)
                if exists:
                    logger.info(f"{table_name} data for traj_id {traj_id} already exists. Skipping.")
                    del traj_id_groups[traj_id]

            # Flatten the remaining groups
            filtered_data = []
            for rows in traj_id_groups.values():
                filtered_data.extend(rows)

            if not filtered_data:
                logger.info(f"No new {table_name} data to insert after filtering")
                return

            await db_ops.copy_data_to_table(conn, table_name, filtered_data, columns)
            logger.info(f"Inserted {len(filtered_data)} {table_name} records in batch")
        except Exception as e:
            logger.error(f"Error in batch_insert_data for {table_name}: {str(e)}")
            raise

    # Specific batch insert methods for each data type - bleiben alle unverändert
    async def batch_insert_pose_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'x_act_raw', 'y_act_raw', 'z_act_raw',
                   'qx_act_raw', 'qy_act_raw', 'qz_act_raw', 'qw_act_raw']
        await self.batch_insert_data(db_ops, conn, 'traj_pose_act_raw', data, columns)

    async def batch_insert_position_cmd_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'x_cmd', 'y_cmd', 'z_cmd']
        await self.batch_insert_data(db_ops, conn, 'traj_position_cmd', data, columns)

    async def batch_insert_orientation_cmd_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'qx_cmd', 'qy_cmd', 'qz_cmd', 'qw_cmd']
        await self.batch_insert_data(db_ops, conn, 'traj_orientation_cmd', data, columns)

    async def batch_insert_vel_act_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'tcp_speed_act']
        await self.batch_insert_data(db_ops, conn, 'traj_vel_act', data, columns)

    async def batch_insert_vel_cmd_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'tcp_speed_cmd']
        await self.batch_insert_data(db_ops, conn, 'traj_vel_cmd', data, columns)

    async def batch_insert_accel_act_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'tcp_accel_act']
        await self.batch_insert_data(db_ops, conn, 'traj_accel_act', data, columns)

    async def batch_insert_accel_cmd_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'tcp_accel_cmd']
        await self.batch_insert_data(db_ops, conn, 'traj_accel_cmd', data, columns)

    async def batch_insert_rapid_setpoints_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached',
                   'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached']
        await self.batch_insert_data(db_ops, conn, 'traj_setpoints', data, columns)

    async def batch_insert_joint_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'joint_1', 'joint_2', 'joint_3',
                   'joint_4', 'joint_5', 'joint_6']
        await self.batch_insert_data(db_ops, conn, 'traj_joint_states', data, columns)

    async def batch_insert_transf_data(self, db_ops, conn, data):
        columns = ['traj_id', 'seg_id', 'timestamp', 'x_act', 'y_act', 'z_act',
                   'qx_act', 'qy_act', 'qz_act', 'qw_act']
        await self.batch_insert_data(db_ops, conn, 'traj_pose_act', data, columns)