"""
Zalo notification implementation (stub).

This module provides a stub for Zalo notifications.
The actual Zalo OA API integration will be implemented once the
team provides the Zalo Official Account credentials and API access.

Used for: Daily summaries sent to parents' Zalo groups.
"""

from datetime import datetime
from typing import Optional

from utils.logger import logger

from .base import BaseNotifier
from .models import (
    Notification,
    NotificationResult,
    NotificationChannel,
)


class ZaloNotifier(BaseNotifier):
    """
    Zalo notification channel (stub).

    Will send daily summary messages to parent Zalo groups.
    Currently a placeholder - actual implementation requires:
    - Zalo Official Account (OA) credentials
    - Zalo OA API access token
    - Parent Zalo user IDs or group IDs

    For demo: the UI will be faked on the frontend side.
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
        if not self.oa_access_token:
            return False, "Zalo OA access token is not configured"
        return True, None

    async def send(self, notification: Notification) -> NotificationResult:
        """
        Send Zalo notification (stub).

        Currently logs the notification that would be sent.
        Actual implementation will use Zalo OA API.
        """
        logger.info(
            f"[ZALO STUB] Would send notification to parent: "
            f"type={notification.notification_type.value}, "
            f"title={notification.title}"
        )

        # For now, return success to not block the flow
        # In production, this will actually call Zalo OA API
        return NotificationResult(
            notification_id=notification.notification_id,
            success=True,
            channel=NotificationChannel.ZALO,
            sent_at=datetime.now(),
            error_message="[STUB] Zalo integration not yet implemented",
        )

    def format_daily_summary(self, notification: Notification) -> str:
        """
        Format daily summary for Zalo (parent-facing).

        The Zalo message should be more formal than Google Chat
        since it's addressed to parents. Example format:

        Bo me cac con than men,
        Co Hana xin gui noi dung hoc tap 2 buoi hom nay cua cac con a:
        Mon Science:
        ...
        Mon Toan:
        ...
        Mon Tieng Anh:
        ...
        Kinh mong bo me nhac nho cac con hoan thanh bai tap day du giup co a.
        Cam on bo me cac con da doc tin a!
        """
        if not notification.daily_summary_context:
            return notification.message

        ctx = notification.daily_summary_context
        lines = []

        # Parent-friendly greeting
        lines.append("Bo me cac con than men,")
        lines.append(notification.message)
        lines.append("")

        for lesson in ctx.lessons:
            lines.append(f"Mon {lesson.subject}:")
            lines.append(lesson.content)
            if lesson.homework:
                lines.append(lesson.homework)
            if lesson.homework_link:
                lines.append(lesson.homework_link)
            if lesson.mandatory_assignment:
                lines.append(lesson.mandatory_assignment)
            if lesson.mandatory_assignment_link:
                lines.append(lesson.mandatory_assignment_link)
            lines.append("")

        lines.append("Kinh mong bo me nhac nho cac con hoan thanh bai tap day du giup co a.")
        lines.append("Cam on bo me cac con da doc tin a!")

        return "\n".join(lines)
