"""
Notification service package.

This package provides multi-channel notification capabilities for the
Vinschool AI Educational Support System.

Supported channels:
- Email (SMTP)
- Google Chat (Webhooks)

Usage:
    from services.notification import get_notification_service, TeacherInfo, StudentInfo
    
    service = get_notification_service()
    
    # Create and send a teacher escalation
    notification = service.create_teacher_escalation(
        teacher=TeacherInfo(teacher_id="t1", name="Teacher", email="teacher@school.edu"),
        student=StudentInfo(student_id="s1", name="Student", grade="9"),
        question="What is quantum physics?",
        confidence_score=0.3,
        reason="Topic not in knowledge base",
    )
    
    results = await service.send(notification)
"""

from .models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationResult,
    NotificationStatus,
    NotificationType,
    EscalationContext,
    HomeworkContext,
    StudentInfo,
    TeacherInfo,
)
from .base import BaseNotifier
from .email_notifier import EmailNotifier
from .google_chat_notifier import GoogleChatNotifier
from .notification_service import NotificationService, get_notification_service


__all__ = [
    # Models
    "Notification",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationResult",
    "NotificationStatus",
    "NotificationType",
    "EscalationContext",
    "HomeworkContext",
    "StudentInfo",
    "TeacherInfo",
    # Notifiers
    "BaseNotifier",
    "EmailNotifier",
    "GoogleChatNotifier",
    # Service
    "NotificationService",
    "get_notification_service",
]
