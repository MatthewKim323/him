from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    height_cm: Optional[float] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Workout schemas
class WorkoutBase(BaseModel):
    exercise_name: str
    load_kg: float
    camera_angle: Optional[str] = None


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutResponse(WorkoutBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Analysis schemas
class RepDataResponse(BaseModel):
    id: int
    rep_number: int
    rom: float
    velocity: float
    is_high_tension: bool
    sticking_region_time: Optional[float] = None
    
    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: int
    workout_id: int
    tension_score: float
    high_tension_reps: Optional[List[int]] = None
    high_tension_time_seconds: float
    feedback_text: Optional[str] = None
    raw_metrics: Optional[dict] = None
    rep_data: List[RepDataResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorkoutWithAnalysis(WorkoutResponse):
    analysis: Optional[AnalysisResponse] = None
