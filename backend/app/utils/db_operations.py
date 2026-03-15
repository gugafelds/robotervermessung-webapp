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

    async def check_traj_id_exists(self, conn, table_name, traj_id):
        query = f"SELECT COUNT(*) FROM motion.{table_name} WHERE traj_id = $1"
        return await conn.fetchval(query, traj_id) > 0

    async def copy_data_to_table(self, conn, table_name, data, columns=None):
        if not data:
            logger.info(f"No data to copy into {table_name}")
            return

        try:
            if table_name == 'traj_setpoints':
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
                schema_name='motion',
                columns=columns
            )

            logger.info(f"Data copied successfully into {table_name}")
        except Exception as error:
            logger.error(f"Error copying data into {table_name}: {error}")
            logger.error(f"Data that caused error: {data}")
            raise