"""
Homework Grading Workflow.
Handles automated grading of student submissions.
"""

from typing import List, Optional
from datetime import datetime

from domain.models.assignment import Assignment
from agents.grading.agent import GradingAgent, GradingCriteria
from config.settings import get_settings
from utils.logger import logger

# Import notification service (lazy to avoid circular imports)
_notification_service = None


def _get_notification_service():
    """Lazy load notification service."""
    global _notification_service
    if _notification_service is None:
        from services.notification import get_notification_service
        _notification_service = get_notification_service()
    return _notification_service


class HomeworkGradingWorkflow:
    """
    Workflow for automated homework grading.

    Flow:
    1. Student submits homework
    2. Extract text (OCR if needed)
    3. Grade against rubric
    4. Generate feedback
    5. Notify student and teacher
    """

    def __init__(self):
        self.grading_agent = GradingAgent()

    async def grade_homework(
        self,
        assignment: Assignment,
        rubric: List[GradingCriteria],
        submission_file_path: Optional[str] = None,
        notify_teacher: bool = True,
        teacher_id: Optional[str] = None,
        teacher_name: Optional[str] = None,
        teacher_email: Optional[str] = None,
        student_name: Optional[str] = None,
    ) -> dict:
        """
        Grade a homework submission.

        Args:
            assignment: Assignment entity
            rubric: Grading rubric
            submission_file_path: Path to submission file (for images)
            notify_student: Whether to notify student
            notify_teacher: Whether to notify teacher

        Returns:
            Dictionary with grading results
        """
        logger.info(f"Grading homework assignment {assignment.id}")

        result = {
            "assignment_id": str(assignment.id),
            "student_id": str(assignment.student_id),
            "graded_at": datetime.utcnow().isoformat(),
            "success": False,
            "score": 0.0,
            "feedback": "",
            "details": {},
            "error": None,
        }

        try:
            # Mark assignment as being graded
            assignment.start_grading()

            # Grade the assignment
            grading_result = await self.grading_agent.grade_assignment(
                assignment=assignment,
                rubric=rubric,
                submission_file_path=submission_file_path,
                student_name=student_name,
            )

            # Update assignment with results
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
                "strengths": grading_result.strengths,
                "improvements": grading_result.improvements,
            }

            logger.info(
                f"Successfully graded assignment {assignment.id}: "
                f"Score {grading_result.total_score}/{assignment.max_score}"
            )

            # Check for low grade and notify teacher
            settings = get_settings()
            if notify_teacher and grading_result.total_score < settings.LOW_GRADE_THRESHOLD:
                await self._notify_low_grade(
                    assignment=assignment,
                    score=grading_result.total_score,
                    feedback=grading_result.feedback,
                    improvements=grading_result.improvements,
                    teacher_id=teacher_id,
                    teacher_name=teacher_name,
                    teacher_email=teacher_email,
                    student_name=student_name,
                )

        except Exception as e:
            logger.error(f"Error grading homework {assignment.id}: {e}")
            result["error"] = str(e)

        return result

    async def grade_batch(
        self,
        assignments: List[tuple[Assignment, List[GradingCriteria]]],
    ) -> List[dict]:
        """
        Grade multiple assignments in batch.

        Args:
            assignments: List of (assignment, rubric) tuples

        Returns:
            List of grading results
        """
        results = []

        for assignment, rubric in assignments:
            result = await self.grade_homework(
                assignment=assignment,
                rubric=rubric,
                notify_student=False,  # Batch notification later
            )
            results.append(result)

        logger.info(f"Batch graded {len(assignments)} assignments")

        return results

    def create_standard_rubric(self, subject: str, assignment_type: str) -> List[GradingCriteria]:
        """
        Create standard rubric based on subject and assignment type.
        This can be customized per teacher/school.
        """
        # Example rubrics - should be configurable
        rubrics = {
            "Mathematics:homework": [
                GradingCriteria(
                    criteria_name="Correctness",
                    max_points=60,
                    description="Accuracy of answers and calculations",
                ),
                GradingCriteria(
                    criteria_name="Work Shown",
                    max_points=20,
                    description="Clear demonstration of problem-solving process",
                ),
                GradingCriteria(
                    criteria_name="Presentation",
                    max_points=20,
                    description="Neatness and organization of work",
                ),
            ],
            "English:essay": [
                GradingCriteria(
                    criteria_name="Content",
                    max_points=40,
                    description="Relevance, depth, and accuracy of content",
                ),
                GradingCriteria(
                    criteria_name="Organization",
                    max_points=30,
                    description="Structure, coherence, and logical flow",
                ),
                GradingCriteria(
                    criteria_name="Language",
                    max_points=30,
                    description="Grammar, vocabulary, and writing style",
                ),
            ],
        }

        key = f"{subject}:{assignment_type}"
        return rubrics.get(key, [
            GradingCriteria(
                criteria_name="Overall Quality",
                max_points=100,
                description="Overall quality of submission",
            )
        ])

    async def _notify_low_grade(
        self,
        assignment: Assignment,
        score: float,
        feedback: str,
        improvements: list[str],
        teacher_id: Optional[str] = None,
        teacher_name: Optional[str] = None,
        teacher_email: Optional[str] = None,
        student_name: Optional[str] = None,
    ) -> None:
        """
        Send low grade alert to teacher(s) when student scores below threshold.
        """
        if not teacher_email:
            logger.debug("No teacher email provided, skipping low grade notification")
            return

        try:
            from services.notification import (
                TeacherInfo,
                StudentInfo,
                NotificationChannel,
            )

            service = _get_notification_service()

            if not service.email_enabled:
                logger.debug("Email notifications disabled, skipping low grade alert")
                return

            settings = get_settings()

            teacher = TeacherInfo(
                teacher_id=teacher_id or str(assignment.teacher_id),
                name=teacher_name or "Teacher",
                email=teacher_email,
            )

            student = StudentInfo(
                student_id=str(assignment.student_id),
                name=student_name or f"Student {assignment.student_id}",
                class_name=assignment.class_name,
            )

            notification = service.create_low_grade_alert(
                teacher=teacher,
                student=student,
                assignment_id=str(assignment.id),
                assignment_title=assignment.title,
                subject=assignment.subject,
                score=score,
                max_score=assignment.max_score,
                threshold=settings.LOW_GRADE_THRESHOLD,
                feedback=feedback,
                areas_for_improvement=improvements,
            )

            results = await service.send(notification)

            for result in results:
                if result.success:
                    logger.info(
                        f"Low grade alert sent to {teacher_email} "
                        f"({len([e for e in teacher_email.split(',') if e.strip()])} recipient(s))"
                    )
                else:
                    logger.warning(f"Low grade alert failed: {result.error_message}")

        except Exception as e:
            logger.error(f"Failed to send low grade notification: {e}")
