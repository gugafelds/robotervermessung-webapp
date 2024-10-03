
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import bahn_route_handler
from .models.bahn_models import Base
from .database import engine

# Note: We're not creating tables as they already exist
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bahn Data API",
    description="API for managing and retrieving Bahn trajectory data",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Assuming your Next.js frontend is running on port 3000
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your Next.js frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router for Bahn-related endpoints
app.include_router(bahn_route_handler.router, prefix="/api/bahn", tags=["bahn"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Bahn Data API"}

@app.on_event("startup")
async def startup_event():
    # You can add any startup events here, like initializing database connections
    print("Starting up the Bahn Data API...")

@app.on_event("shutdown")
async def shutdown_event():
    # You can add any shutdown events here, like closing database connections
    print("Shutting down the Bahn Data API...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)