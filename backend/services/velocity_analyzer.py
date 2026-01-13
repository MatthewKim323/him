import numpy as np
from typing import List, Dict, Tuple


class VelocityAnalyzer:
    """Analyze velocity, ROM, and identify sticking regions"""
    
    def __init__(self):
        pass
    
    def analyze_reps(self, reps: List[Dict], exercise_name: str) -> List[Dict]:
        """
        Analyze each rep for velocity, ROM, and sticking regions
        
        Args:
            reps: List of rep segments from RepSegmenter
            exercise_name: Type of exercise
        
        Returns:
            List of analyzed rep data
        """
        analyzed_reps = []
        
        for rep in reps:
            frames = rep["frames"]
            if len(frames) < 2:
                continue
            
            # Calculate ROM (range of motion)
            rom = self._calculate_rom(frames, exercise_name)
            
            # Calculate velocities
            velocities = self._calculate_velocities(frames, exercise_name)
            
            # Find concentric phase (lifting phase)
            concentric_velocity = self._get_concentric_velocity(velocities, frames, exercise_name)
            
            # Identify sticking region (slowest 20-30% of ROM)
            sticking_region = self._find_sticking_region(frames, velocities, exercise_name)
            
            analyzed_reps.append({
                "rep_number": rep["rep_number"],
                "rom": rom,
                "velocities": velocities,
                "concentric_velocity": concentric_velocity,
                "sticking_region": sticking_region,
                "frames": frames
            })
        
        return analyzed_reps
    
    def _calculate_rom(self, frames: List[Dict], exercise_name: str) -> float:
        """Calculate range of motion for a rep"""
        if not frames:
            return 0.0
        
        # Get primary joint for ROM calculation
        joint_map = {
            "squat": "left_hip",
            "bench": "left_elbow",
            "curl": "left_elbow",
        }
        
        primary_joint = joint_map.get(exercise_name.lower(), "left_hip")
        
        positions = []
        for frame in frames:
            if frame.get("keypoints") and primary_joint in frame["keypoints"]:
                joint = frame["keypoints"][primary_joint]
                # Use y-coordinate (vertical position)
                positions.append(joint["y"])
        
        if len(positions) < 2:
            return 0.0
        
        # ROM is the difference between max and min position
        rom = max(positions) - min(positions)
        return rom
    
    def _calculate_velocities(
        self,
        frames: List[Dict],
        exercise_name: str
    ) -> List[float]:
        """Calculate velocity for each frame"""
        velocities = [0.0]  # First frame has no velocity
        
        joint_map = {
            "squat": "left_hip",
            "bench": "left_elbow",
            "curl": "left_elbow",
        }
        
        primary_joint = joint_map.get(exercise_name.lower(), "left_hip")
        
        for i in range(1, len(frames)):
            prev_frame = frames[i - 1]
            curr_frame = frames[i]
            
            if not (prev_frame.get("keypoints") and curr_frame.get("keypoints")):
                velocities.append(0.0)
                continue
            
            if primary_joint not in prev_frame["keypoints"] or primary_joint not in curr_frame["keypoints"]:
                velocities.append(0.0)
                continue
            
            prev_pos = prev_frame["keypoints"][primary_joint]
            curr_pos = curr_frame["keypoints"][primary_joint]
            
            # Calculate displacement (using y-coordinate for vertical movement)
            dt = curr_frame["timestamp"] - prev_frame["timestamp"]
            if dt <= 0:
                velocities.append(0.0)
                continue
            
            dy = curr_pos["y"] - prev_pos["y"]
            velocity = dy / dt
            
            velocities.append(velocity)
        
        # Smooth velocities with moving average
        return self._smooth_velocities(velocities)
    
    def _smooth_velocities(self, velocities: List[float], window: int = 3) -> List[float]:
        """Smooth velocities with moving average"""
        smoothed = []
        for i in range(len(velocities)):
            start = max(0, i - window // 2)
            end = min(len(velocities), i + window // 2 + 1)
            window_vels = velocities[start:end]
            smoothed.append(np.mean(window_vels))
        return smoothed
    
    def _get_concentric_velocity(
        self,
        velocities: List[float],
        frames: List[Dict],
        exercise_name: str
    ) -> float:
        """Get average concentric (lifting) phase velocity"""
        # Concentric phase has negative velocity (moving up = decreasing y)
        # For most exercises, concentric is when velocity is most negative
        if not velocities:
            return 0.0
        
        # Find the most negative velocities (fastest upward movement)
        negative_velocities = [v for v in velocities if v < 0]
        
        if not negative_velocities:
            return 0.0
        
        # Use average of bottom 50% (fastest movements)
        sorted_vels = sorted(negative_velocities)
        bottom_half = sorted_vels[:len(sorted_vels) // 2]
        
        return abs(np.mean(bottom_half)) if bottom_half else 0.0
    
    def _find_sticking_region(
        self,
        frames: List[Dict],
        velocities: List[float],
        exercise_name: str
    ) -> Dict:
        """Find the sticking region (slowest 20-30% of ROM)"""
        if len(frames) < 2 or len(velocities) < 2:
            return {"start_frame": 0, "end_frame": 0, "time": 0.0}
        
        # Find frames in concentric phase (negative velocities)
        concentric_frames = []
        for i, vel in enumerate(velocities):
            if i < len(frames) and vel < 0:  # Moving up
                concentric_frames.append((i, abs(vel)))  # Use absolute value
        
        if not concentric_frames:
            return {"start_frame": 0, "end_frame": 0, "time": 0.0}
        
        # Sort by velocity (slowest first)
        concentric_frames.sort(key=lambda x: x[1])
        
        # Get slowest 25% of frames
        slowest_count = max(1, int(len(concentric_frames) * 0.25))
        slowest_frames = [f[0] for f in concentric_frames[:slowest_count]]
        
        if not slowest_frames:
            return {"start_frame": 0, "end_frame": 0, "time": 0.0}
        
        start_frame = min(slowest_frames)
        end_frame = max(slowest_frames)
        
        # Calculate time duration
        if end_frame < len(frames) and start_frame < len(frames):
            time = frames[end_frame]["timestamp"] - frames[start_frame]["timestamp"]
        else:
            time = 0.0
        
        return {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "time": time
        }
    
    def calculate_velocity_loss(self, analyzed_reps: List[Dict]) -> List[float]:
        """Calculate velocity loss percentage for each rep relative to first rep"""
        if not analyzed_reps:
            return []
        
        first_rep_velocity = analyzed_reps[0].get("concentric_velocity", 0.0)
        if first_rep_velocity == 0:
            return [0.0] * len(analyzed_reps)
        
        velocity_loss = []
        for rep in analyzed_reps:
            current_velocity = rep.get("concentric_velocity", 0.0)
            if current_velocity == 0:
                loss = 100.0
            else:
                loss = ((first_rep_velocity - current_velocity) / first_rep_velocity) * 100.0
            velocity_loss.append(max(0.0, loss))
        
        return velocity_loss
