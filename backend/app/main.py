from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import bahn_route_handler
from .database import init_db

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

# Initialize the database
init_db(app)

@app.get("/")
async def root():
    return {"message": "Welcome to the Bahn Data API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)