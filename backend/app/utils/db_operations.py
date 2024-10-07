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

        bahn_id = data[0][0]
        if await self.check_bahn_id_exists(conn, table_name, bahn_id):
            logger.info(f"{table_name} data for bahn_id {bahn_id} already exists. Skipping insertion.")
            return

        columns = ', '.join(f'${i+1}' for i in range(len(data[0])))
        query = f"INSERT INTO bewegungsdaten.{table_name} VALUES ({columns})"
        try:
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