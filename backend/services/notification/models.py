"""
Notification data models for the NotificationService.

This module defines Pydantic models for different notification types
including teacher escalations, homework alerts, and general notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications supported by the system."""
    TEACHER_ESCALATION = "teacher_escalation"
    HOMEWORK_SUBMITTED = "homework_submitted"
    HOMEWORK_GRADED = "homework_graded"
    LOW_CONFIDENCE_ANSWER = "low_confidence_answer"
    STUDENT_STRUGGLING = "student_struggling"
    DAILY_SUMMARY = "daily_summary"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    GOOGLE_CHAT = "google_chat"
    BOTH = "both"


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


class TeacherInfo(BaseModel):
    """Information about the teacher to notify."""
    teacher_id: str
    name: str
    email: str
    google_chat_webhook: Optional[str] = None


class EscalationContext(BaseModel):
    """Context for a teacher escalation notification."""
    question: str
    student_answer_attempt: Optional[str] = None
    ai_response: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    sources_checked: list[str] = Field(default_factory=list)


class HomeworkContext(BaseModel):
    """Context for homework-related notifications."""
    assignment_id: str
    assignment_title: str
    subject: str
    score: Optional[float] = None
    max_score: float = 100.0
    feedback: Optional[str] = None
    areas_for_improvement: list[str] = Field(default_factory=list)


class Notification(BaseModel):
    """Base notification model."""
    notification_id: str = Field(default_factory=lambda: str(__import__('uuid').uuid4()))
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel = NotificationChannel.EMAIL
    
    # Recipients
    teacher: TeacherInfo
    student: Optional[StudentInfo] = None
    
    # Content
    title: str
    message: str
    
    # Context (optional, based on notification type)
    escalation_context: Optional[EscalationContext] = None
    homework_context: Optional[HomeworkContext] = None
    
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
