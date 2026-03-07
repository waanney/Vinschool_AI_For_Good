"""
Email notification implementation.

This module provides email notification functionality using SMTP.
Supports HTML formatting for rich notification content and multiple
recipients per notification (comma-separated in ``TeacherInfo.email``).
Used for: teacher escalations, low grade alerts.
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
    NotificationChannel,
)


class EmailNotifier(BaseNotifier):
    """
    Email notification channel using SMTP.

    Sends formatted HTML emails to teachers for escalations and low grade alerts.
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
        """Send email notification to one or more recipients.

        The teacher email field may contain a single address or a
        comma-separated list (e.g. ``"a@x.com, b@x.com"``).  All
        addresses are placed in the ``To`` header so every recipient
        receives the same email in a single SMTP transaction.
        """
        recipients = self._get_recipient_emails(notification)
        if not recipients:
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.EMAIL,
                error_message="No recipient email address found",
            )

        to_header = ", ".join(recipients)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.title
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = to_header

            html_content = self._create_html_content(notification)
            plain_content = self._create_plain_content(notification)

            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

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

            logger.info(f"Email sent successfully to {to_header} ({len(recipients)} recipient(s))")

            return NotificationResult(
                notification_id=notification.notification_id,
                success=True,
                channel=NotificationChannel.EMAIL,
                sent_at=datetime.now(),
                email_message_id=str(message_id) if message_id else None,
            )

        except Exception as e:
            error_msg = f"Failed to send email to {to_header}: {str(e)}"
            logger.error(error_msg)
            return NotificationResult(
                notification_id=notification.notification_id,
                success=False,
                channel=NotificationChannel.EMAIL,
                error_message=error_msg,
            )

    def _get_recipient_emails(self, notification: Notification) -> list[str]:
        """Parse recipient email(s) from the notification's teacher field.

        Supports a single address or a comma-separated list.
        Returns a deduplicated list of non-empty addresses.
        """
        if not notification.teacher or not notification.teacher.email:
            return []
        return list(dict.fromkeys(
            e.strip() for e in notification.teacher.email.split(",") if e.strip()
        ))

    def _create_html_content(self, notification: Notification) -> str:
        """Create HTML email content based on notification type."""
        context_html = ""

        if notification.notification_type == NotificationType.TEACHER_ESCALATION:
            context_html = self._build_escalation_html(notification)
        elif notification.notification_type == NotificationType.LOW_GRADE_ALERT:
            context_html = self._build_low_grade_html(notification)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }}
                .info-box {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 4px; border-left: 4px solid #2196F3; }}
                .label {{ font-weight: bold; color: #666; }}
                .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .score-low {{ color: #F44336; font-weight: bold; }}
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

        chat_link_html = ""
        if ctx.google_chat_link:
            chat_link_html = f"""
            <div class="info-box">
                <p><span class="label">Respond directly in Google Chat:</span></p>
                <a href="{ctx.google_chat_link}" class="button">Open Google Chat</a>
            </div>
            """

        return f"""
        <div class="info-box">
            <p><span class="label">Question Asked:</span></p>
            <p style="background: #fff; padding: 10px; border-radius: 4px;">"{ctx.question}"</p>
        </div>

        {student_info}

        <div class="info-box">
            <p><span class="label">AI Confidence Score:</span> {f'{ctx.confidence_score:.1%}' if ctx.confidence_score is not None else 'N/A'}</p>
            <p><span class="label">Subject:</span> {ctx.subject or 'Not specified'}</p>
            <p><span class="label">Reason for Escalation:</span> {ctx.reason}</p>
        </div>

        {f'<div class="info-box"><p><span class="label">AI Response Given:</span></p><p>{ctx.ai_response}</p></div>' if ctx.ai_response else ''}

        {chat_link_html}
        """

    def _build_low_grade_html(self, notification: Notification) -> str:
        """Build HTML for low grade context."""
        if not notification.low_grade_context:
            return ""

        ctx = notification.low_grade_context

        student_info = ""
        if notification.student:
            student_info = f"""
            <div class="info-box">
                <p><span class="label">Student:</span> {notification.student.name}</p>
                <p><span class="label">Grade:</span> {notification.student.grade or 'N/A'}</p>
                <p><span class="label">Class:</span> {notification.student.class_name or 'N/A'}</p>
            </div>
            """

        improvements_html = ""
        if ctx.areas_for_improvement:
            items = "".join([f"<li>{area}</li>" for area in ctx.areas_for_improvement])
            improvements_html = f"""
            <div class="info-box">
                <p><span class="label">Areas for Improvement:</span></p>
                <ul>{items}</ul>
            </div>
            """

        return f"""
        <div class="info-box">
            <p><span class="label">Assignment:</span> {ctx.assignment_title}</p>
            <p><span class="label">Subject:</span> {ctx.subject}</p>
            <p><span class="label">Score:</span>
               <span class="score-low">{ctx.score:.1f}/{ctx.max_score:.1f}</span>
               (threshold: {ctx.threshold:.1f})
            </p>
        </div>

        {student_info}

        {f'<div class="info-box"><p><span class="label">Nhận xét từ Cô Hana:</span></p><p>{ctx.feedback}</p></div>' if ctx.feedback else ''}

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
                f"  Confidence: {f'{ctx.confidence_score:.1%}' if ctx.confidence_score is not None else 'N/A'}",
                f"  Reason: {ctx.reason}",
                f"  Subject: {ctx.subject or 'N/A'}",
                "",
            ])
            if ctx.google_chat_link:
                lines.extend([
                    f"  Respond in Google Chat: {ctx.google_chat_link}",
                    "",
                ])

        if notification.low_grade_context:
            ctx = notification.low_grade_context
            lines.extend([
                "Assignment Details:",
                f"  Title: {ctx.assignment_title}",
                f"  Subject: {ctx.subject}",
                f"  Score: {ctx.score:.1f}/{ctx.max_score:.1f} (threshold: {ctx.threshold:.1f})",
                "",
            ])

        if notification.student:
            lines.extend([
                "Student:",
                f"  Name: {notification.student.name}",
                f"  Grade: {notification.student.grade or 'N/A'}",
                f"  Class: {notification.student.class_name or 'N/A'}",
                "",
            ])

        lines.extend([
            "---",
            "",
            "This is an automated notification. Please do not reply to this email.",
            "",
            "Vinschool AI Educational Support System",
        ])

        return "\n".join(lines)
