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
            bahnplanung,
            source_data_ist,
            source_data_soll,
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
                    bahnplanung,
                    source_data_ist,
                    source_data_soll,
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
                # Collect data by type and extract all bahn_ids
                bahn_info_data = []
                pose_data = []
                position_soll_data = []
                orientation_soll_data = []
                twist_ist_data = []
                twist_soll_data = []
                accel_ist_data = []
                accel_soll_data = []
                rapid_events_data = []
                joint_data = []
                transf_data = []

                all_bahn_ids = []

                # Group all data by type and collect bahn_ids
                for data_set in all_processed_data:
                    bahn_id = data_set['bahn_info_data'][0]
                    all_bahn_ids.append(bahn_id)

                    bahn_info_data.append(data_set['bahn_info_data'])
                    pose_data.extend(data_set.get('POSE_MAPPING', []))
                    position_soll_data.extend(data_set.get('POSITION_SOLL_MAPPING', []))
                    orientation_soll_data.extend(data_set.get('ORIENTATION_SOLL_MAPPING', []))
                    twist_ist_data.extend(data_set.get('TWIST_IST_MAPPING', []))
                    twist_soll_data.extend(data_set.get('TWIST_SOLL_MAPPING', []))
                    accel_ist_data.extend(data_set.get('ACCEL_IST_MAPPING', []))
                    accel_soll_data.extend(data_set.get('ACCEL_SOLL_MAPPING', []))
                    rapid_events_data.extend(data_set.get('RAPID_EVENTS_MAPPING', []))
                    joint_data.extend(data_set.get('JOINT_MAPPING', []))
                    transf_data.extend(data_set.get('TRANSFORM_MAPPING', []))

                # First check which bahn_ids already exist in each table
                # This avoids checking each record individually
                tables = [
                    'bahn_info',
                    'bahn_pose_ist',
                    'bahn_position_soll',
                    'bahn_orientation_soll',
                    'bahn_twist_ist',
                    'bahn_twist_soll',
                    'bahn_accel_ist',
                    'bahn_accel_soll',
                    'bahn_events',
                    'bahn_joint_states',
                    'bahn_pose_trans',
                ]

                existing_bahn_ids = {}
                for table in tables:
                    # Query for all bahn_ids in this table in one go
                    query = f"""
                    SELECT DISTINCT bahn_id FROM bewegungsdaten.{table} 
                    WHERE bahn_id = ANY($1::text[])
                    """
                    rows = await conn.fetch(query, all_bahn_ids)
                    existing_bahn_ids[table] = {row['bahn_id'] for row in rows}

                    existing_count = len(existing_bahn_ids[table])
                    if existing_count > 0:
                        logger.info(f"Found {existing_count} existing bahn_ids in {table}")

                # Filter out records that already exist in each table
                filtered_bahn_info = [
                    record for record in bahn_info_data
                    if record[0] not in existing_bahn_ids['bahn_info']
                ]

                filtered_pose = [
                    record for record in pose_data
                    if record[0] not in existing_bahn_ids['bahn_pose_ist']
                ]

                filtered_transf = [
                    record for record in transf_data
                    if record[0] not in existing_bahn_ids['bahn_pose_trans']
                ]

                filtered_position_soll = [
                    record for record in position_soll_data
                    if record[0] not in existing_bahn_ids['bahn_position_soll']
                ]

                filtered_orientation_soll = [
                    record for record in orientation_soll_data
                    if record[0] not in existing_bahn_ids['bahn_orientation_soll']
                ]

                filtered_twist_ist = [
                    record for record in twist_ist_data
                    if record[0] not in existing_bahn_ids['bahn_twist_ist']
                ]

                filtered_twist_soll = [
                    record for record in twist_soll_data
                    if record[0] not in existing_bahn_ids['bahn_twist_soll']
                ]

                filtered_accel_ist = [
                    record for record in accel_ist_data
                    if record[0] not in existing_bahn_ids['bahn_accel_ist']
                ]

                filtered_accel_soll = [
                    record for record in accel_soll_data
                    if record[0] not in existing_bahn_ids['bahn_accel_soll']
                ]

                filtered_events = [
                    record for record in rapid_events_data
                    if record[0] not in existing_bahn_ids['bahn_events']
                ]

                filtered_joint = [
                    record for record in joint_data
                    if record[0] not in existing_bahn_ids['bahn_joint_states']
                ]


                # Now insert all filtered data in a single transaction
                try:
                    async with conn.transaction():
                        # First insert bahn_info (metadata)
                        if filtered_bahn_info:
                            columns = [
                                'bahn_id', 'robot_model', 'bahnplanung', 'recording_date', 'start_time',
                                'end_time', 'source_data_ist', 'source_data_soll', 'record_filename',
                                'np_ereignisse', 'frequency_pose_ist', 'frequency_position_soll',
                                'frequency_orientation_soll', 'frequency_twist_ist', 'frequency_twist_soll',
                                'frequency_accel_ist', 'frequency_joint_states',
                                'np_pose_ist', 'np_twist_ist', 'np_accel_ist', 'np_pos_soll', 'np_orient_soll',
                                'np_twist_soll', 'np_jointstates', 'weight',
                                'pick_and_place', 'transformation_matrix',
                                'np_accel_soll', 'frequency_accel_soll', 'setted_velocity', 'stop_point', 'wait_time'
                            ]

                            # Ensure all records have proper length
                            padded_records = []
                            for record in filtered_bahn_info:
                                if len(record) < 46:
                                    padded_record = list(record)
                                    padded_record.extend([None] * (46 - len(padded_record)))
                                    padded_records.append(tuple(padded_record))
                                else:
                                    padded_records.append(record)

                            await db_ops.copy_data_to_table(conn, 'bahn_info', padded_records, columns)
                            logger.info(f"Inserted {len(padded_records)} new bahn_info records in batch")
                        else:
                            logger.info("No new bahn_info records to insert")

                        # Define data mappings for other tables
                        data_mappings = [
                            (filtered_pose, 'bahn_pose_ist',
                             ['bahn_id', 'segment_id', 'timestamp', 'x_ist', 'y_ist', 'z_ist', 'qx_ist', 'qy_ist',
                              'qz_ist', 'qw_ist', 'source_data_ist']),
                            (filtered_transf, 'bahn_pose_trans',
                             ['bahn_id', 'segment_id', 'timestamp', 'x_trans', 'y_trans', 'z_trans', 'qx_trans', 'qy_trans',
                              'qz_trans', 'qw_trans']),
                            (filtered_position_soll, 'bahn_position_soll',
                             ['bahn_id', 'segment_id', 'timestamp', 'x_soll', 'y_soll', 'z_soll', 'source_data_soll']),
                            (filtered_orientation_soll, 'bahn_orientation_soll',
                             ['bahn_id', 'segment_id', 'timestamp', 'qx_soll', 'qy_soll', 'qz_soll', 'qw_soll',
                              'source_data_soll']),
                            (filtered_twist_ist, 'bahn_twist_ist',
                             ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_ist']),
                            (filtered_twist_soll, 'bahn_twist_soll',
                             ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_soll', 'source_data_soll']),
                            (filtered_accel_ist, 'bahn_accel_ist',
                             ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_ist']),
                            (filtered_accel_soll, 'bahn_accel_soll',
                             ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_soll']),
                            (filtered_events, 'bahn_events',
                             ['bahn_id', 'segment_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached', 'qx_reached',
                              'qy_reached', 'qz_reached', 'qw_reached', 'source_data_soll', 'movement_type']),
                            (filtered_joint, 'bahn_joint_states',
                             ['bahn_id', 'segment_id', 'timestamp', 'joint_1', 'joint_2', 'joint_3', 'joint_4',
                              'joint_5', 'joint_6', 'source_data_soll']),
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
    async def batch_insert_bahn_info(self, db_ops, conn, data_list):
        """Insert multiple bahn_info records at once"""
        # Methode bleibt unverändert
        try:
            # Filter out records that already exist
            new_records = []
            for record in data_list:
                bahn_id = record[0]
                exists = await db_ops.check_bahn_id_exists(conn, 'bahn_info', bahn_id)
                if not exists:
                    new_records.append(record)

            if not new_records:
                logger.info("No new bahn_info records to insert")
                return

            columns = [
                'bahn_id', 'robot_model', 'bahnplanung', 'recording_date', 'start_time',
                'end_time', 'source_data_ist', 'source_data_soll', 'record_filename',
                'np_ereignisse', 'frequency_pose_ist', 'frequency_position_soll',
                'frequency_orientation_soll', 'frequency_twist_ist', 'frequency_twist_soll',
                'frequency_accel_ist', 'frequency_joint_states',
                'np_pose_ist', 'np_twist_ist', 'np_accel_ist', 'np_pos_soll', 'np_orient_soll',
                'np_twist_soll', 'np_jointstates', 'weight',
                'pick_and_place', 'transformation_matrix',
                'np_accel_soll', 'frequency_accel_soll', 'setted_velocity', 'stop_point', 'wait_time'
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

            await db_ops.copy_data_to_table(conn, 'bahn_info', padded_records, columns)
            logger.info(f"Inserted {len(padded_records)} bahn_info records in batch")
        except Exception as e:
            logger.error(f"Error in batch_insert_bahn_info: {str(e)}")
            raise

    # Helper methods for each data type insertion
    async def batch_insert_data(self, db_ops, conn, table_name, data, columns=None):
        """Generic batch insert for any table with uniqueness check on bahn_id"""
        # Methode bleibt unverändert
        if not data:
            logger.info(f"No {table_name} data to insert")
            return

        try:
            # Group data by bahn_id
            bahn_id_groups = {}
            for row in data:
                bahn_id = row[0]  # Assuming bahn_id is always the first column
                if bahn_id not in bahn_id_groups:
                    bahn_id_groups[bahn_id] = []
                bahn_id_groups[bahn_id].append(row)

            # Check which bahn_ids already exist
            for bahn_id, rows in list(bahn_id_groups.items()):
                exists = await db_ops.check_bahn_id_exists(conn, table_name, bahn_id)
                if exists:
                    logger.info(f"{table_name} data for bahn_id {bahn_id} already exists. Skipping.")
                    del bahn_id_groups[bahn_id]

            # Flatten the remaining groups
            filtered_data = []
            for rows in bahn_id_groups.values():
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
        columns = ['bahn_id', 'segment_id', 'timestamp', 'x_ist', 'y_ist', 'z_ist',
                   'qx_ist', 'qy_ist', 'qz_ist', 'qw_ist', 'source_data_ist']
        await self.batch_insert_data(db_ops, conn, 'bahn_pose_ist', data, columns)

    async def batch_insert_position_soll_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'x_soll', 'y_soll', 'z_soll', 'source_data_soll']
        await self.batch_insert_data(db_ops, conn, 'bahn_position_soll', data, columns)

    async def batch_insert_orientation_soll_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'qx_soll', 'qy_soll', 'qz_soll', 'qw_soll', 'source_data_soll']
        await self.batch_insert_data(db_ops, conn, 'bahn_orientation_soll', data, columns)

    async def batch_insert_twist_ist_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_ist']
        await self.batch_insert_data(db_ops, conn, 'bahn_twist_ist', data, columns)

    async def batch_insert_twist_soll_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_soll', 'source_data_soll']
        await self.batch_insert_data(db_ops, conn, 'bahn_twist_soll', data, columns)

    async def batch_insert_accel_ist_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_ist']
        await self.batch_insert_data(db_ops, conn, 'bahn_accel_ist', data, columns)

    async def batch_insert_accel_soll_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_soll']
        await self.batch_insert_data(db_ops, conn, 'bahn_accel_soll', data, columns)

    async def batch_insert_rapid_events_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached',
                   'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached', 'source_data_soll', 'movement_type']
        await self.batch_insert_data(db_ops, conn, 'bahn_events', data, columns)

    async def batch_insert_joint_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'joint_1', 'joint_2', 'joint_3',
                   'joint_4', 'joint_5', 'joint_6', 'source_data_soll']
        await self.batch_insert_data(db_ops, conn, 'bahn_joint_states', data, columns)

    async def batch_insert_transf_data(self, db_ops, conn, data):
        columns = ['bahn_id', 'segment_id', 'timestamp', 'x_trans', 'y_trans', 'z_trans',
                   'qx_trans', 'qy_trans', 'qz_trans', 'qw_trans', 'calibration_id']
        await self.batch_insert_data(db_ops, conn, 'bahn_pose_trans', data, columns)