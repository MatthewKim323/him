import numpy as np
from typing import List, Dict, Tuple, Optional


class RepSegmenter:
    """Segment workout video into individual reps based on exercise type"""
    
    def __init__(self):
        self.exercise_configs = {
            "squat": {
                "primary_joints": ["left_knee", "right_knee", "left_hip", "right_hip"],
                "angle_joints": {
                    "knee": ("hip", "knee", "ankle"),
                    "hip": ("shoulder", "hip", "knee")
                },
                "bottom_threshold": 0.3,  # Max flexion threshold
                "top_threshold": 0.7,  # Extension threshold
            },
            "bench": {
                "primary_joints": ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder"],
                "angle_joints": {
                    "elbow": ("shoulder", "elbow", "wrist"),
                    "shoulder": ("hip", "shoulder", "elbow")
                },
                "bottom_threshold": 0.2,
                "top_threshold": 0.8,
            },
            "curl": {
                "primary_joints": ["left_elbow", "right_elbow"],
                "angle_joints": {
                    "elbow": ("shoulder", "elbow", "wrist")
                },
                "bottom_threshold": 0.15,  # Full extension
                "top_threshold": 0.85,  # Max flexion
            },
        }
    
    def segment_reps(
        self,
        frame_data: List[Dict],
        exercise_name: str
    ) -> List[Dict]:
        """
        Segment video frames into individual reps
        
        Args:
            frame_data: List of frames with keypoints
            exercise_name: Type of exercise (squat, bench, curl, etc.)
        
        Returns:
            List of rep segments with start/end frames
        """
        config = self.exercise_configs.get(exercise_name.lower())
        if not config:
            # Default to squat if exercise not recognized
            config = self.exercise_configs["squat"]
        
        # Calculate joint angles for each frame
        angles = self._calculate_angles(frame_data, config)
        
        # Find rep boundaries
        reps = self._find_rep_boundaries(angles, frame_data, config)
        
        return reps
    
    def _calculate_angles(
        self,
        frame_data: List[Dict],
        config: Dict
    ) -> List[float]:
        """Calculate primary joint angles for rep detection"""
        angles = []
        
        for frame in frame_data:
            if not frame.get("has_pose") or not frame.get("keypoints"):
                angles.append(None)
                continue
            
            keypoints = frame["keypoints"]
            
            # Calculate average angle for primary joints
            angle_values = []
            for angle_name, (joint1, joint2, joint3) in config["angle_joints"].items():
                # Try left and right sides
                for side in ["left_", "right_"]:
                    j1_key = f"{side}{joint1}"
                    j2_key = f"{side}{joint2}"
                    j3_key = f"{side}{joint3}"
                    
                    if all(k in keypoints for k in [j1_key, j2_key, j3_key]):
                        angle = self._calculate_joint_angle(
                            keypoints[j1_key],
                            keypoints[j2_key],
                            keypoints[j3_key]
                        )
                        if angle is not None:
                            angle_values.append(angle)
            
            if angle_values:
                # Use average angle, normalized to 0-1
                avg_angle = np.mean(angle_values)
                # Normalize based on typical range (0-180 degrees -> 0-1)
                normalized = avg_angle / 180.0
                angles.append(normalized)
            else:
                angles.append(None)
        
        return angles
    
    def _calculate_joint_angle(
        self,
        point1: Dict,
        point2: Dict,
        point3: Dict
    ) -> Optional[float]:
        """Calculate angle at point2 between point1 and point3"""
        try:
            # Convert to numpy arrays (using x, y coordinates)
            p1 = np.array([point1["x"], point1["y"]])
            p2 = np.array([point2["x"], point2["y"]])
            p3 = np.array([point3["x"], point3["y"]])
            
            # Calculate vectors
            v1 = p1 - p2
            v2 = p3 - p2
            
            # Calculate angle
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(cos_angle)
            
            return np.degrees(angle)
        except (KeyError, ValueError, ZeroDivisionError):
            return None
    
    def _find_rep_boundaries(
        self,
        angles: List[Optional[float]],
        frame_data: List[Dict],
        config: Dict
    ) -> List[Dict]:
        """Find rep start and end points based on angle thresholds"""
        if not angles or all(a is None for a in angles):
            return []
        
        # Smooth angles with moving average
        smoothed = self._smooth_angles(angles)
        
        reps = []
        in_rep = False
        rep_start = None
        direction = None  # "down" or "up"
        
        bottom_threshold = config["bottom_threshold"]
        top_threshold = config["top_threshold"]
        
        for i, angle in enumerate(smoothed):
            if angle is None:
                continue
            
            if not in_rep:
                # Looking for rep start (going down past top threshold)
                if angle < top_threshold:
                    in_rep = True
                    rep_start = i
                    direction = "down"
            else:
                # Track direction changes
                if direction == "down" and angle <= bottom_threshold:
                    direction = "up"  # Reached bottom, now going up
                elif direction == "up" and angle >= top_threshold:
                    # Completed a rep
                    reps.append({
                        "rep_number": len(reps) + 1,
                        "start_frame": rep_start,
                        "end_frame": i,
                        "start_time": frame_data[rep_start]["timestamp"],
                        "end_time": frame_data[i]["timestamp"],
                        "frames": frame_data[rep_start:i+1]
                    })
                    in_rep = False
                    rep_start = None
        
        # Handle incomplete last rep
        if in_rep and rep_start is not None:
            if len(reps) == 0 or rep_start > reps[-1]["end_frame"]:
                reps.append({
                    "rep_number": len(reps) + 1,
                    "start_frame": rep_start,
                    "end_frame": len(frame_data) - 1,
                    "start_time": frame_data[rep_start]["timestamp"],
                    "end_time": frame_data[-1]["timestamp"],
                    "frames": frame_data[rep_start:]
                })
        
        return reps
    
    def _smooth_angles(self, angles: List[Optional[float]], window: int = 5) -> List[Optional[float]]:
        """Smooth angles with moving average"""
        smoothed = []
        for i in range(len(angles)):
            if angles[i] is None:
                smoothed.append(None)
                continue
            
            # Get window of valid angles
            window_angles = []
            for j in range(max(0, i - window // 2), min(len(angles), i + window // 2 + 1)):
                if angles[j] is not None:
                    window_angles.append(angles[j])
            
            if window_angles:
                smoothed.append(np.mean(window_angles))
            else:
                smoothed.append(None)
        
        return smoothed
