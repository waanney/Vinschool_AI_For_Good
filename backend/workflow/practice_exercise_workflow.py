"""
Practice Exercise Request Workflow.
Handles student requests for personalized practice exercises based on weak points.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID

from agents.teaching_assistant.agent import TeachingAssistantAgent
from agents.grading.agent import GradingAgent, GradingCriteria
from domain.models.assignment import Assignment
from utils.logger import logger


class WeakPoint:
    """Represents a knowledge gap detected in student performance."""
    
    def __init__(
        self,
        topic: str,
        subject: str,
        error_rate: float,
        recent_mistakes: List[str],
    ):
        self.topic = topic
        self.subject = subject
        self.error_rate = error_rate
        self.recent_mistakes = recent_mistakes


class ExerciseRecommendation:
    """Represents a recommended practice exercise."""
    
    def __init__(
        self,
        exercise_id: str,
        title: str,
        topic: str,
        difficulty: str,
        description: str,
        max_score: float = 100.0,
    ):
        self.exercise_id = exercise_id
        self.title = title
        self.topic = topic
        self.difficulty = difficulty
        self.description = description
        self.max_score = max_score
    
    def to_dict(self) -> dict:
        return {
            "exercise_id": self.exercise_id,
            "title": self.title,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "description": self.description,
            "max_score": self.max_score,
        }


class PracticeExerciseWorkflow:
    """
    Workflow for personalized practice exercise requests.
    
    Flow:
    1. Student requests additional practice exercises
    2. AI analyzes past performance to detect weak points
    3. AI selects appropriate exercises from teacher's pool
    4. Student submits work (image/link)
    5. AI grades and provides feedback
    6. System tracks progress data
    """
    
    def __init__(self):
        self.teaching_agent = TeachingAssistantAgent()
        self.grading_agent = GradingAgent()
    
    async def analyze_weak_points(
        self,
        student_id: str,
        subject: str,
        grade: int,
        recent_assignments: Optional[List[Assignment]] = None,
    ) -> List[WeakPoint]:
        """
        Analyze student's performance to detect knowledge gaps.
        
        Args:
            student_id: Student ID
            subject: Subject area
            grade: Student's grade level
            recent_assignments: Optional list of recent assignments to analyze
            
        Returns:
            List of detected weak points
        """
        logger.info(f"Analyzing weak points for student {student_id} in {subject}")
        
        try:
            # TODO: In production, retrieve from database
            # For now, use provided assignments or create mock data
            if not recent_assignments:
                logger.warning("No assignment history provided, cannot detect weak points accurately")
                return []
            
            # Analyze performance patterns
            topic_performance: Dict[str, List[float]] = {}
            topic_mistakes: Dict[str, List[str]] = {}
            
            for assignment in recent_assignments:
                # Extract performance by topic from assignment feedback
                # This would typically parse structured grading data
                topic = assignment.title  # Simplified - would extract actual topic
                
                if hasattr(assignment, 'score') and assignment.score is not None:
                    if topic not in topic_performance:
                        topic_performance[topic] = []
                        topic_mistakes[topic] = []
                    
                    # Calculate error rate (inverse of score)
                    score_ratio = assignment.score / assignment.max_score
                    error_rate = 1.0 - score_ratio
                    topic_performance[topic].append(error_rate)
                    
                    # Extract common mistakes from feedback
                    if hasattr(assignment, 'feedback') and assignment.feedback:
                        topic_mistakes[topic].append(assignment.feedback[:100])
            
            # Identify weak points (error rate > 30%)
            weak_points = []
            for topic, error_rates in topic_performance.items():
                avg_error_rate = sum(error_rates) / len(error_rates)
                
                if avg_error_rate > 0.3:  # 30% or more errors
                    weak_point = WeakPoint(
                        topic=topic,
                        subject=subject,
                        error_rate=avg_error_rate,
                        recent_mistakes=topic_mistakes.get(topic, []),
                    )
                    weak_points.append(weak_point)
            
            # Sort by error rate (highest first)
            weak_points.sort(key=lambda wp: wp.error_rate, reverse=True)
            
            logger.info(f"Detected {len(weak_points)} weak points for student {student_id}")
            
            return weak_points
            
        except Exception as e:
            logger.error(f"Error analyzing weak points: {e}")
            return []
    
    async def recommend_exercises(
        self,
        student_id: str,
        grade: int,
        subject: str,
        weak_points: List[WeakPoint],
        num_exercises: int = 5,
    ) -> List[ExerciseRecommendation]:
        """
        Select appropriate practice exercises based on detected weak points.
        
        Args:
            student_id: Student ID
            grade: Student's grade level
            subject: Subject area
            weak_points: Detected knowledge gaps
            num_exercises: Number of exercises to recommend
            
        Returns:
            List of recommended exercises
        """
        logger.info(
            f"Recommending {num_exercises} exercises for student {student_id} "
            f"targeting {len(weak_points)} weak points"
        )
        
        try:
            if not weak_points:
                logger.warning("No weak points detected, generating general exercises")
                # Generate general practice exercises
                exercises_text = await self.teaching_agent.generate_personalized_exercises(
                    student_level="intermediate",
                    subject=subject,
                    topic=f"Grade {grade} {subject} review",
                    num_exercises=num_exercises,
                )
                
                recommendations = []
                for i, exercise in enumerate(exercises_text[:num_exercises], 1):
                    recommendations.append(
                        ExerciseRecommendation(
                            exercise_id=f"gen_{i}",
                            title=f"General Practice Exercise {i}",
                            topic=subject,
                            difficulty="intermediate",
                            description=exercise,
                        )
                    )
                
                return recommendations
            
            # Generate targeted exercises for each weak point
            recommendations = []
            exercises_per_topic = max(1, num_exercises // len(weak_points))
            
            for weak_point in weak_points[:num_exercises]:
                # Determine difficulty based on error rate
                if weak_point.error_rate > 0.6:
                    difficulty = "beginner"  # High error rate → easier exercises
                elif weak_point.error_rate > 0.4:
                    difficulty = "intermediate"
                else:
                    difficulty = "advanced"
                
                # Generate exercises for this topic
                exercises_text = await self.teaching_agent.generate_personalized_exercises(
                    student_level=difficulty,
                    subject=subject,
                    topic=weak_point.topic,
                    num_exercises=exercises_per_topic,
                )
                
                # Create recommendations
                for i, exercise in enumerate(exercises_text[:exercises_per_topic], 1):
                    recommendations.append(
                        ExerciseRecommendation(
                            exercise_id=f"{weak_point.topic.replace(' ', '_')}_{i}",
                            title=f"Practice: {weak_point.topic} #{i}",
                            topic=weak_point.topic,
                            difficulty=difficulty,
                            description=exercise,
                        )
                    )
                
                if len(recommendations) >= num_exercises:
                    break
            
            logger.info(f"Generated {len(recommendations)} targeted exercise recommendations")
            
            return recommendations[:num_exercises]
            
        except Exception as e:
            logger.error(f"Error recommending exercises: {e}")
            return []
    
    async def handle_practice_request(
        self,
        student_id: str,
        grade: int,
        subject: str,
        class_name: Optional[str] = None,
        num_exercises: int = 5,
        recent_assignments: Optional[List[Assignment]] = None,
    ) -> dict:
        """
        Handle complete practice exercise request flow.
        
        Args:
            student_id: Student ID
            grade: Student's grade level
            subject: Subject area
            class_name: Optional class identifier
            num_exercises: Number of exercises to generate
            recent_assignments: Optional recent assignment history
            
        Returns:
            Dictionary with recommended exercises and weak point analysis
        """
        logger.info(
            f"Processing practice request for student {student_id} "
            f"(Grade {grade}, {subject})"
        )
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "grade": grade,
            "timestamp": datetime.utcnow().isoformat(),
            "weak_points": [],
            "recommendations": [],
            "success": False,
            "error": None,
        }
        
        try:
            # Step 1: Analyze weak points
            weak_points = await self.analyze_weak_points(
                student_id=student_id,
                subject=subject,
                grade=grade,
                recent_assignments=recent_assignments,
            )
            
            result["weak_points"] = [
                {
                    "topic": wp.topic,
                    "error_rate": wp.error_rate,
                    "recent_mistakes": wp.recent_mistakes[:3],  # Limit for brevity
                }
                for wp in weak_points
            ]
            
            # Step 2: Recommend exercises
            recommendations = await self.recommend_exercises(
                student_id=student_id,
                grade=grade,
                subject=subject,
                weak_points=weak_points,
                num_exercises=num_exercises,
            )
            
            result["recommendations"] = [rec.to_dict() for rec in recommendations]
            result["success"] = True
            
            logger.info(
                f"Successfully processed practice request: "
                f"{len(weak_points)} weak points, {len(recommendations)} exercises"
            )
            
        except Exception as e:
            logger.error(f"Error handling practice request: {e}")
            result["error"] = str(e)
        
        return result
    
    async def grade_practice_submission(
        self,
        assignment: Assignment,
        rubric: List[GradingCriteria],
        submission_file_path: Optional[str] = None,
    ) -> dict:
        """
        Grade a practice exercise submission.
        
        Args:
            assignment: Assignment entity
            rubric: Grading rubric
            submission_file_path: Path to submission file
            
        Returns:
            Grading result with score and feedback
        """
        logger.info(f"Grading practice submission for assignment {assignment.id}")
        
        result = {
            "assignment_id": str(assignment.id),
            "student_id": str(assignment.student_id),
            "graded_at": datetime.utcnow().isoformat(),
            "success": False,
            "score": 0.0,
            "feedback": "",
            "details": {},
        }
        
        try:
            # Mark assignment as being graded
            assignment.start_grading()
            
            # Grade the submission
            grading_result = await self.grading_agent.grade_assignment(
                assignment=assignment,
                rubric=rubric,
                submission_file_path=submission_file_path,
            )
            
            # Update assignment
            assignment.complete_ai_grading(
                score=grading_result.total_score,
                feedback=grading_result.feedback,
            )
            
            # Update result
            result["success"] = True
            result["score"] = grading_result.total_score
            result["feedback"] = grading_result.feedback
            result["details"] = {
                "criteria_scores": grading_result.criteria_scores,
            }
            
            logger.info(
                f"Successfully graded practice submission: "
                f"Score {grading_result.total_score}/{assignment.max_score}"
            )
            
        except Exception as e:
            logger.error(f"Error grading practice submission: {e}")
            result["error"] = str(e)
        
        return result
