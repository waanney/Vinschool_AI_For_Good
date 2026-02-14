"""
Main NotificationService that orchestrates all notification channels.

This module provides the high-level API for sending notifications,
managing channels, and creating notifications from workflow events.

Notification types:
- Teacher Escalation: AI can't answer -> email + Google Chat to teacher
- Low Grade Alert: Student scores below threshold -> email to teacher
- Daily Summary: End-of-day recap -> Google Chat to students, Zalo to parents
"""

import asyncio
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from config.settings import get_settings
from utils.logger import logger

from .base import BaseNotifier
from .email_notifier import EmailNotifier
from .google_chat_notifier import GoogleChatNotifier
from .zalo_notifier import ZaloNotifier
from .models import (
    Notification,
    NotificationChannel,
    NotificationResult,
    NotificationStatus,
    NotificationType,
    EscalationContext,
    LowGradeContext,
    StudentInfo,
    TeacherInfo,
    ParentInfo,
)


class NotificationService:
    """
    Main notification service orchestrating email, Google Chat, and Zalo channels.

    Factory methods:
    - create_teacher_escalation() -> email + Google Chat to teacher
    - create_low_grade_alert() -> email to teacher
    - create_daily_summary_for_students() -> Google Chat to student group
    - create_daily_summary_for_parents() -> Zalo to parent group
    """

    _instance: Optional["NotificationService"] = None

    def __new__(cls) -> "NotificationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        settings = get_settings()

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

        self._google_chat_notifier = GoogleChatNotifier(
            default_webhook_url=settings.GOOGLE_CHAT_WEBHOOK_URL,
            timeout=settings.NOTIFICATION_TIMEOUT,
            enabled=settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS,
        )

        self._zalo_notifier = ZaloNotifier(
            oa_access_token=settings.ZALO_OA_ACCESS_TOKEN,
            enabled=settings.ENABLE_ZALO_NOTIFICATIONS,
        )

        self._notifiers: dict[NotificationChannel, BaseNotifier] = {
            NotificationChannel.EMAIL: self._email_notifier,
            NotificationChannel.GOOGLE_CHAT: self._google_chat_notifier,
            NotificationChannel.ZALO: self._zalo_notifier,
        }

        # Derive the Google Chat web link from webhook URL
        self._default_google_chat_link = self._extract_chat_link(
            settings.GOOGLE_CHAT_WEBHOOK_URL
        )

        self._initialized = True
        logger.info("NotificationService initialized")

    @property
    def email_enabled(self) -> bool:
        return self._email_notifier.enabled

    @property
    def google_chat_enabled(self) -> bool:
        return self._google_chat_notifier.enabled

    @property
    def zalo_enabled(self) -> bool:
        return self._zalo_notifier.enabled

    async def send(self, notification: Notification) -> list[NotificationResult]:
        """Send a notification through the configured channel(s)."""
        results = []

        if notification.channel == NotificationChannel.ALL:
            tasks = []
            for channel, notifier in self._notifiers.items():
                if notifier.enabled:
                    tasks.append(notifier.send(notification))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
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
        all_success = all(r.success for r in results) if results else False
        notification.status = NotificationStatus.SENT if all_success else NotificationStatus.FAILED
        notification.sent_at = datetime.now() if all_success else None

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
        """Send notification with retry logic for failed attempts."""
        results = await self.send(notification)

        for i in range(max_retries):
            failed_channels = [r for r in results if not r.success]
            if not failed_channels:
                break

            notification.retry_count = i + 1
            logger.warning(f"Retrying notification {notification.notification_id} (attempt {i + 1}/{max_retries})")

            await asyncio.sleep(delay * (i + 1))

            retry_results = await self.send(notification)
            for retry_result in retry_results:
                for j, original in enumerate(results):
                    if original.channel == retry_result.channel:
                        if retry_result.success:
                            results[j] = retry_result
                        break

        return results

    @staticmethod
    def _extract_chat_link(webhook_url: Optional[str]) -> Optional[str]:
        """
        Extract a user-accessible Google Chat link from a webhook URL.

        Webhook URL format:
          https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=...&token=...
        Derived web link:
          https://mail.google.com/chat/u/0/#chat/space/SPACE_ID
        """
        if not webhook_url:
            return None

        match = re.search(r'/spaces/([^/]+)/', webhook_url)
        if match:
            space_id = match.group(1)
            return f"https://mail.google.com/chat/u/0/#chat/space/{space_id}"
        return None

    # ===== Factory methods =====

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
        google_chat_link: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> Notification:
        """
        Create a teacher escalation notification.

        Sent when AI can't confidently answer a student question.
        Default channel is EMAIL (with optional Google Chat link embedded).
        """
        # Auto-derive Google Chat link from webhook URL if not explicitly provided
        resolved_chat_link = google_chat_link or self._default_google_chat_link

        return Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            channel=channel,
            teacher=teacher,
            student=student,
            title=f"{student.name} has a question for you",
            message=f"Student {student.name} asked a question that the AI couldn't confidently answer. "
                   f"Please review and provide guidance.",
            escalation_context=EscalationContext(
                question=question,
                ai_response=ai_response,
                confidence_score=confidence_score,
                reason=reason,
                subject=subject,
                topic=topic,
                google_chat_link=resolved_chat_link,
            ),
        )

    def create_low_grade_alert(
        self,
        teacher: TeacherInfo,
        student: StudentInfo,
        assignment_id: str,
        assignment_title: str,
        subject: str,
        score: float,
        max_score: float = 10.0,
        threshold: float = 7.0,
        feedback: Optional[str] = None,
        areas_for_improvement: Optional[list[str]] = None,
        channel: NotificationChannel = NotificationChannel.EMAIL,
    ) -> Notification:
        """
        Create a low grade alert notification for teacher.

        Sent when a student's graded score falls below the threshold.
        """
        return Notification(
            notification_type=NotificationType.LOW_GRADE_ALERT,
            channel=channel,
            teacher=teacher,
            student=student,
            title=f"Low Grade Alert: {student.name} - {assignment_title}",
            message=f"Student {student.name} scored {score:.1f}/{max_score:.1f} on {assignment_title}, "
                   f"which is below the threshold of {threshold:.1f}.",
            low_grade_context=LowGradeContext(
                assignment_id=assignment_id,
                assignment_title=assignment_title,
                subject=subject,
                score=score,
                max_score=max_score,
                threshold=threshold,
                feedback=feedback,
                areas_for_improvement=areas_for_improvement or [],
            ),
        )

    def create_daily_summary_for_students(
        self,
        student: StudentInfo,
        date: str,
        content: str,
        channel: NotificationChannel = NotificationChannel.GOOGLE_CHAT,
    ) -> Notification:
        """
        Create daily summary notification for students (Google Chat).

        Wraps the AI-generated plain text content with a student-facing
        greeting and closing template.

        Args:
            student: Student info
            date: Date string (e.g. "2026-01-12")
            content: AI-generated plain text summary
            channel: Delivery channel (default: Google Chat)
        """
        greeting = "Các con thân mến,\nCô Hana gửi lại nội dung buổi học ngày hôm nay của các con,\n\n"
        closing = "\n\nCác con nhớ hoàn thành bài tập đầy đủ nhé!"
        full_message = greeting + content + closing

        return Notification(
            notification_type=NotificationType.DAILY_SUMMARY,
            channel=channel,
            student=student,
            title=f"Daily Summary - {date}",
            message=full_message,
        )

    def create_daily_summary_for_parents(
        self,
        parent: ParentInfo,
        student: StudentInfo,
        date: str,
        content: str,
        channel: NotificationChannel = NotificationChannel.ZALO,
    ) -> Notification:
        """
        Create daily summary notification for parents (Zalo).

        Wraps the AI-generated plain text content with a parent-facing
        greeting and closing template (more formal tone).

        Args:
            parent: Parent info
            student: Student info
            date: Date string (e.g. "2026-01-12")
            content: AI-generated plain text summary
            channel: Delivery channel (default: Zalo)
        """
        greeting = "Bố mẹ các con thân mến,\nCô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:\n\n"
        closing = "\n\nKính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.\nCảm ơn bố mẹ các con đã đọc tin ạ!"
        full_message = greeting + content + closing

        return Notification(
            notification_type=NotificationType.DAILY_SUMMARY,
            channel=channel,
            student=student,
            parent=parent,
            title=f"Daily Summary - {date}",
            message=full_message,
        )


def get_notification_service() -> NotificationService:
    """Get the singleton NotificationService instance."""
    return NotificationService()
