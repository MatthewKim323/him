import cv2
import mediapipe as mp
import numpy as np
import json
from typing import List, Dict, Optional
from pathlib import Path
from config import settings

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


class VideoProcessor:
    """Process videos and extract pose keypoints using MediaPipe"""
    
    def __init__(self):
        self.pose = mp_pose.Pose(
            min_detection_confidence=settings.min_detection_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
            model_complexity=2  # Use full model for better accuracy
        )
    
    def process_video(self, video_path: str, fps: int = 30) -> List[Dict]:
        """
        Process video and extract pose keypoints for each frame
        
        Args:
            video_path: Path to video file
            fps: Target frames per second to process (default 30)
        
        Returns:
            List of dictionaries containing frame data and keypoints
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = max(1, int(video_fps / fps))
        
        frame_data = []
        frame_number = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process every nth frame based on target fps
            if frame_number % frame_interval == 0:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process frame with MediaPipe
                results = self.pose.process(rgb_frame)
                
                # Extract keypoints
                keypoints = self._extract_keypoints(results)
                
                frame_data.append({
                    "frame_number": frame_number,
                    "timestamp": frame_number / video_fps,
                    "keypoints": keypoints,
                    "has_pose": results.pose_landmarks is not None
                })
            
            frame_number += 1
        
        cap.release()
        self.pose.close()
        
        return frame_data
    
    def _extract_keypoints(self, results) -> Optional[Dict]:
        """Extract keypoint coordinates from MediaPipe results"""
        if not results.pose_landmarks:
            return None
        
        keypoints = {}
        landmark_names = {
            0: "nose",
            11: "left_shoulder",
            12: "right_shoulder",
            13: "left_elbow",
            14: "right_elbow",
            15: "left_wrist",
            16: "right_wrist",
            23: "left_hip",
            24: "right_hip",
            25: "left_knee",
            26: "right_knee",
            27: "left_ankle",
            28: "right_ankle",
        }
        
        for idx, name in landmark_names.items():
            landmark = results.pose_landmarks.landmark[idx]
            keypoints[name] = {
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z,
                "visibility": landmark.visibility
            }
        
        return keypoints
    
    def get_video_info(self, video_path: str) -> Dict:
        """Get basic video information"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration
        }
