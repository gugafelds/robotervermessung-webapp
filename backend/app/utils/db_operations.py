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

    async def insert_bahn_info(self, conn, data):
        if await self.check_bahn_id_exists(conn, 'bahn_info', data[0]):
            logger.info(f"bahn_info for bahn_id {data[0]} already exists. Skipping insertion.")
            return

        query = """
            INSERT INTO bewegungsdaten.bahn_info 
            (bahn_id, robot_model, bahnplanung, recording_date, start_time, end_time, 
             source_data_ist, source_data_soll, record_filename, 
             np_ereignisse, frequency_pose_ist, frequency_position_soll, 
             frequency_orientation_soll, frequency_twist_ist, frequency_twist_soll, 
             frequency_accel_ist, frequency_joint_states, calibration_run, np_pose_ist, np_twist_ist, np_accel_ist, np_pos_soll, np_orient_soll, np_twist_soll, np_jointstates)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
        """
        try:
            await conn.execute(query, *data)
            logger.info(f"Data inserted successfully into bahn_info")
        except Exception as error:
            logger.error(f"Error inserting data into bahn_info: {error}")
            raise

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
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_accel_x', 'tcp_accel_y', 
                            'tcp_accel_z', 'tcp_accel_ist', 'tcp_angular_accel_x', 'tcp_angular_accel_y',
                            'tcp_angular_accel_z', 'tcp_angular_accel_ist', 'source_data_ist'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                            'double precision', 'double precision', 'double precision', 'double precision',
                            'double precision', 'double precision', 'varchar']
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
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_x', 'tcp_speed_y',
                            'tcp_speed_z', 'tcp_speed_ist', 'tcp_angular_x', 'tcp_angular_y',
                            'tcp_angular_z', 'tcp_angular_ist', 'source_data_ist'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                            'double precision', 'double precision', 'double precision', 'double precision',
                            'double precision', 'double precision', 'varchar']
                },
                'bahn_twist_soll': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'tcp_speed_soll', 'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'varchar']
                },
                'bahn_events': {
                    'columns': ['bahn_id', 'segment_id', 'timestamp', 'x_reached', 'y_reached', 'z_reached',
                            'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached', 'source_data_soll'],
                    'types': ['varchar', 'varchar', 'varchar', 'double precision', 'double precision',
                            'double precision', 'double precision', 'double precision', 'double precision',
                            'double precision', 'varchar']
                }
            }

            if table_name in table_schemas:
                schema = table_schemas[table_name]
                
                # Convert the data with proper types
                converted_data = []
                for row in data:
                    converted_row = []
                    for i, value in enumerate(row):
                        if schema['types'][i] == 'varchar':
                            converted_row.append(str(value) if value is not None else None)
                        elif schema['types'][i] == 'double precision':
                            converted_row.append(float(value) if value is not None else 0.0)
                    converted_data.append(converted_row)

                # Create the INSERT query with proper column names and type casting
                columns = ', '.join(schema['columns'])
                placeholders = ', '.join(f'${i+1}::{typ}' for i, typ in enumerate(schema['types']))
                query = f"""
                    INSERT INTO bewegungsdaten.{table_name} 
                    ({columns})
                    VALUES ({placeholders})
                """
                
                await conn.executemany(query, converted_data)
            else:
                # Fallback for any unhandled tables
                columns = ', '.join(f'${i+1}' for i in range(len(data[0])))
                query = f"INSERT INTO bewegungsdaten.{table_name} VALUES ({columns})"
                await conn.executemany(query, data)
            
            logger.info(f"Data inserted successfully into {table_name}")
            
        except Exception as error:
            logger.error(f"Error inserting data into {table_name}: {error}")
            raise

    # You can keep the specific insert methods if you want, but they'll all use insert_data now
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