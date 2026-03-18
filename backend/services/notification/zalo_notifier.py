"""
Zalo notification implementation.

This module sends daily summary notifications to the Zalo clone UI
by storing plain-text messages in an in-memory store. The frontend
polls GET /api/zalo/messages to fetch and display them.

In production, this would be replaced with real Zalo OA API calls.
For this demo, it simulates Zalo delivery by making the message
available to our clone UI.

The notification message already contains the full AI-generated text.
The notifier stores it as-is for the frontend to render.

Used for: Daily summaries sent to parents via Zalo.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from utils.logger import logger

from .base import BaseNotifier
from .models import (
    Notification,
    NotificationResult,
    NotificationChannel,
)


# In-memory message store (shared with the API route)
# Each entry: {"id": str, "sender": str, "text": str, "time": str, "is_ai": bool}
# In production this would be a database table
zalo_message_store: list[dict] = []


class ZaloNotifier(BaseNotifier):
    """
    Zalo notification channel for the clone UI.

    Instead of calling the real Zalo OA API, this stores plain-text
    messages in zalo_message_store so the frontend can poll them
    via GET /api/zalo/messages.

    The `notification.message` field is expected to contain the full
    AI-generated text ready for display.
    """

    def __init__(
        self,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)

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
        new messages and render them as plain text.
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
        Format notification into a plain-text dict for the frontend.

        The frontend renders this as a Zalo chat bubble showing the
        full AI-generated message text.
        """
        now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

        return {
            "id": notification.notification_id,
            "sender": "AI Assistant",
            "text": notification.message,
            "time": now.strftime("%H:%M"),
            "is_ai": True,
        }
