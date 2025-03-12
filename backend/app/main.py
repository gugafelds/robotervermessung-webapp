from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import bahn_route_handler, auswertung_route_handler, rosbag_route_handler, transformation_route_handler
from .database import init_db
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import aioredis
import os
from dotenv import load_dotenv
import logging
#from .api.endpoints.transformation_route_handler import MatlabEngine

# Global config
#USE_MATLAB = False  # Hier direkt definiert

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bahn Data API",
    description="API for managing and retrieving Bahn trajectory data",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router for Bahn-related endpoints
app.include_router(bahn_route_handler.router, prefix="/api/bahn", tags=["bahn"])
app.include_router(auswertung_route_handler.router, prefix="/api/auswertung", tags=["auswertung"])
app.include_router(rosbag_route_handler.router, prefix="/api/rosbag", tags=["rosbag"])
# Transformation Router nur einbinden wenn MATLAB aktiv ist
#if USE_MATLAB:
#    app.include_router(transformation_route_handler.router, prefix="/api/transform", tags=["transform"])
#    logger.info("MATLAB transformation routes enabled")
#else:
#    logger.info("MATLAB transformation routes disabled")

# Initialize the database
init_db(app)

# Initialize Redis cache
@app.on_event("startup")
async def startup_event():
    # Redis initialization bleibt gleich
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = aioredis.from_url(redis_url, encoding="utf8")
        await redis_client.ping()
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache:")
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")

    # Matlab initialization nur wenn USE_MATLAB true ist
    #if USE_MATLAB:
    #    try:
    #        MatlabEngine.get_instance()
    #        logger.info("Successfully initialized MATLAB engine")
    #    except Exception as e:
    #        logger.error(f"Failed to initialize MATLAB engine: {e}")
    #else:
    #    logger.info("MATLAB engine initialization skipped (USE_MATLAB=false)")

#@app.on_event("shutdown")
#async def shutdown_event():
#    # Clean up MATLAB engine only if it was used
#    if USE_MATLAB and MatlabEngine._instance is not None:
#        MatlabEngine._instance.quit()
#        logger.info("Successfully shut down MATLAB engine")

@app.get("/")
async def root():
    return {"message": "Welcome to the Bahn Data API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, timeout_keep_alive=300)