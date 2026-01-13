from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost/him_db"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File upload
    max_upload_size_mb: int = 100
    allowed_video_extensions: list[str] = [".mp4", ".mov", ".avi", ".mkv"]
    temp_video_dir: str = "/tmp/him_videos"
    
    # MediaPipe
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
