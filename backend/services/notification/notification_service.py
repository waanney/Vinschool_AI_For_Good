"""
Main NotificationService that orchestrates all notification channels.

This module provides the high-level API for sending notifications,
managing channels, and creating notifications from workflow events.
"""

import asyncio
from datetime import datetime
from typing import Optional

from config.settings import get_settings
from utils.logger import logger

from .base import BaseNotifier
from .email_notifier import EmailNotifier
from .google_chat_notifier import GoogleChatNotifier
from .models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationResult,
    NotificationStatus,
    NotificationType,
    EscalationContext,
    HomeworkContext,
    StudentInfo,
    TeacherInfo,
)

# Using global logger from utils.logger


class NotificationService:
    """
    Main notification service that orchestrates all notification channels.
    
    This service provides:
    - Multi-channel notification delivery (email, Google Chat)
    - Automatic channel selection based on notification priority
    - Factory methods for creating notifications from workflow events
    - Retry logic for failed notifications
    """
    
    _instance: Optional["NotificationService"] = None
    
    def __new__(cls) -> "NotificationService":
        """Singleton pattern for NotificationService."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the notification service with configured channels."""
        if self._initialized:
            return
        
        settings = get_settings()
        
        # Initialize email notifier
        self._email_notifier = EmailNotifier(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            sender_email=settings.NOTIFICATION_SENDER_EMAIL,
            sender_name=settings.NOTIFICATION_SENDER_NAME,
            use_tls=settings.SMTP_USE_TLS,
            enabled=settings.ENABLE_EMAIL_NOTIFICATIONS,
        )
        
        # Initialize Google Chat notifier
        self._google_chat_notifier = GoogleChatNotifier(
            default_webhook_url=settings.GOOGLE_CHAT_WEBHOOK_URL,
            timeout=settings.NOTIFICATION_TIMEOUT,
            enabled=settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS,
        )
        
        self._notifiers: dict[NotificationChannel, BaseNotifier] = {
            NotificationChannel.EMAIL: self._email_notifier,
            NotificationChannel.GOOGLE_CHAT: self._google_chat_notifier,
        }
        
        self._initialized = True
        logger.info("NotificationService initialized")
    
    @property
    def email_enabled(self) -> bool:
        """Check if email notifications are enabled."""
        return self._email_notifier.enabled
    
    @property
    def google_chat_enabled(self) -> bool:
        """Check if Google Chat notifications are enabled."""
        return self._google_chat_notifier.enabled
    
    async def send(self, notification: Notification) -> list[NotificationResult]:
        """
        Send a notification through the configured channel(s).
        
        Args:
            notification: The notification to send.
            
        Returns:
            List of NotificationResults (one per channel if using BOTH).
        """
        results = []
        
        if notification.channel == NotificationChannel.BOTH:
            # Send through all enabled channels
            tasks = []
            for channel, notifier in self._notifiers.items():
                if notifier.enabled:
                    tasks.append(notifier.send(notification))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Convert exceptions to failed results
                results = [
                    r if isinstance(r, NotificationResult) else NotificationResult(
                        notification_id=notification.notification_id,
                        success=False,
                        channel=notification.channel,
                        error_message=str(r),
                    )
                    for r in results
                ]
        else:
            # Send through specific channel
            notifier = self._notifiers.get(notification.channel)
            if notifier and notifier.enabled:
                result = await notifier.send(notification)
                results.append(result)
            else:
                results.append(NotificationResult(
                    notification_id=notification.notification_id,
                    success=False,
                    channel=notification.channel,
                    error_message=f"Channel {notification.channel.value} is not enabled",
                ))
        
        # Update notification status
        all_success = all(r.success for r in results)
        notification.status = NotificationStatus.SENT if all_success else NotificationStatus.FAILED
        notification.sent_at = datetime.now() if all_success else None
        
        # Log results
        for result in results:
            if result.success:
                logger.info(f"Notification {notification.notification_id} sent via {result.channel.value}")
            else:
                logger.error(f"Notification {notification.notification_id} failed via {result.channel.value}: {result.error_message}")
        
        return results
    
    async def send_with_retry(
        self,
        notification: Notification,
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> list[NotificationResult]:
        """
        Send notification with retry logic for failed attempts.
        
        Args:
            notification: The notification to send.
            max_retries: Maximum number of retry attempts.
            delay: Delay between retries in seconds.
            
        Returns:
            List of final NotificationResults.
        """
        results = await self.send(notification)
        
        for i in range(max_retries):
            # Check if any channel failed
            failed_channels = [r for r in results if not r.success]
            if not failed_channels:
                break
            
            notification.retry_count = i + 1
            logger.warning(f"Retrying notification {notification.notification_id} (attempt {i + 1}/{max_retries})")
            
            await asyncio.sleep(delay * (i + 1))  # Exponential backoff
            
            # Retry failed channels
            retry_results = await self.send(notification)
            
            # Update results
            for retry_result in retry_results:
                # Find and replace the corresponding result
                for j, original in enumerate(results):
                    if original.channel == retry_result.channel:
                        if retry_result.success:
                            results[j] = retry_result
                        break
        
        return results
    
    # ===== Factory methods for creating notifications =====
    
    def create_teacher_escalation(
        self,
        teacher: TeacherInfo,
        student: StudentInfo,
        question: str,
        confidence_score: float,
        reason: str,
        ai_response: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        priority: Optional[NotificationPriority] = None,
        channel: NotificationChannel = NotificationChannel.BOTH,
    ) -> Notification:
        """
        Create a teacher escalation notification.
        
        This is used when the AI cannot confidently answer a student's question
        and needs to escalate to the teacher.
        
        Args:
            teacher: Teacher to notify.
            student: Student who asked the question.
            question: The question that couldn't be answered.
            confidence_score: AI's confidence score (0-1).
            reason: Reason for escalation.
            ai_response: The response AI gave (if any).
            subject: Subject area of the question.
            topic: Specific topic of the question.
            priority: Notification priority (auto-determined if None).
            channel: Notification channel(s) to use.
            
        Returns:
            Configured Notification object.
        """
        # Auto-determine priority based on confidence
        if priority is None:
            if confidence_score < 0.3:
                priority = NotificationPriority.HIGH
            elif confidence_score < 0.5:
                priority = NotificationPriority.MEDIUM
            else:
                priority = NotificationPriority.LOW
        
        return Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            priority=priority,
            channel=channel,
            teacher=teacher,
            student=student,
            title=f"Student Question Needs Your Attention",
            message=f"Student {student.name} asked a question that the AI couldn't confidently answer. "
                   f"Please review and provide guidance.",
            escalation_context=EscalationContext(
                question=question,
                ai_response=ai_response,
                confidence_score=confidence_score,
                reason=reason,
                subject=subject,
                topic=topic,
            ),
        )
    
    def create_homework_notification(
        self,
        teacher: TeacherInfo,
        student: StudentInfo,
        assignment_id: str,
        assignment_title: str,
        subject: str,
        notification_type: NotificationType,
        score: Optional[float] = None,
        max_score: float = 100.0,
        feedback: Optional[str] = None,
        areas_for_improvement: Optional[list[str]] = None,
        priority: NotificationPriority = NotificationPriority.LOW,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> Notification:
        """
        Create a homework-related notification.
        
        Args:
            teacher: Teacher to notify.
            student: Student who submitted/received grade.
            assignment_id: Assignment identifier.
            assignment_title: Human-readable assignment title.
            subject: Subject of the assignment.
            notification_type: HOMEWORK_SUBMITTED or HOMEWORK_GRADED.
            score: Student's score (for graded notifications).
            max_score: Maximum possible score.
            feedback: Grading feedback.
            areas_for_improvement: List of areas to improve.
            priority: Notification priority.
            channel: Notification channel(s) to use.
            
        Returns:
            Configured Notification object.
        """
        if notification_type == NotificationType.HOMEWORK_SUBMITTED:
            title = f"Homework Submitted: {assignment_title}"
            message = f"Student {student.name} has submitted their homework for {assignment_title}."
        else:
            title = f"Homework Graded: {assignment_title}"
            message = f"Homework for {student.name} has been graded."
        
        return Notification(
            notification_type=notification_type,
            priority=priority,
            channel=channel,
            teacher=teacher,
            student=student,
            title=title,
            message=message,
            homework_context=HomeworkContext(
                assignment_id=assignment_id,
                assignment_title=assignment_title,
                subject=subject,
                score=score,
                max_score=max_score,
                feedback=feedback,
                areas_for_improvement=areas_for_improvement or [],
            ),
        )
    
    def create_struggling_student_alert(
        self,
        teacher: TeacherInfo,
        student: StudentInfo,
        reason: str,
        subject: Optional[str] = None,
        recent_scores: Optional[list[float]] = None,
        channel: NotificationChannel = NotificationChannel.BOTH,
    ) -> Notification:
        """
        Create an alert for a struggling student.
        
        This is used to proactively notify teachers when a student
        appears to be struggling based on patterns in their work.
        
        Args:
            teacher: Teacher to notify.
            student: Student who is struggling.
            reason: Explanation of why the student appears to be struggling.
            subject: Subject area where struggling is observed.
            recent_scores: Recent scores that indicate struggling.
            channel: Notification channel(s) to use.
            
        Returns:
            Configured Notification object.
        """
        score_info = ""
        if recent_scores:
            avg_score = sum(recent_scores) / len(recent_scores)
            score_info = f" Average recent score: {avg_score:.1f}%."
        
        return Notification(
            notification_type=NotificationType.STUDENT_STRUGGLING,
            priority=NotificationPriority.HIGH,
            channel=channel,
            teacher=teacher,
            student=student,
            title=f"Student May Need Additional Support",
            message=f"Based on recent activity, {student.name} may be struggling "
                   f"with {subject or 'their coursework'}. {reason}{score_info}",
        )


# Global instance getter
def get_notification_service() -> NotificationService:
    """Get the singleton NotificationService instance."""
    return NotificationService()
