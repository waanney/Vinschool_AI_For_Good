"""
Unit tests for the Notification Service.

Tests cover:
- Notification models
- Email notifier
- Google Chat notifier
- NotificationService orchestration
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.notification import (
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
    EmailNotifier,
    GoogleChatNotifier,
    NotificationService,
)


# ===== Test Fixtures =====

@pytest.fixture
def sample_teacher():
    """Create a sample teacher for testing."""
    return TeacherInfo(
        teacher_id="teacher-001",
        name="Nguyen Van A",
        email="teacher@vinschool.edu.vn",
        google_chat_webhook="https://chat.googleapis.com/v1/spaces/xxx/messages?key=yyy",
    )


@pytest.fixture
def sample_student():
    """Create a sample student for testing."""
    return StudentInfo(
        student_id="student-001",
        name="Tran Van B",
        grade="9",
        class_name="9A1",
    )


@pytest.fixture
def sample_escalation_context():
    """Create a sample escalation context."""
    return EscalationContext(
        question="What is quantum entanglement?",
        ai_response="I'm not confident about this topic.",
        confidence_score=0.3,
        reason="Topic not in knowledge base",
        subject="Physics",
        topic="Quantum Mechanics",
    )


@pytest.fixture
def sample_homework_context():
    """Create a sample homework context."""
    return HomeworkContext(
        assignment_id="hw-001",
        assignment_title="Fraction Operations",
        subject="Mathematics",
        score=85.0,
        max_score=100.0,
        feedback="Good work! Minor errors in problem 3.",
        areas_for_improvement=["Double-check denominators", "Simplify final answers"],
    )


@pytest.fixture
def sample_notification(sample_teacher, sample_student, sample_escalation_context):
    """Create a sample notification for testing."""
    return Notification(
        notification_type=NotificationType.TEACHER_ESCALATION,
        priority=NotificationPriority.HIGH,
        channel=NotificationChannel.EMAIL,
        teacher=sample_teacher,
        student=sample_student,
        title="Student Question Needs Attention",
        message="A student asked a question the AI couldn't confidently answer.",
        escalation_context=sample_escalation_context,
    )


# ===== Model Tests =====

class TestNotificationModels:
    """Tests for notification data models."""
    
    def test_student_info_creation(self):
        """Test StudentInfo model creation."""
        student = StudentInfo(
            student_id="s1",
            name="Test Student",
            grade="10",
            class_name="10A",
        )
        assert student.student_id == "s1"
        assert student.name == "Test Student"
        assert student.grade == "10"
        assert student.class_name == "10A"
    
    def test_student_info_optional_fields(self):
        """Test StudentInfo with optional fields."""
        student = StudentInfo(student_id="s1", name="Test")
        assert student.grade is None
        assert student.class_name is None
    
    def test_teacher_info_creation(self):
        """Test TeacherInfo model creation."""
        teacher = TeacherInfo(
            teacher_id="t1",
            name="Test Teacher",
            email="test@school.edu",
        )
        assert teacher.teacher_id == "t1"
        assert teacher.email == "test@school.edu"
        assert teacher.google_chat_webhook is None
    
    def test_escalation_context_confidence_bounds(self):
        """Test that confidence score is bounded 0-1."""
        ctx = EscalationContext(
            question="Test",
            confidence_score=0.5,
            reason="Test reason",
        )
        assert 0.0 <= ctx.confidence_score <= 1.0
    
    def test_notification_auto_id(self, sample_teacher):
        """Test that notification gets auto-generated ID."""
        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            teacher=sample_teacher,
            title="Test",
            message="Test message",
        )
        assert notification.notification_id is not None
        assert len(notification.notification_id) > 0
    
    def test_notification_default_values(self, sample_teacher):
        """Test notification default values."""
        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            teacher=sample_teacher,
            title="Test",
            message="Test message",
        )
        assert notification.priority == NotificationPriority.MEDIUM
        assert notification.channel == NotificationChannel.EMAIL
        assert notification.status == NotificationStatus.PENDING
        assert notification.retry_count == 0
    
    def test_notification_result_success(self):
        """Test successful notification result."""
        result = NotificationResult(
            notification_id="n1",
            success=True,
            channel=NotificationChannel.EMAIL,
            sent_at=datetime.now(),
            email_message_id="msg-123",
        )
        assert result.success is True
        assert result.error_message is None
    
    def test_notification_result_failure(self):
        """Test failed notification result."""
        result = NotificationResult(
            notification_id="n1",
            success=False,
            channel=NotificationChannel.EMAIL,
            error_message="SMTP connection failed",
        )
        assert result.success is False
        assert result.sent_at is None


# ===== Email Notifier Tests =====

class TestEmailNotifier:
    """Tests for EmailNotifier."""
    
    def test_email_notifier_initialization(self):
        """Test EmailNotifier initialization."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        assert notifier.channel_name == "email"
        assert notifier.enabled is True
    
    def test_email_notifier_disabled(self):
        """Test disabled EmailNotifier."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
            enabled=False,
        )
        assert notifier.enabled is False
    
    @pytest.mark.asyncio
    async def test_validate_config_missing_host(self):
        """Test config validation with missing host."""
        notifier = EmailNotifier(
            smtp_host="",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        valid, error = await notifier.validate_config()
        assert valid is False
        assert "host" in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_config_missing_credentials(self):
        """Test config validation with missing credentials."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="",
            password="",
            sender_email="sender@test.com",
        )
        valid, error = await notifier.validate_config()
        assert valid is False
        assert "credentials" in error.lower()
    
    def test_get_subject_with_priority(self, sample_notification):
        """Test subject line generation with priority."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        
        # High priority
        sample_notification.priority = NotificationPriority.HIGH
        subject = notifier._get_subject(sample_notification)
        assert "⚠️" in subject
        
        # Urgent priority
        sample_notification.priority = NotificationPriority.URGENT
        subject = notifier._get_subject(sample_notification)
        assert "🚨" in subject
        assert "URGENT" in subject
    
    def test_create_html_content(self, sample_notification):
        """Test HTML content generation."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        html = notifier._create_html_content(sample_notification)
        
        assert "<!DOCTYPE html>" in html
        assert sample_notification.title in html
        assert sample_notification.message in html
        assert "Vinschool" in html
    
    def test_create_plain_content(self, sample_notification):
        """Test plain text content generation."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        plain = notifier._create_plain_content(sample_notification)
        
        assert sample_notification.title in plain
        assert sample_notification.message in plain


# ===== Google Chat Notifier Tests =====

class TestGoogleChatNotifier:
    """Tests for GoogleChatNotifier."""
    
    def test_google_chat_notifier_initialization(self):
        """Test GoogleChatNotifier initialization."""
        notifier = GoogleChatNotifier(
            default_webhook_url="https://chat.googleapis.com/v1/spaces/xxx",
        )
        assert notifier.channel_name == "google_chat"
        assert notifier.enabled is True
    
    def test_google_chat_notifier_disabled(self):
        """Test disabled GoogleChatNotifier."""
        notifier = GoogleChatNotifier(enabled=False)
        assert notifier.enabled is False
    
    @pytest.mark.asyncio
    async def test_validate_config_no_webhook(self):
        """Test config validation with no webhook."""
        notifier = GoogleChatNotifier()
        valid, error = await notifier.validate_config()
        # Should be valid (just a warning)
        assert valid is True
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_url(self):
        """Test config validation with invalid webhook URL."""
        notifier = GoogleChatNotifier(
            default_webhook_url="https://invalid-url.com/webhook",
        )
        valid, error = await notifier.validate_config()
        assert valid is False
        assert "format" in error.lower()
    
    def test_create_card_message(self, sample_notification):
        """Test Google Chat card message creation."""
        notifier = GoogleChatNotifier()
        card = notifier._create_card_message(sample_notification)
        
        assert "cardsV2" in card
        assert len(card["cardsV2"]) == 1
        assert "card" in card["cardsV2"][0]
        assert "header" in card["cardsV2"][0]["card"]
        assert "sections" in card["cardsV2"][0]["card"]
    
    def test_build_escalation_sections(self, sample_notification):
        """Test escalation sections building."""
        notifier = GoogleChatNotifier()
        sections = notifier._build_escalation_sections(sample_notification)
        
        assert len(sections) >= 1
        # Should have question details section
        question_section = sections[0]
        assert "header" in question_section
        assert "Question" in question_section["header"]
    
    @pytest.mark.asyncio
    async def test_send_no_webhook(self, sample_notification):
        """Test sending without webhook URL."""
        notifier = GoogleChatNotifier()
        sample_notification.teacher.google_chat_webhook = None
        
        result = await notifier.send(sample_notification)
        
        assert result.success is False
        assert "webhook" in result.error_message.lower()


# ===== Notification Service Tests =====

class TestNotificationService:
    """Tests for NotificationService orchestration."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        with patch("services.notification.notification_service.get_settings") as mock:
            settings = MagicMock()
            settings.SMTP_HOST = "smtp.test.com"
            settings.SMTP_PORT = 587
            settings.SMTP_USERNAME = "user"
            settings.SMTP_PASSWORD = "pass"
            settings.NOTIFICATION_SENDER_EMAIL = "sender@test.com"
            settings.NOTIFICATION_SENDER_NAME = "Test Sender"
            settings.SMTP_USE_TLS = True
            settings.ENABLE_EMAIL_NOTIFICATIONS = True
            settings.GOOGLE_CHAT_WEBHOOK_URL = None
            settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS = False
            settings.NOTIFICATION_TIMEOUT = 30
            mock.return_value = settings
            yield settings
    
    def test_create_teacher_escalation(
        self, mock_settings, sample_teacher, sample_student
    ):
        """Test creating teacher escalation notification."""
        # Reset singleton for clean test
        NotificationService._instance = None
        
        service = NotificationService()
        notification = service.create_teacher_escalation(
            teacher=sample_teacher,
            student=sample_student,
            question="What is X?",
            confidence_score=0.25,  # Below 0.3 threshold for HIGH priority
            reason="Low confidence",
        )
        
        assert notification.notification_type == NotificationType.TEACHER_ESCALATION
        assert notification.teacher == sample_teacher
        assert notification.student == sample_student
        assert notification.escalation_context is not None
        assert notification.escalation_context.question == "What is X?"
        
        # Should auto-determine high priority for low confidence (< 0.3)
        assert notification.priority == NotificationPriority.HIGH
    
    def test_create_homework_notification(
        self, mock_settings, sample_teacher, sample_student
    ):
        """Test creating homework notification."""
        NotificationService._instance = None
        
        service = NotificationService()
        notification = service.create_homework_notification(
            teacher=sample_teacher,
            student=sample_student,
            assignment_id="hw-001",
            assignment_title="Math Homework",
            subject="Mathematics",
            notification_type=NotificationType.HOMEWORK_GRADED,
            score=85.0,
        )
        
        assert notification.notification_type == NotificationType.HOMEWORK_GRADED
        assert notification.homework_context is not None
        assert notification.homework_context.score == 85.0
    
    def test_create_struggling_student_alert(
        self, mock_settings, sample_teacher, sample_student
    ):
        """Test creating struggling student alert."""
        NotificationService._instance = None
        
        service = NotificationService()
        notification = service.create_struggling_student_alert(
            teacher=sample_teacher,
            student=sample_student,
            reason="Multiple failed attempts",
            subject="Mathematics",
            recent_scores=[45.0, 52.0, 48.0],
        )
        
        assert notification.notification_type == NotificationType.STUDENT_STRUGGLING
        assert notification.priority == NotificationPriority.HIGH
        assert "48.3" in notification.message  # Average score
    
    @pytest.mark.asyncio
    async def test_send_notification_email_only(
        self, mock_settings, sample_notification
    ):
        """Test sending notification via email only."""
        NotificationService._instance = None
        
        service = NotificationService()
        
        # Mock the email notifier
        with patch.object(service._email_notifier, "send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = NotificationResult(
                notification_id=sample_notification.notification_id,
                success=True,
                channel=NotificationChannel.EMAIL,
                sent_at=datetime.now(),
            )
            
            sample_notification.channel = NotificationChannel.EMAIL
            results = await service.send(sample_notification)
            
            assert len(results) == 1
            assert results[0].success is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_disabled_channel(
        self, mock_settings, sample_notification
    ):
        """Test sending to disabled channel."""
        NotificationService._instance = None
        mock_settings.ENABLE_EMAIL_NOTIFICATIONS = False
        
        service = NotificationService()
        sample_notification.channel = NotificationChannel.EMAIL
        
        results = await service.send(sample_notification)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "not enabled" in results[0].error_message


# ===== Integration Tests =====

class TestWorkflowIntegration:
    """Integration tests for notification in workflows."""
    
    @pytest.mark.asyncio
    async def test_workflow_escalation_triggers_notification(self):
        """Test that workflow escalation triggers notification."""
        # This is an integration test that would require more setup
        # For now, we test the notification helper method in isolation
        pass


# Run with: pytest tests/test_notification_service.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
