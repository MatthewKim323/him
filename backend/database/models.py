from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    height_cm = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workouts = relationship("Workout", back_populates="user")


class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_name = Column(String, nullable=False)
    load_kg = Column(Float, nullable=False)
    camera_angle = Column(String, nullable=True)  # "side", "front", "back", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="workouts")
    analysis = relationship("Analysis", back_populates="workout", uselist=False)


class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False, unique=True)
    tension_score = Column(Float, nullable=False)  # 0-100
    high_tension_reps = Column(String, nullable=True)  # JSON array of rep numbers
    high_tension_time_seconds = Column(Float, nullable=False)
    feedback_text = Column(Text, nullable=True)
    raw_metrics = Column(JSON, nullable=True)  # Store all calculated metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workout = relationship("Workout", back_populates="analysis")
    rep_data = relationship("RepData", back_populates="analysis", cascade="all, delete-orphan")


class RepData(Base):
    __tablename__ = "rep_data"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    rep_number = Column(Integer, nullable=False)
    rom = Column(Float, nullable=False)  # Range of motion in pixels/normalized units
    velocity = Column(Float, nullable=False)  # Concentric velocity
    is_high_tension = Column(Boolean, default=False)
    sticking_region_time = Column(Float, nullable=True)  # Time in slowest portion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    analysis = relationship("Analysis", back_populates="rep_data")
