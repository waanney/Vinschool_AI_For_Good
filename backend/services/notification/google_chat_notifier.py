"""
Google Chat notification implementation.

This module provides Google Chat notification functionality using webhooks.
Supports card-based messages for rich notification content.
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
    NotificationPriority,
)

# Using global logger from utils.logger


class GoogleChatNotifier(BaseNotifier):
    """
    Google Chat notification channel using webhooks.

    Sends formatted card messages to Google Chat spaces/rooms.
    Uses the Google Chat incoming webhook API.
    """

    def __init__(
        self,
        default_webhook_url: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True,
    ):
        """
        Initialize the Google Chat notifier.

        Args:
            default_webhook_url: Default webhook URL for notifications.
            timeout: HTTP request timeout in seconds.
            enabled: Whether Google Chat notifications are enabled.
        """
        super().__init__(enabled=enabled)
        self.default_webhook_url = default_webhook_url
        self.timeout = timeout

    @property
    def channel_name(self) -> str:
        return "google_chat"

    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate Google Chat configuration."""
        # At least default webhook or per-teacher webhooks should be available
        if not self.default_webhook_url:
            logger.warning("No default Google Chat webhook configured. "
                          "Will rely on per-teacher webhook URLs.")
            return True, None  # Not an error, but a warning

        # Validate webhook URL format
        if not self.default_webhook_url.startswith("https://chat.googleapis.com/"):
            return False, "Invalid Google Chat webhook URL format"

        return True, None

    async def send(self, notification: Notification) -> NotificationResult:
        """Send Google Chat notification."""
        # Determine webhook URL (teacher-specific or default)
        webhook_url = notification.teacher.google_chat_webhook or self.default_webhook_url

        if not webhook_url:
            error_msg = f"No Google Chat webhook URL for teacher {notification.teacher.name}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=notification.channel,
                error_message=error_msg,
            )

        try:
            # Create card message
            card_message = self._create_card_message(notification)

            # Send to Google Chat
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=card_message,
                    timeout=self.timeout,
                )
                response.raise_for_status()

            # Parse response for thread info
            response_data = response.json()
            thread_id = response_data.get("thread", {}).get("name")

            logger.info(f"Google Chat message sent successfully for teacher {notification.teacher.name}")

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=notification.channel,
                sent_at=datetime.now(),
                google_chat_thread_id=thread_id,
            )

        except httpx.TimeoutException:
            error_msg = f"Timeout sending Google Chat notification"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=notification.channel,
                error_message=error_msg,
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error sending Google Chat notification: {e.response.status_code}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=notification.channel,
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Failed to send Google Chat notification: {str(e)}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=notification.channel,
                error_message=error_msg,
            )

    def _create_card_message(self, notification: Notification) -> dict:
        """
        Create a Google Chat card message.

        Uses the Cards v2 format for rich message formatting.
        See: https://developers.google.com/chat/api/reference/rest/v1/cards
        """
        # Priority-based styling
        header_colors = {
            NotificationPriority.LOW: "#4CAF50",
            NotificationPriority.MEDIUM: "#2196F3",
            NotificationPriority.HIGH: "#FF9800",
            NotificationPriority.URGENT: "#F44336",
        }

        priority_icons = {
            NotificationPriority.LOW: "BOOKMARK",
            NotificationPriority.MEDIUM: "DESCRIPTION",
            NotificationPriority.HIGH: "STAR",
            NotificationPriority.URGENT: "URGENT",
        }

        # Build sections based on notification type
        sections = self._build_sections(notification)

        card = {
            "cardsV2": [
                {
                    "cardId": notification.notification_id,
                    "card": {
                        "header": {
                            "title": notification.title,
                            "subtitle": f"Priority: {notification.priority.value.upper()}",
                            "imageUrl": self._get_notification_icon(notification.notification_type),
                            "imageType": "CIRCLE",
                        },
                        "sections": sections,
                    }
                }
            ]
        }

        return card

    def _build_sections(self, notification: Notification) -> list[dict]:
        """Build card sections based on notification type."""
        sections = []

        # Main message section
        sections.append({
            "header": "Details",
            "widgets": [
                {
                    "textParagraph": {
                        "text": notification.message
                    }
                }
            ]
        })

        # Notification type-specific sections
        if notification.notification_type == NotificationType.TEACHER_ESCALATION:
            sections.extend(self._build_escalation_sections(notification))
        elif notification.notification_type in [
            NotificationType.HOMEWORK_SUBMITTED,
            NotificationType.HOMEWORK_GRADED,
        ]:
            sections.extend(self._build_homework_sections(notification))

        # Student info section (if available)
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

        # Footer section
        sections.append({
            "widgets": [
                {
                    "textParagraph": {
                        "text": f"<i>Sent at {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}</i>"
                    }
                }
            ]
        })

        return sections

    def _build_escalation_sections(self, notification: Notification) -> list[dict]:
        """Build sections for escalation notifications."""
        if not notification.escalation_context:
            return []

        ctx = notification.escalation_context

        sections = [
            {
                "header": "Question Details",
                "widgets": [
                    {
                        "textParagraph": {
                            "text": f"<b>Question:</b> \"{ctx.question}\""
                        }
                    },
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
                    {
                        "textParagraph": {
                            "text": f"<b>Reason for Escalation:</b> {ctx.reason}"
                        }
                    }
                ]
            }
        ]

        if ctx.ai_response:
            sections.append({
                "header": "AI Response Given",
                "collapsible": True,
                "widgets": [
                    {
                        "textParagraph": {
                            "text": ctx.ai_response
                        }
                    }
                ]
            })

        return sections

    def _build_homework_sections(self, notification: Notification) -> list[dict]:
        """Build sections for homework notifications."""
        if not notification.homework_context:
            return []

        ctx = notification.homework_context

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
            }
        ]

        if ctx.score is not None:
            score_percent = (ctx.score / ctx.max_score) * 100
            widgets.append({
                "decoratedText": {
                    "topLabel": "Score",
                    "text": f"{ctx.score:.1f}/{ctx.max_score:.1f} ({score_percent:.1f}%)",
                    "startIcon": {"knownIcon": "STAR"}
                }
            })

        sections = [{"header": "Assignment Details", "widgets": widgets}]

        if ctx.feedback:
            sections.append({
                "header": "Feedback",
                "collapsible": True,
                "widgets": [
                    {
                        "textParagraph": {
                            "text": ctx.feedback
                        }
                    }
                ]
            })

        if ctx.areas_for_improvement:
            improvement_text = "\n".join([f"• {area}" for area in ctx.areas_for_improvement])
            sections.append({
                "header": "Areas for Improvement",
                "collapsible": True,
                "widgets": [
                    {
                        "textParagraph": {
                            "text": improvement_text
                        }
                    }
                ]
            })

        return sections

    def _get_notification_icon(self, notification_type: NotificationType) -> str:
        """Get an appropriate icon URL for the notification type."""
        # Using Google's Material Design icons
        icons = {
            NotificationType.TEACHER_ESCALATION: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/priority_high/default/48px.svg",
            NotificationType.HOMEWORK_SUBMITTED: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/assignment/default/48px.svg",
            NotificationType.HOMEWORK_GRADED: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/grading/default/48px.svg",
            NotificationType.LOW_CONFIDENCE_ANSWER: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/help/default/48px.svg",
            NotificationType.STUDENT_STRUGGLING: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/warning/default/48px.svg",
            NotificationType.DAILY_SUMMARY: "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/summarize/default/48px.svg",
        }
        return icons.get(
            notification_type,
            "https://fonts.gstatic.com/s/i/short-term/release/materialsymbolsoutlined/notifications/default/48px.svg"
        )
