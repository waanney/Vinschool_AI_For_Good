"""
Google Chat notification implementation.

This module provides Google Chat notification functionality using webhooks.
Used for:
- Teacher escalations (send to teacher's webhook)
- Daily summaries (send to student class group webhook)
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
    Google Chat notification channel using webhooks.

    Sends formatted card messages to Google Chat spaces/rooms.
    """

    def __init__(
        self,
        default_webhook_url: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.default_webhook_url = default_webhook_url
        self.timeout = timeout

    @property
    def channel_name(self) -> str:
        return "google_chat"

    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Google Chat configuration."""
        if not self.default_webhook_url:
            logger.warning("No default Google Chat webhook configured. "
                          "Will rely on per-teacher webhook URLs.")
            return True, None

        if not self.default_webhook_url.startswith("https://chat.googleapis.com/"):
            return False, "Invalid Google Chat webhook URL format"

        return True, None

    async def send(self, notification: Notification) -> NotificationResult:
        """Send Google Chat notification."""
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
            if notification.notification_type == NotificationType.DAILY_SUMMARY:
                message = self._create_daily_summary_message(notification)
            else:
                message = self._create_card_message(notification)

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
        # For teacher escalations, use teacher-specific webhook or default
        if notification.teacher and notification.teacher.google_chat_webhook:
            return notification.teacher.google_chat_webhook
        return self.default_webhook_url

    def _create_card_message(self, notification: Notification) -> dict:
        """Create a Google Chat card message for escalation/alert notifications."""
        sections = self._build_sections(notification)

        return {
            "cardsV2": [
                {
                    "cardId": notification.notification_id,
                    "card": {
                        "header": {
                            "title": f"{self._get_notification_emoji(notification.notification_type)} {notification.title}",
                            "subtitle": notification.notification_type.value.replace("_", " ").title(),
                        },
                        "sections": sections,
                    }
                }
            ]
        }

    def _create_daily_summary_message(self, notification: Notification) -> dict:
        """
        Create a plain text message for daily summary (student/parent facing).

        The notification.message already contains the full formatted text
        (greeting + AI summary content + closing) assembled by the
        NotificationService factory methods.
        """
        return {"text": notification.message}

    def _build_sections(self, notification: Notification) -> list[dict]:
        """Build card sections based on notification type."""
        sections = []

        # Main message
        sections.append({
            "header": "Details",
            "widgets": [{"textParagraph": {"text": notification.message}}]
        })

        if notification.notification_type == NotificationType.TEACHER_ESCALATION:
            sections.extend(self._build_escalation_sections(notification))
        elif notification.notification_type == NotificationType.LOW_GRADE_ALERT:
            sections.extend(self._build_low_grade_sections(notification))

        # Student info
        if notification.student:
            sections.append({
                "header": "Student Information",
                "widgets": [
                    {
                        "decoratedText": {
                            "topLabel": "Student Name",
                            "text": notification.student.name,
                            "startIcon": {"knownIcon": "PERSON"}
                        }
                    },
                    {
                        "decoratedText": {
                            "topLabel": "Grade / Class",
                            "text": f"{notification.student.grade or 'N/A'} / {notification.student.class_name or 'N/A'}",
                            "startIcon": {"knownIcon": "BOOKMARK"}
                        }
                    }
                ]
            })

        # Timestamp
        sections.append({
            "widgets": [{
                "textParagraph": {
                    "text": f"<i>Sent at {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}</i>"
                }
            }]
        })

        return sections

    def _build_escalation_sections(self, notification: Notification) -> list[dict]:
        """Build sections for escalation notifications."""
        if not notification.escalation_context:
            return []

        ctx = notification.escalation_context

        widgets = [
            {"textParagraph": {"text": f"<b>Question:</b> \"{ctx.question}\""}},
            {
                "decoratedText": {
                    "topLabel": "AI Confidence",
                    "text": f"{ctx.confidence_score:.1%}",
                    "startIcon": {"knownIcon": "CONFIRMATION_NUMBER_ICON"}
                }
            },
            {
                "decoratedText": {
                    "topLabel": "Subject",
                    "text": ctx.subject or "Not specified",
                    "startIcon": {"knownIcon": "DESCRIPTION"}
                }
            },
            {"textParagraph": {"text": f"<b>Reason:</b> {ctx.reason}"}},
        ]

        sections = [{"header": "Question Details", "widgets": widgets}]

        if ctx.ai_response:
            sections.append({
                "header": "AI Response Given",
                "collapsible": True,
                "widgets": [{"textParagraph": {"text": ctx.ai_response}}]
            })

        if ctx.google_chat_link:
            sections.append({
                "header": "Respond to Student",
                "widgets": [{
                    "buttonList": {
                        "buttons": [{
                            "text": "Open Chat with Student",
                            "onClick": {"openLink": {"url": ctx.google_chat_link}}
                        }]
                    }
                }]
            })

        return sections

    def _build_low_grade_sections(self, notification: Notification) -> list[dict]:
        """Build sections for low grade notifications."""
        if not notification.low_grade_context:
            return []

        ctx = notification.low_grade_context

        widgets = [
            {
                "decoratedText": {
                    "topLabel": "Assignment",
                    "text": ctx.assignment_title,
                    "startIcon": {"knownIcon": "DESCRIPTION"}
                }
            },
            {
                "decoratedText": {
                    "topLabel": "Subject",
                    "text": ctx.subject,
                    "startIcon": {"knownIcon": "BOOKMARK"}
                }
            },
            {
                "decoratedText": {
                    "topLabel": "Score",
                    "text": f"{ctx.score:.1f}/{ctx.max_score:.1f} (threshold: {ctx.threshold:.1f})",
                    "startIcon": {"knownIcon": "STAR"}
                }
            },
        ]

        sections = [{"header": "Assignment Details", "widgets": widgets}]

        if ctx.feedback:
            sections.append({
                "header": "AI Feedback",
                "collapsible": True,
                "widgets": [{"textParagraph": {"text": ctx.feedback}}]
            })

        if ctx.areas_for_improvement:
            text = "\n".join([f"- {area}" for area in ctx.areas_for_improvement])
            sections.append({
                "header": "Areas for Improvement",
                "collapsible": True,
                "widgets": [{"textParagraph": {"text": text}}]
            })

        return sections

    def _get_notification_emoji(self, notification_type: NotificationType) -> str:
        """Get an emoji for the notification type."""
        emojis = {
            NotificationType.TEACHER_ESCALATION: "❓",
            NotificationType.LOW_GRADE_ALERT: "⚠️",
            NotificationType.DAILY_SUMMARY: "📋",
        }
        return emojis.get(notification_type, "🔔")
