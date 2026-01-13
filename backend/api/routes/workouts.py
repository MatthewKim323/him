from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import json
import tempfile
from pathlib import Path

from database import get_db, User, Workout, Analysis, RepData
from database.schemas import (
    WorkoutCreate,
    WorkoutResponse,
    AnalysisResponse,
    WorkoutWithAnalysis,
    RepDataResponse
)
from auth.dependencies import get_current_user
from services.video_processor import VideoProcessor
from services.rep_segmenter import RepSegmenter
from services.velocity_analyzer import VelocityAnalyzer
from services.tension_scorer import TensionScorer
from config import settings

router = APIRouter(prefix="/api/workouts", tags=["workouts"])

# Ensure temp directory exists
os.makedirs(settings.temp_video_dir, exist_ok=True)


@router.post("/analyze", response_model=WorkoutWithAnalysis, status_code=status.HTTP_201_CREATED)
async def analyze_workout(
    video: UploadFile = File(...),
    exercise_name: str = Form(...),
    load_kg: float = Form(...),
    camera_angle: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and analyze a workout video"""
    
    # Validate file extension
    file_ext = Path(video.filename).suffix.lower()
    if file_ext not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_video_extensions)}"
        )
    
    # Validate file size
    video.file.seek(0, os.SEEK_END)
    file_size = video.file.tell()
    video.file.seek(0)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Save video to temporary file
    temp_file = None
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext,
            dir=settings.temp_video_dir
        )
        
        # Write video data
        content = await video.read()
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()
        
        # Create workout record
        db_workout = Workout(
            user_id=current_user.id,
            exercise_name=exercise_name,
            load_kg=load_kg,
            camera_angle=camera_angle
        )
        db.add(db_workout)
        db.commit()
        db.refresh(db_workout)
        
        # Process video
        processor = VideoProcessor()
        frame_data = processor.process_video(temp_file.name)
        
        # Segment reps
        segmenter = RepSegmenter()
        reps = segmenter.segment_reps(frame_data, exercise_name)
        
        if not reps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not detect reps in video. Please ensure the exercise is clearly visible."
            )
        
        # Analyze velocity and ROM
        velocity_analyzer = VelocityAnalyzer()
        analyzed_reps = velocity_analyzer.analyze_reps(reps, exercise_name)
        velocity_loss = velocity_analyzer.calculate_velocity_loss(analyzed_reps)
        
        # Calculate tension score
        scorer = TensionScorer()
        tension_result = scorer.calculate_tension_score(
            analyzed_reps,
            velocity_loss,
            load_kg,
            exercise_name
        )
        
        # Create analysis record
        db_analysis = Analysis(
            workout_id=db_workout.id,
            tension_score=tension_result["tension_score"],
            high_tension_reps=str(tension_result["high_tension_reps"]),
            high_tension_time_seconds=tension_result["high_tension_time_seconds"],
            feedback_text=tension_result["feedback_text"],
            raw_metrics=tension_result.get("raw_metrics", {})
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        
        # Create rep data records
        for analyzed_rep in analyzed_reps:
            rep_num = analyzed_rep["rep_number"]
            db_rep = RepData(
                analysis_id=db_analysis.id,
                rep_number=rep_num,
                rom=analyzed_rep["rom"],
                velocity=analyzed_rep["concentric_velocity"],
                is_high_tension=rep_num in tension_result["high_tension_reps"],
                sticking_region_time=analyzed_rep["sticking_region"].get("time")
            )
            db.add(db_rep)
        
        db.commit()
        db.refresh(db_analysis)
        
        # Load rep data for response
        rep_data = db.query(RepData).filter(RepData.analysis_id == db_analysis.id).all()
        
        # Convert to response models
        workout_response = WorkoutResponse.model_validate(db_workout)
        
        # Parse high_tension_reps from string to list
        high_tension_reps_list = json.loads(db_analysis.high_tension_reps) if db_analysis.high_tension_reps else []
        
        # Create analysis response with rep_data
        analysis_dict = {
            "id": db_analysis.id,
            "workout_id": db_analysis.workout_id,
            "tension_score": db_analysis.tension_score,
            "high_tension_reps": high_tension_reps_list,
            "high_tension_time_seconds": db_analysis.high_tension_time_seconds,
            "feedback_text": db_analysis.feedback_text,
            "raw_metrics": db_analysis.raw_metrics,
            "rep_data": [RepDataResponse.model_validate(rep) for rep in rep_data],
            "created_at": db_analysis.created_at
        }
        analysis_response = AnalysisResponse(**analysis_dict)
        
        return {
            **workout_response.model_dump(),
            "analysis": analysis_response.model_dump()
        }
        
    except Exception as e:
        # Clean up workout if analysis failed
        if 'db_workout' in locals():
            db.delete(db_workout)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing video: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass


@router.get("/{workout_id}", response_model=WorkoutWithAnalysis)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific workout and its analysis"""
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    analysis = db.query(Analysis).filter(Analysis.workout_id == workout_id).first()
    rep_data = []
    if analysis:
        rep_data = db.query(RepData).filter(RepData.analysis_id == analysis.id).all()
    
    workout_response = WorkoutResponse.model_validate(workout)
    
    if analysis:
        # Parse high_tension_reps from string to list
        high_tension_reps_list = json.loads(analysis.high_tension_reps) if analysis.high_tension_reps else []
        
        analysis_dict = {
            "id": analysis.id,
            "workout_id": analysis.workout_id,
            "tension_score": analysis.tension_score,
            "high_tension_reps": high_tension_reps_list,
            "high_tension_time_seconds": analysis.high_tension_time_seconds,
            "feedback_text": analysis.feedback_text,
            "raw_metrics": analysis.raw_metrics,
            "rep_data": [RepDataResponse.model_validate(rep) for rep in rep_data],
            "created_at": analysis.created_at
        }
        analysis_response = AnalysisResponse(**analysis_dict)
    else:
        analysis_response = None
    
    return {
        **workout_response.model_dump(),
        "analysis": analysis_response.model_dump() if analysis_response else None
    }


@router.get("", response_model=List[WorkoutResponse])
def list_workouts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all workouts for the current user"""
    workouts = db.query(Workout).filter(
        Workout.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return workouts


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a workout and its associated analysis"""
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    db.delete(workout)
    db.commit()
    
    return None
