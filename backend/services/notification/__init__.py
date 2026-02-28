"""
Notification service package.

Supported channels:
- Email (SMTP) - teacher escalations (with link to Google Chat space) + low grade alerts
- Google Chat (Chat API / Webhook fallback) - daily summaries to students in the shared space
- Zalo - daily summaries to parents (stores messages for clone UI)

Usage:
    from services.notification import get_notification_service, TeacherInfo, StudentInfo

    service = get_notification_service()

    # Teacher escalation (confidence_score is optional)
    notification = service.create_teacher_escalation(
        teacher=TeacherInfo(teacher_id="t1", name="Teacher", email="teacher@school.edu"),
        student=StudentInfo(student_id="s1", name="Student"),
        question="What is quantum physics?",
        reason="Topic not in knowledge base",
    )
    results = await service.send(notification)

    # Low grade alert
    notification = service.create_low_grade_alert(
        teacher=teacher,
        student=student,
        assignment_id="hw-001",
        assignment_title="Fractions",
        subject="Mathematics",
        score=5.0,
        max_score=10.0,
        threshold=7.0,
    )
    results = await service.send(notification)
"""

from .models import (
    Notification,
    NotificationChannel,
    NotificationResult,
    NotificationStatus,
    NotificationType,
    EscalationContext,
    LowGradeContext,
    LessonSummary,
    DailySummaryContext,
    SubmissionGradedContext,
    StudentInfo,
    TeacherInfo,
    ParentInfo,
)
from .base import BaseNotifier
from .email_notifier import EmailNotifier
from .google_chat_notifier import GoogleChatNotifier
from .zalo_notifier import ZaloNotifier
from .notification_service import NotificationService, get_notification_service


__all__ = [
    # Models
    "Notification",
    "NotificationChannel",
    "NotificationResult",
    "NotificationStatus",
    "NotificationType",
    "EscalationContext",
    "LowGradeContext",
    "LessonSummary",
    "DailySummaryContext",
    "SubmissionGradedContext",
    "StudentInfo",
    "TeacherInfo",
    "ParentInfo",
    # Notifiers
    "BaseNotifier",
    "EmailNotifier",
    "GoogleChatNotifier",
    "ZaloNotifier",
    # Service
    "NotificationService",
    "get_notification_service",
]
