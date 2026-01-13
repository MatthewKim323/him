from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from api.routes import auth, workouts
from config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="HIM - Mechanical Tension Analysis API",
    description="API for analyzing workout videos and quantifying mechanical tension",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(workouts.router)


@app.get("/")
def root():
    return {"message": "HIM API - Mechanical Tension Analysis"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
