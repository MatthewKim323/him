import numpy as np
from typing import List, Dict, Tuple


class TensionScorer:
    """Calculate mechanical tension scores and generate feedback"""
    
    def __init__(self):
        pass
    
    def calculate_tension_score(
        self,
        analyzed_reps: List[Dict],
        velocity_loss: List[float],
        load_kg: float,
        exercise_name: str
    ) -> Dict:
        """
        Calculate overall tension score and generate feedback
        
        Args:
            analyzed_reps: List of analyzed rep data
            velocity_loss: Velocity loss percentages per rep
            load_kg: External load in kg
            exercise_name: Type of exercise
        
        Returns:
            Dictionary with tension score, high-tension reps, and feedback
        """
        if not analyzed_reps:
            return {
                "tension_score": 0.0,
                "high_tension_reps": [],
                "high_tension_time_seconds": 0.0,
                "feedback_text": "No reps detected in video."
            }
        
        # Base score from velocity loss (primary metric)
        avg_velocity_loss = np.mean(velocity_loss) if velocity_loss else 0.0
        velocity_score = min(100.0, avg_velocity_loss * 1.2)  # Scale to 0-100
        
        # Calculate leverage adjustments
        leverage_scores = self._calculate_leverage_scores(analyzed_reps, exercise_name)
        avg_leverage = np.mean(leverage_scores) if leverage_scores else 0.5
        
        # Identify high-tension reps (velocity loss > 30% or slow velocity)
        high_tension_reps = self._identify_high_tension_reps(
            analyzed_reps,
            velocity_loss
        )
        
        # Calculate high-tension time
        high_tension_time = self._calculate_high_tension_time(
            analyzed_reps,
            high_tension_reps
        )
        
        # Combine scores (70% velocity loss, 30% leverage)
        tension_score = (velocity_score * 0.7) + (avg_leverage * 100 * 0.3)
        tension_score = min(100.0, max(0.0, tension_score))
        
        # Generate feedback
        feedback = self._generate_feedback(
            tension_score,
            high_tension_reps,
            high_tension_time,
            len(analyzed_reps),
            velocity_loss
        )
        
        return {
            "tension_score": round(tension_score, 1),
            "high_tension_reps": high_tension_reps,
            "high_tension_time_seconds": round(high_tension_time, 2),
            "feedback_text": feedback,
            "raw_metrics": {
                "velocity_loss": velocity_loss,
                "avg_velocity_loss": avg_velocity_loss,
                "leverage_scores": leverage_scores,
                "rep_count": len(analyzed_reps)
            }
        }
    
    def _calculate_leverage_scores(
        self,
        analyzed_reps: List[Dict],
        exercise_name: str
    ) -> List[float]:
        """Calculate leverage-based tension scores for each rep"""
        leverage_scores = []
        
        joint_map = {
            "squat": ("left_hip", "left_knee"),
            "bench": ("left_shoulder", "left_elbow"),
            "curl": ("left_elbow", "left_wrist"),
        }
        
        primary_joint, secondary_joint = joint_map.get(
            exercise_name.lower(),
            ("left_hip", "left_knee")
        )
        
        for rep in analyzed_reps:
            frames = rep.get("frames", [])
            if not frames:
                leverage_scores.append(0.5)
                continue
            
            # Find sticking region frames
            sticking = rep.get("sticking_region", {})
            sticking_frames = frames[
                sticking.get("start_frame", 0):
                sticking.get("end_frame", len(frames))
            ]
            
            if not sticking_frames:
                leverage_scores.append(0.5)
                continue
            
            # Calculate average joint angle at sticking point
            angles = []
            for frame in sticking_frames:
                if frame.get("keypoints"):
                    kp = frame["keypoints"]
                    if primary_joint in kp and secondary_joint in kp:
                        # Calculate angle (simplified - using position difference)
                        p1 = kp[primary_joint]
                        p2 = kp[secondary_joint]
                        
                        # Distance from joint (proxy for leverage)
                        dx = p2["x"] - p1["x"]
                        dy = p2["y"] - p1["y"]
                        distance = np.sqrt(dx**2 + dy**2)
                        
                        # Normalize to 0-1 (closer to joint = higher tension)
                        normalized = min(1.0, distance * 2.0)
                        angles.append(normalized)
            
            if angles:
                avg_leverage = np.mean(angles)
                leverage_scores.append(avg_leverage)
            else:
                leverage_scores.append(0.5)
        
        return leverage_scores
    
    def _identify_high_tension_reps(
        self,
        analyzed_reps: List[Dict],
        velocity_loss: List[float]
    ) -> List[int]:
        """Identify which reps had high tension"""
        high_tension = []
        
        for i, rep in enumerate(analyzed_reps):
            # High tension if velocity loss > 30% or velocity is very slow
            vel_loss = velocity_loss[i] if i < len(velocity_loss) else 0.0
            concentric_vel = rep.get("concentric_velocity", 0.0)
            
            # Threshold: velocity loss > 30% OR velocity < 20% of first rep
            first_rep_vel = analyzed_reps[0].get("concentric_velocity", 1.0)
            if first_rep_vel > 0:
                vel_ratio = concentric_vel / first_rep_vel
            else:
                vel_ratio = 1.0
            
            if vel_loss > 30.0 or vel_ratio < 0.2:
                high_tension.append(rep["rep_number"])
        
        return high_tension
    
    def _calculate_high_tension_time(
        self,
        analyzed_reps: List[Dict],
        high_tension_rep_numbers: List[int]
    ) -> float:
        """Calculate total time spent in high-tension regions"""
        total_time = 0.0
        
        for rep in analyzed_reps:
            if rep["rep_number"] in high_tension_rep_numbers:
                sticking = rep.get("sticking_region", {})
                total_time += sticking.get("time", 0.0)
        
        return total_time
    
    def _generate_feedback(
        self,
        tension_score: float,
        high_tension_reps: List[int],
        high_tension_time: float,
        rep_count: int,
        velocity_loss: List[float]
    ) -> str:
        """Generate user-friendly feedback message"""
        if rep_count == 0:
            return "No reps detected. Please ensure you're visible in the video and performing the exercise correctly."
        
        feedback_parts = []
        
        # Overall score feedback
        if tension_score >= 80:
            feedback_parts.append(f"High mechanical tension achieved (Score: {tension_score:.0f}/100).")
        elif tension_score >= 60:
            feedback_parts.append(f"Moderate mechanical tension (Score: {tension_score:.0f}/100).")
        else:
            feedback_parts.append(f"Lower mechanical tension (Score: {tension_score:.0f}/100). Consider increasing load or slowing tempo.")
        
        # High-tension reps feedback
        if high_tension_reps:
            if len(high_tension_reps) == 1:
                feedback_parts.append(f"You hit high tension on rep {high_tension_reps[0]}.")
            elif len(high_tension_reps) <= 3:
                reps_str = ", ".join(map(str, high_tension_reps[:-1])) + f", and {high_tension_reps[-1]}"
                feedback_parts.append(f"You hit high tension on reps {reps_str}.")
            else:
                feedback_parts.append(f"You hit high tension on {len(high_tension_reps)} reps (reps {high_tension_reps[0]}-{high_tension_reps[-1]}).")
            
            feedback_parts.append(f"Total high-tension time: {high_tension_time:.1f} seconds.")
        else:
            feedback_parts.append("No high-tension reps detected. Consider increasing load for better stimulus.")
        
        # Velocity loss feedback
        if velocity_loss and len(velocity_loss) > 1:
            final_loss = velocity_loss[-1]
            if final_loss > 50:
                feedback_parts.append("Significant velocity loss detected - last rep was near failure.")
            elif final_loss > 30:
                feedback_parts.append("Moderate velocity loss - good training stimulus.")
        
        return " ".join(feedback_parts)
