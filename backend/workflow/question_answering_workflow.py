"""
Question Answering Workflow.
Handles student questions with automatic routing and escalation.
"""

from typing import Optional
from datetime import datetime

from agents.teaching_assistant.agent import (
    TeachingAssistantAgent,
    QuestionContext,
    AnswerResponse,
)
from config import settings
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


class QuestionAnsweringWorkflow:
    """
    Workflow for handling student questions.

    Flow:
    1. Student submits question
    2. AI searches knowledge base
    3. If confident → provide answer
    4. If not confident → escalate to teacher + send notification
    5. Log interaction for analytics
    """

    def __init__(self):
        self.teaching_agent = TeachingAssistantAgent()
        self.escalation_threshold = settings.teacher_escalation_threshold

    async def handle_question(
        self,
        student_id: str,
        question: str,
        grade: int,
        subject: str,
        class_name: Optional[str] = None,
        student_name: Optional[str] = None,
        teacher_id: Optional[str] = None,
        teacher_name: Optional[str] = None,
        teacher_email: Optional[str] = None,
        teacher_webhook: Optional[str] = None,
    ) -> dict:
        """
        Handle a student question end-to-end.

        Args:
            student_id: Student ID
            question: Question text
            grade: Student grade level
            subject: Subject area
            class_name: Optional class identifier
            student_name: Student name (for notifications)
            teacher_id: Teacher ID (for notifications)
            teacher_name: Teacher name (for notifications)
            teacher_email: Teacher email (for notifications)
            teacher_webhook: Teacher's Google Chat webhook URL

        Returns:
            Dictionary with answer or escalation info
        """
        logger.info(f"Handling question from student {student_id}: {question[:100]}")

        result = {
            "student_id": student_id,
            "question": question,
            "timestamp": datetime.utcnow().isoformat(),
            "answer": None,
            "confidence": 0.0,
            "escalated": False,
            "escalation_reason": None,
            "sources": [],
        }

        try:
            # Create question context
            context = QuestionContext(
                question=question,
                student_id=student_id,
                grade=grade,
                subject=subject,
                class_name=class_name,
            )

            # Get answer from teaching assistant
            response: AnswerResponse = await self.teaching_agent.answer_question(context)

            # Update result
            result["answer"] = response.answer
            result["confidence"] = response.confidence
            result["sources"] = response.sources

            # Check if escalation is needed
            if response.escalate_to_teacher or response.confidence < self.escalation_threshold:
                result["escalated"] = True
                result["escalation_reason"] = response.reasoning

                # Tell the student their question is being escalated
                result["answer"] = (
                    "Câu hỏi này cô chưa có đủ thông tin để trả lời. "
                    "Cô sẽ chuyển câu hỏi sang cho giáo viên để giải đáp sớm nhất cho con."
                )

                logger.info(
                    f"Question escalated to teacher. "
                    f"Confidence: {response.confidence:.2f}, "
                    f"Reason: {response.reasoning}"
                )

                # Send notification to teacher if info is provided
                await self._notify_teacher_escalation(
                    question=question,
                    answer=response.answer,
                    confidence=response.confidence,
                    reason=response.reasoning,
                    subject=subject,
                    student_id=student_id,
                    student_name=student_name,
                    grade=str(grade),
                    class_name=class_name,
                    teacher_id=teacher_id,
                    teacher_name=teacher_name,
                    teacher_email=teacher_email,
                    teacher_webhook=teacher_webhook,
                )
            else:
                logger.info(
                    f"Question answered successfully. "
                    f"Confidence: {response.confidence:.2f}"
                )

        except Exception as e:
            logger.error(f"Error handling question: {e}")
            result["escalated"] = True
            result["escalation_reason"] = f"Error occurred: {str(e)}"
            result["answer"] = "Xin lỗi, đã có lỗi xảy ra. Câu hỏi của bạn đã được chuyển đến giáo viên."

        return result

    async def get_answer_for_teacher_review(
        self,
        student_id: str,
        question: str,
        grade: int,
        subject: str,
    ) -> dict:
        """
        Get AI-generated answer for teacher to review before sending to student.
        Used when teacher wants to verify AI response.
        """
        context = QuestionContext(
            question=question,
            student_id=student_id,
            grade=grade,
            subject=subject,
        )

        response = await self.teaching_agent.answer_question(context)

        return {
            "suggested_answer": response.answer,
            "confidence": response.confidence,
            "sources": response.sources,
            "reasoning": response.reasoning,
        }

    async def _notify_teacher_escalation(
        self,
        question: str,
        answer: str,
        confidence: float,
        reason: str,
        subject: str,
        student_id: str,
        student_name: Optional[str] = None,
        grade: Optional[str] = None,
        class_name: Optional[str] = None,
        teacher_id: Optional[str] = None,
        teacher_name: Optional[str] = None,
        teacher_email: Optional[str] = None,
        teacher_webhook: Optional[str] = None,
    ) -> None:
        """
        Send notification to teacher about escalated question.

        This is a helper method that handles notification creation and sending.
        If teacher info is not provided, notification is skipped.
        """
        # Check if we have enough info to send notification
        if not teacher_email and not teacher_webhook:
            logger.debug("No teacher contact info provided, skipping notification")
            return

        try:
            from services.notification import (
                TeacherInfo,
                StudentInfo,
                NotificationChannel,
            )

            service = _get_notification_service()

            if not service.email_enabled and not service.google_chat_enabled:
                logger.debug("All notification channels are disabled")
                return

            # Determine which channel to use
            if teacher_email and teacher_webhook:
                channel = NotificationChannel.ALL
            elif teacher_email:
                channel = NotificationChannel.EMAIL
            else:
                channel = NotificationChannel.GOOGLE_CHAT

            # Create teacher and student info
            teacher = TeacherInfo(
                teacher_id=teacher_id or "unknown",
                name=teacher_name or "Teacher",
                email=teacher_email or "",
                google_chat_webhook=teacher_webhook,
            )

            student = StudentInfo(
                student_id=student_id,
                name=student_name or f"Student {student_id}",
                grade=grade,
                class_name=class_name,
            )

            # Create and send notification
            notification = service.create_teacher_escalation(
                teacher=teacher,
                student=student,
                question=question,
                confidence_score=confidence,
                reason=reason,
                ai_response=answer,
                subject=subject,
                channel=channel,
            )

            results = await service.send(notification)

            # Log results
            for result in results:
                if result.success:
                    logger.info(f"Teacher notification sent via {result.channel.value}")
                else:
                    logger.warning(f"Teacher notification failed: {result.error_message}")

        except Exception as e:
            # Don't let notification failures break the workflow
            logger.error(f"Failed to send teacher notification: {e}")
