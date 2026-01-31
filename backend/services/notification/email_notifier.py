"""
Email notification implementation.

This module provides email notification functionality using SMTP.
Supports HTML formatting for rich notification content.
"""

import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from utils.logger import logger

from .base import BaseNotifier
from .models import (
    Notification,
    NotificationResult,
    NotificationType,
    NotificationPriority,
)

# Using global logger from utils.logger


class EmailNotifier(BaseNotifier):
    """
    Email notification channel using SMTP.

    Sends formatted HTML emails to teachers for various notification types.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender_email: str,
        sender_name: str = "Vinschool AI Assistant",
        use_tls: bool = True,
        enabled: bool = True,
    ):
        """
        Initialize the email notifier.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            username: SMTP authentication username.
            password: SMTP authentication password.
            sender_email: Email address to send from.
            sender_name: Display name for the sender.
            use_tls: Whether to use TLS encryption.
            enabled: Whether email notifications are enabled.
        """
        super().__init__(enabled=enabled)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.use_tls = use_tls

    @property
    def channel_name(self) -> str:
        return "email"

    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate SMTP configuration."""
        if not self.smtp_host:
            return False, "SMTP host is not configured"
        if not self.smtp_port:
            return False, "SMTP port is not configured"
        if not self.username or not self.password:
            return False, "SMTP credentials are not configured"
        if not self.sender_email:
            return False, "Sender email is not configured"

        # Test connection
        try:
            context = ssl.create_default_context()
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.username, self.password)
            else:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.username, self.password)
            return True, None
        except Exception as e:
            return False, f"Failed to connect to SMTP server: {str(e)}"

    async def send(self, notification: Notification) -> NotificationResult:
        """Send email notification."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._get_subject(notification)
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = notification.teacher.email

            # Create HTML content
            html_content = self._create_html_content(notification)
            plain_content = self._create_plain_content(notification)

            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            context = ssl.create_default_context()

            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.username, self.password)
                    message_id = server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.username, self.password)
                    message_id = server.send_message(msg)

            logger.info(f"Email sent successfully to {notification.teacher.email}")

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=notification.channel,
                sent_at=datetime.now(),
                email_message_id=str(message_id) if message_id else None,
            )

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)

            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=notification.channel,
                error_message=error_msg,
            )

    def _get_subject(self, notification: Notification) -> str:
        """Generate email subject based on notification type and priority."""
        priority_prefix = ""
        if notification.priority == NotificationPriority.URGENT:
            priority_prefix = "🚨 URGENT: "
        elif notification.priority == NotificationPriority.HIGH:
            priority_prefix = "⚠️ "

        return f"{priority_prefix}{notification.title}"

    def _create_html_content(self, notification: Notification) -> str:
        """Create HTML email content."""
        # Priority-based header color
        header_colors = {
            NotificationPriority.LOW: "#4CAF50",
            NotificationPriority.MEDIUM: "#2196F3",
            NotificationPriority.HIGH: "#FF9800",
            NotificationPriority.URGENT: "#F44336",
        }
        header_color = header_colors.get(notification.priority, "#2196F3")

        # Build context-specific content
        context_html = ""

        if notification.notification_type == NotificationType.TEACHER_ESCALATION:
            context_html = self._build_escalation_html(notification)
        elif notification.notification_type in [
            NotificationType.HOMEWORK_SUBMITTED,
            NotificationType.HOMEWORK_GRADED,
        ]:
            context_html = self._build_homework_html(notification)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {header_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }}
                .info-box {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 4px; border-left: 4px solid {header_color}; }}
                .label {{ font-weight: bold; color: #666; }}
                .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: {header_color}; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">{notification.title}</h2>
                </div>
                <div class="content">
                    <p>{notification.message}</p>
                    {context_html}
                </div>
                <div class="footer">
                    <p><strong>This is an automated notification. Please do not reply to this email.</strong></p>
                    <p style="margin-top: 10px;">Vinschool AI Educational Support System</p>
                    <p style="font-size: 11px; color: #999;">To respond to this notification, please log in to the Vinschool platform.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_escalation_html(self, notification: Notification) -> str:
        """Build HTML for escalation context."""
        if not notification.escalation_context:
            return ""

        ctx = notification.escalation_context

        student_info = ""
        if notification.student:
            student_info = f"""
            <div class="info-box">
                <p><span class="label">Student:</span> {notification.student.name}</p>
                <p><span class="label">Grade:</span> {notification.student.grade or 'N/A'}</p>
                <p><span class="label">Class:</span> {notification.student.class_name or 'N/A'}</p>
            </div>
            """

        return f"""
        <div class="info-box">
            <p><span class="label">Question Asked:</span></p>
            <p style="background: #fff; padding: 10px; border-radius: 4px;">"{ctx.question}"</p>
        </div>

        {student_info}

        <div class="info-box">
            <p><span class="label">AI Confidence Score:</span> {ctx.confidence_score:.1%}</p>
            <p><span class="label">Subject:</span> {ctx.subject or 'Not specified'}</p>
            <p><span class="label">Topic:</span> {ctx.topic or 'Not specified'}</p>
            <p><span class="label">Reason for Escalation:</span> {ctx.reason}</p>
        </div>

        {f'<div class="info-box"><p><span class="label">AI Response Given:</span></p><p>{ctx.ai_response}</p></div>' if ctx.ai_response else ''}
        """

    def _build_homework_html(self, notification: Notification) -> str:
        """Build HTML for homework context."""
        if not notification.homework_context:
            return ""

        ctx = notification.homework_context

        score_html = ""
        if ctx.score is not None:
            score_percent = (ctx.score / ctx.max_score) * 100
            score_color = "#4CAF50" if score_percent >= 70 else "#FF9800" if score_percent >= 50 else "#F44336"
            score_html = f"""
            <div class="info-box">
                <p><span class="label">Score:</span>
                   <span style="color: {score_color}; font-weight: bold;">{ctx.score:.1f}/{ctx.max_score:.1f} ({score_percent:.1f}%)</span>
                </p>
            </div>
            """

        improvements_html = ""
        if ctx.areas_for_improvement:
            improvements_list = "".join([f"<li>{area}</li>" for area in ctx.areas_for_improvement])
            improvements_html = f"""
            <div class="info-box">
                <p><span class="label">Areas for Improvement:</span></p>
                <ul>{improvements_list}</ul>
            </div>
            """

        return f"""
        <div class="info-box">
            <p><span class="label">Assignment:</span> {ctx.assignment_title}</p>
            <p><span class="label">Subject:</span> {ctx.subject}</p>
        </div>

        {score_html}

        {f'<div class="info-box"><p><span class="label">Feedback:</span></p><p>{ctx.feedback}</p></div>' if ctx.feedback else ''}

        {improvements_html}
        """

    def _create_plain_content(self, notification: Notification) -> str:
        """Create plain text email content as fallback."""
        lines = [
            notification.title,
            "=" * len(notification.title),
            "",
            notification.message,
            "",
        ]

        if notification.escalation_context:
            ctx = notification.escalation_context
            lines.extend([
                "Question Details:",
                f"  Question: {ctx.question}",
                f"  Confidence: {ctx.confidence_score:.1%}",
                f"  Reason: {ctx.reason}",
                "",
            ])

        if notification.homework_context:
            ctx = notification.homework_context
            lines.extend([
                "Assignment Details:",
                f"  Title: {ctx.assignment_title}",
                f"  Subject: {ctx.subject}",
                f"  Score: {ctx.score}/{ctx.max_score}" if ctx.score else "",
                "",
            ])

        lines.extend([
            "---",
            "",
            "This is an automated notification. Please do not reply to this email.",
            "To respond, please log in to the Vinschool platform.",
            "",
            "Vinschool AI Educational Support System",
        ])

        return "\n".join(lines)
