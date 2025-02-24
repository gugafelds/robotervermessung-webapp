import asyncpg
import logging

logger = logging.getLogger(__name__)

class DatabaseOperations:
    def __init__(self, db_params):
        self.db_params = db_params

    async def connect_to_db(self):
        try:
            return await asyncpg.connect(**self.db_params)
        except Exception as error:
            logger.error(f"Error while connecting to PostgreSQL: {error}")
            raise

    async def check_bahn_id_exists(self, conn, table_name, bahn_id):
        query = f"SELECT COUNT(*) FROM bewegungsdaten.{table_name} WHERE bahn_id = $1"
        return await conn.fetchval(query, bahn_id) > 0

    async def copy_data_to_table(self, conn, table_name, data, columns=None):
        if not data:
            logger.info(f"No data to copy into {table_name}")
            return

        try:
            if table_name == 'bahn_events':
                converted_records = []
                for record in data:
                    converted_record = list(record)  # Konvertiere Tuple zu Liste
                    # Konvertiere Positionen zu float
                    for i in range(3, 10):  # Indizes 3-9 sind die float-Werte
                        converted_record[i] = float(converted_record[i])
                    converted_records.append(tuple(converted_record))
            else:
                converted_records = data

            await conn.copy_records_to_table(
                table_name,
                records=converted_records,
                schema_name='bewegungsdaten',
                columns=columns
            )

            logger.info(f"Data copied successfully into {table_name}")
        except Exception as error:
            logger.error(f"Error copying data into {table_name}: {error}")
            logger.error(f"Data that caused error: {data}")
            raise

    async def insert_bahn_info(self, conn, data):
        if await self.check_bahn_id_exists(conn, 'bahn_info', data[0]):
            logger.info(f"bahn_info for bahn_id {data[0]} already exists. Skipping insertion.")
            return

        columns = [
            'bahn_id', 'robot_model', 'bahnplanung', 'recording_date', 'start_time',
            'end_time', 'source_data_ist', 'source_data_soll', 'record_filename',
            'np_ereignisse', 'frequency_pose_ist', 'frequency_position_soll',
            'frequency_orientation_soll', 'frequency_twist_ist', 'frequency_twist_soll',
            'frequency_accel_ist', 'frequency_joint_states', 'calibration_run',
            'np_pose_ist', 'np_twist_ist', 'np_accel_ist', 'np_pos_soll', 'np_orient_soll',
            'np_twist_soll', 'np_jointstates', 'weight', 'x_start_pos', 'y_start_pos',
            'z_start_pos', 'x_end_pos', 'y_end_pos', 'z_end_pos', 'handling_height',
            'qx_start', 'qy_start', 'qz_start', 'qw_start', 'qx_end', 'qy_end',
            'qz_end', 'qw_end', 'velocity_picking', 'velocity_handling', 'frequency_imu',
            'pick_and_place', 'np_imu'
        ]

        # Erweitere data auf die benötigte Länge mit None-Werten wenn nötig
        data_length = len(data)
        if data_length < 46:
            data = list(data)
            data.extend([None] * (46 - data_length))

        await self.copy_data_to_table(conn, 'bahn_info', [data], columns)

    async def insert_data(self, conn, table_name, data):
        if not data:
            logger.info(f"No {table_name} data to insert.")
            return

        try:
            bahn_id = data[0][0]
            if await self.check_bahn_id_exists(conn, table_name, bahn_id):
                logger.info(f"{table_name} data for bahn_id {bahn_id} already exists. Skipping insertion.")
                return

            table_schemas = {
                'bahn_joint_states': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'joint_1', 'joint_2', 'joint_3',
                                'joint_4', 'joint_5', 'joint_6', 'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                              'double precision', 'double precision', 'double precision', 'double precision', 'varchar']
                },
                'bahn_accel_ist': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_ist', 'tcp_angular_accel_ist',
                                'source_data_ist'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision', 'varchar']
                },
                'bahn_orientation_soll': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'qx_soll', 'qy_soll', 'qz_soll',
                                'qw_soll', 'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                              'double precision', 'double precision', 'varchar']
                },
                'bahn_pose_ist': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'x_ist', 'y_ist', 'z_ist',
                                'qx_ist', 'qy_ist', 'qz_ist', 'qw_ist', 'source_data_ist'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                              'double precision', 'double precision', 'double precision', 'double precision',
                              'double precision', 'varchar']
                },
                'bahn_position_soll': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'x_soll', 'y_soll', 'z_soll',
                                'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                              'double precision', 'varchar']
                },
                'bahn_twist_ist': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_ist', 'tcp_angular_ist',
                                'source_data_ist'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision',
                              'double precision', 'varchar']
                },
                'bahn_twist_soll': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_soll', 'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'varchar']
                },
                'bahn_events': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached',
                                'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached', 'source_data_soll',
                                'movement_type'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                              'double precision', 'double precision', 'double precision', 'double precision',
                              'double precision', 'varchar', 'varchar'],
                    'bahn_imu': {
                        'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_pi', 'tcp_angular_vel_pi',
                                    'source_data_ist'],
                        'types': ['varchar', 'varchar', 'varchar', 'double precision',
                                  'double precision', 'varchar']
                    },
                }
            }

            if table_name in table_schemas:
                schema = table_schemas[table_name]
                converted_data = []

                for row in data:
                    converted_row = []
                    for value, type_name in zip(row, schema['types']):
                        if value is None:
                            converted_row.append(None)
                        elif type_name == 'str':
                            converted_row.append(str(value))
                        elif type_name == 'float':
                            converted_row.append(float(value))
                        elif type_name == 'int':
                            converted_row.append(int(value))
                        else:
                            converted_row.append(value)
                    converted_data.append(tuple(converted_row))

                await self.copy_data_to_table(conn, table_name, converted_data, schema['columns'])
            else:
                # Fallback für nicht definierte Tabellen
                await self.copy_data_to_table(conn, table_name, data)

        except Exception as error:
            logger.error(f"Error inserting data into {table_name}: {error}")
            raise

    # Spezifische Insert-Methoden als Wrapper
    async def insert_pose_data(self, conn, data):
        await self.insert_data(conn, 'bahn_pose_ist', data)

    async def insert_position_soll_data(self, conn, data):
        await self.insert_data(conn, 'bahn_position_soll', data)

    async def insert_twist_soll_data(self, conn, data):
        await self.insert_data(conn, 'bahn_twist_soll', data)

    async def insert_orientation_soll_data(self, conn, data):
        await self.insert_data(conn, 'bahn_orientation_soll', data)

    async def insert_accel_data(self, conn, data):
        await self.insert_data(conn, 'bahn_accel_ist', data)

    async def insert_twist_ist_data(self, conn, data):
        await self.insert_data(conn, 'bahn_twist_ist', data)

    async def insert_rapid_events_data(self, conn, data):
        await self.insert_data(conn, 'bahn_events', data)

    async def insert_joint_data(self, conn, data):
        await self.insert_data(conn, 'bahn_joint_states', data)

    async def insert_imu_data(self, conn, data):
        await self.insert_data(conn, 'bahn_imu', data)