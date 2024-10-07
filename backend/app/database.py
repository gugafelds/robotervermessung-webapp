import asyncpg
from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def get_connection(self):
        if not self.pool:
            await self.connect()
        return await self.pool.acquire()

    async def release_connection(self, connection):
        await self.pool.release(connection)

db = Database()

async def get_db():
    conn = await db.get_connection()
    try:
        yield conn
    finally:
        await db.release_connection(conn)

def init_db(app: FastAPI):
    @app.on_event("startup")
    async def startup():
        await db.connect()

    @app.on_event("shutdown")
    async def shutdown():
        await db.disconnect()