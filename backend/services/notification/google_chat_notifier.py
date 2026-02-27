"""
Google Chat notification implementation.

This module provides Google Chat notification functionality via two modes:

1. **Chat API** (preferred): Uses a service-account to post messages through
   the Google Chat REST API. Requires ``GOOGLE_APPLICATION_CREDENTIALS``
   and ``GOOGLE_CHAT_SPACE_ID`` in ``.env``.  This is the same bot used
   by the Pub/Sub listener, so there's only **one** bot identity.

2. **Webhook** (legacy fallback): Uses an incoming webhook URL. Simpler
   but creates a second bot identity and doesn't support all features.

Used for:
- Daily summaries to students (plain-text message to the class Google Chat group)
"""

import json
from datetime import datetime
from typing import Optional

import httpx

from utils.logger import logger

from .base import BaseNotifier
from .models import (
    Notification,
    NotificationResult,
    NotificationType,
    NotificationChannel,
)


class GoogleChatNotifier(BaseNotifier):
    """
    Google Chat notification channel.

    Prefers the Chat API (service-account) when credentials and a space ID
    are provided, otherwise falls back to webhooks.
    """

    def __init__(
        self,
        default_webhook_url: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True,
        # Chat API mode (preferred)
        credentials_path: Optional[str] = None,
        default_space_id: Optional[str] = None,
    ):
        super().__init__(enabled=enabled)
        self.default_webhook_url = default_webhook_url
        self.timeout = timeout

        # Chat API fields
        self._credentials_path = credentials_path
        self._default_space_id = default_space_id
        self._credentials = None

        # Decide mode
        self._use_chat_api = bool(credentials_path and default_space_id)
        if self._use_chat_api:
            logger.info("[GCHAT-NOTIFIER] Using Chat API mode (service account)")
        elif default_webhook_url:
            logger.info("[GCHAT-NOTIFIER] Using webhook mode (legacy)")
        else:
            logger.info("[GCHAT-NOTIFIER] No Chat API or webhook configured")

    @property
    def channel_name(self) -> str:
        return "google_chat"

    # ===== Credential helpers (Chat API mode) =====

    def _load_credentials(self):
        """Load service-account credentials for the Chat API."""
        try:
            from google.oauth2 import service_account

            scopes = ["https://www.googleapis.com/auth/chat.bot"]
            self._credentials = service_account.Credentials.from_service_account_file(
                self._credentials_path, scopes=scopes
            )
            return self._credentials
        except ImportError:
            logger.error("[GCHAT-NOTIFIER] google-auth not installed")
            return None
        except Exception as e:
            logger.error(f"[GCHAT-NOTIFIER] Failed to load credentials: {e}")
            return None

    def _get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if not self._credentials:
            if not self._load_credentials():
                return None
        from google.auth.transport.requests import Request

        if self._credentials.expired or not self._credentials.token:
            self._credentials.refresh(Request())
        return self._credentials.token

    # ===== Config validation =====

    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Google Chat configuration."""
        if self._use_chat_api:
            import os
            if not os.path.exists(self._credentials_path):
                return False, f"Credentials file not found: {self._credentials_path}"
            return True, None

        if not self.default_webhook_url:
            logger.warning("No Chat API or webhook configured. "
                          "Will rely on per-teacher webhook URLs.")
            return True, None

        if not self.default_webhook_url.startswith("https://chat.googleapis.com/"):
            return False, "Invalid Google Chat webhook URL format"

        return True, None

    async def send(self, notification: Notification) -> NotificationResult:
        """Send Google Chat notification via Chat API or webhook."""
        if self._use_chat_api:
            return await self._send_via_chat_api(notification)
        return await self._send_via_webhook(notification)

    # ===== Chat API mode =====

    def _resolve_space(self, notification: Notification) -> Optional[str]:
        """Resolve the Google Chat space name for this notification.

        Priority: teacher.google_chat_webhook (if it looks like a space name),
        then the default_space_id.
        """
        # If the teacher field stores a space name (e.g. "spaces/xxx")
        if notification.teacher and notification.teacher.google_chat_webhook:
            val = notification.teacher.google_chat_webhook
            if val.startswith("spaces/"):
                return val
        return self._default_space_id

    async def _send_via_chat_api(self, notification: Notification) -> NotificationResult:
        """Send using the Google Chat REST API (service account)."""
        space = self._resolve_space(notification)
        if not space:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message="No Google Chat space ID available",
            )

        token = self._get_access_token()
        if not token:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message="Failed to get Chat API access token",
            )

        try:
            body = self._create_daily_summary_message(notification)

            url = f"https://chat.googleapis.com/v1/{space}/messages"

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                    timeout=self.timeout,
                )
                resp.raise_for_status()

            data = resp.json()
            thread_id = data.get("thread", {}).get("name")
            logger.info(f"Google Chat message sent via Chat API to {space}")

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=NotificationChannel.GOOGLE_CHAT,
                sent_at=datetime.now(),
                google_chat_thread_id=thread_id,
            )

        except httpx.TimeoutException:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message="Timeout sending via Chat API",
            )
        except httpx.HTTPStatusError as e:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=f"Chat API HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=f"Chat API error: {e}",
            )

    # ===== Webhook mode (legacy) =====

    async def _send_via_webhook(self, notification: Notification) -> NotificationResult:
        """Send using an incoming webhook URL (legacy fallback)."""
        webhook_url = self._get_webhook_url(notification)

        if not webhook_url:
            error_msg = "No Google Chat webhook URL available"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=error_msg,
            )

        try:
            # Choose message format based on notification type
            message = self._create_daily_summary_message(notification)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=message,
                    timeout=self.timeout,
                )
                response.raise_for_status()

            response_data = response.json()
            thread_id = response_data.get("thread", {}).get("name")

            logger.info(f"Google Chat message sent successfully")

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=NotificationChannel.GOOGLE_CHAT,
                sent_at=datetime.now(),
                google_chat_thread_id=thread_id,
            )

        except httpx.TimeoutException:
            error_msg = "Timeout sending Google Chat notification"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=error_msg,
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error sending Google Chat notification: {e.response.status_code}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Failed to send Google Chat notification: {str(e)}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.GOOGLE_CHAT,
                error_message=error_msg,
            )

    def _get_webhook_url(self, notification: Notification) -> Optional[str]:
        """Get the appropriate webhook URL for this notification."""
        if notification.teacher and notification.teacher.google_chat_webhook:
            return notification.teacher.google_chat_webhook
        return self.default_webhook_url

    def _create_daily_summary_message(self, notification: Notification) -> dict:
        """
        Create a plain text message for daily summary (student/parent facing).

        The notification.message already contains the full AI-generated text.
        """
        return {"text": notification.message}
