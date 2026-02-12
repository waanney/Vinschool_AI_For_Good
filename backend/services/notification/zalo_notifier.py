"""
Zalo notification implementation.

This module sends daily summary notifications to the Zalo clone UI
by storing structured messages in an in-memory store. The frontend
polls GET /api/zalo/messages to fetch and display them.

In production, this would be replaced with real Zalo OA API calls.
For this demo, it simulates Zalo delivery by making the message
available to our clone UI.

Used for: Daily summaries sent to parents via Zalo.
"""

from datetime import datetime
from typing import Optional

from utils.logger import logger

from .base import BaseNotifier
from .models import (
    Notification,
    NotificationResult,
    NotificationChannel,
    NotificationType,
)


# In-memory message store (shared with the API route)
# In production this would be a database table
zalo_message_store: list[dict] = []


class ZaloNotifier(BaseNotifier):
    """
    Zalo notification channel for the clone UI.

    Instead of calling the real Zalo OA API, this stores formatted
    messages in zalo_message_store so the frontend can poll them
    via GET /api/zalo/messages.
    """

    def __init__(
        self,
        oa_access_token: Optional[str] = None,
        enabled: bool = False,
    ):
        super().__init__(enabled=enabled)
        self.oa_access_token = oa_access_token

    @property
    def channel_name(self) -> str:
        return "zalo"

    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Zalo configuration."""
        # For demo mode, always valid since we use the in-memory store
        return True, None

    async def send(self, notification: Notification) -> NotificationResult:
        """
        Send Zalo notification by storing it in the message store.

        The Zalo clone UI polls GET /api/zalo/messages to pick up
        new messages and render them.
        """
        try:
            message_data = self._format_message(notification)
            zalo_message_store.append(message_data)

            logger.info(
                f"[ZALO] Message stored for UI: "
                f"type={notification.notification_type.value}, "
                f"title={notification.title}, "
                f"id={notification.notification_id}"
            )

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=NotificationChannel.ZALO,
                sent_at=datetime.now(),
            )

        except Exception as e:
            error_msg = f"Failed to store Zalo message: {str(e)}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.ZALO,
                error_message=error_msg,
            )

    def _format_message(self, notification: Notification) -> dict:
        """
        Format notification into a structured dict for the frontend.

        The frontend renders this as a Zalo chat bubble with:
        - Greeting ("Bố mẹ các con thân mến,")
        - Intro line
        - Per-subject lesson details
        - Closing line
        """
        now = datetime.now()

        if notification.notification_type == NotificationType.DAILY_SUMMARY:
            return self._format_daily_summary(notification, now)

        # Fallback for other notification types
        return {
            "id": notification.notification_id,
            "sender": "AI Assistant",
            "greeting": "",
            "intro": notification.message,
            "lessons": [],
            "closing": "",
            "time": now.strftime("%H:%M"),
            "is_ai": True,
        }

    def _format_daily_summary(self, notification: Notification, now: datetime) -> dict:
        """Format a daily summary notification for parents."""
        lessons = []
        closing = "Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ. Cảm ơn bố mẹ!"

        if notification.daily_summary_context:
            ctx = notification.daily_summary_context

            for lesson in ctx.lessons:
                lessons.append({
                    "subject": lesson.subject,
                    "content": lesson.content,
                    "homework": lesson.homework,
                    "homework_link": lesson.homework_link,
                    "mandatory_assignment": lesson.mandatory_assignment,
                    "mandatory_assignment_deadline": lesson.mandatory_assignment_deadline,
                    "mandatory_assignment_link": lesson.mandatory_assignment_link,
                    "reading_materials_link": lesson.reading_materials_link,
                })

            if ctx.general_notes:
                closing = ctx.general_notes

        return {
            "id": notification.notification_id,
            "sender": "AI Assistant",
            "greeting": "Bố mẹ các con thân mến,",
            "intro": notification.message,
            "lessons": lessons,
            "closing": closing,
            "time": now.strftime("%H:%M"),
            "is_ai": True,
        }
