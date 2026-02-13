"""
Notification data models for the NotificationService.

This module defines Pydantic models for different notification types:
- Teacher escalations (when AI cannot answer student questions)
- Low grade alerts (when student score falls below threshold)
- Daily summaries (end-of-day lesson + homework recap for students/parents)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications supported by the system."""
    TEACHER_ESCALATION = "teacher_escalation"
    LOW_GRADE_ALERT = "low_grade_alert"
    DAILY_SUMMARY = "daily_summary"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    GOOGLE_CHAT = "google_chat"
    ZALO = "zalo"
    ALL = "all"


class NotificationStatus(str, Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class StudentInfo(BaseModel):
    """Information about the student related to the notification."""
    student_id: str
    name: str
    grade: Optional[str] = None
    class_name: Optional[str] = None
    email: Optional[str] = None


class ParentInfo(BaseModel):
    """Information about the parent to notify (for Zalo/daily summary)."""
    parent_id: Optional[str] = None
    name: Optional[str] = None
    zalo_id: Optional[str] = None
    phone: Optional[str] = None


class TeacherInfo(BaseModel):
    """Information about the teacher to notify."""
    teacher_id: str
    name: str
    email: str
    google_chat_webhook: Optional[str] = None


class EscalationContext(BaseModel):
    """Context for a teacher escalation notification."""
    question: str
    ai_response: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    # Link to Google Chat group where teacher can respond directly
    google_chat_link: Optional[str] = None


class LowGradeContext(BaseModel):
    """Context for a low grade notification sent to teacher."""
    assignment_id: str
    assignment_title: str
    subject: str
    score: float
    max_score: float = 10.0
    threshold: float = 7.0
    feedback: Optional[str] = None
    areas_for_improvement: list[str] = Field(default_factory=list)


class LessonSummary(BaseModel):
    """Summary of a single lesson/subject for daily notification."""
    subject: str
    content: str
    homework: Optional[str] = None
    homework_link: Optional[str] = None
    mandatory_assignment: Optional[str] = None
    mandatory_assignment_deadline: Optional[str] = None
    mandatory_assignment_link: Optional[str] = None
    reading_materials_link: Optional[str] = None


class DailySummaryContext(BaseModel):
    """Context for the end-of-day summary notification."""
    date: str  # e.g. "2026-01-12"
    lessons: list[LessonSummary] = Field(default_factory=list)
    general_notes: Optional[str] = None


class Notification(BaseModel):
    """Base notification model."""
    notification_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    notification_type: NotificationType
    channel: NotificationChannel = NotificationChannel.EMAIL

    # Recipients (use depending on notification type)
    teacher: Optional[TeacherInfo] = None
    student: Optional[StudentInfo] = None
    parent: Optional[ParentInfo] = None

    # Content
    title: str
    message: str

    # Context (optional, based on notification type)
    escalation_context: Optional[EscalationContext] = None
    low_grade_context: Optional[LowGradeContext] = None
    daily_summary_context: Optional[DailySummaryContext] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    status: NotificationStatus = NotificationStatus.PENDING

    # Delivery tracking
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class NotificationResult(BaseModel):
    """Result of sending a notification."""
    notification_id: str
    success: bool
    channel: NotificationChannel
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Channel-specific details
    email_message_id: Optional[str] = None
    google_chat_thread_id: Optional[str] = None
