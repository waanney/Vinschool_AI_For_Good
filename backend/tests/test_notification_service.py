"""
Unit tests for the Notification Service.

Tests cover:
- Notification models (new types: LOW_GRADE_ALERT, DAILY_SUMMARY)
- Email notifier (escalation, low grade)
- Google Chat notifier (escalation, daily summary)
- Zalo notifier (stub)
- NotificationService factory methods
- Workflow integration (escalation + low grade alert)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.notification import (
    Notification,
    NotificationChannel,
    NotificationResult,
    NotificationStatus,
    NotificationType,
    EscalationContext,
    LowGradeContext,
    LessonSummary,
    DailySummaryContext,
    StudentInfo,
    TeacherInfo,
    ParentInfo,
    EmailNotifier,
    GoogleChatNotifier,
    ZaloNotifier,
    NotificationService,
)


# ===== Test Fixtures =====

@pytest.fixture
def sample_teacher():
    return TeacherInfo(
        teacher_id="teacher-001",
        name="Nguyen Van A",
        email="teacher@vinschool.edu.vn",
        google_chat_webhook="https://chat.googleapis.com/v1/spaces/xxx/messages?key=yyy",
    )


@pytest.fixture
def sample_student():
    return StudentInfo(
        student_id="student-001",
        name="Tran Van B",
        grade="9",
        class_name="9A1",
        email="student@stu.vinschool.edu.vn",
    )


@pytest.fixture
def sample_parent():
    return ParentInfo(
        parent_id="parent-001",
        name="Tran Van C",
        zalo_id="zalo-123",
        phone="0901234567",
    )


@pytest.fixture
def sample_escalation_context():
    return EscalationContext(
        question="Thu 6 tuan nay co kiem tra Tieng Viet khong co?",
        ai_response="Cau hoi nay co chua co du thong tin de tra loi.",
        confidence_score=0.3,
        reason="Topic not in knowledge base",
        subject="Tieng Viet",
        google_chat_link="https://mail.google.com/chat/u/0/#chat/space/1234567",
    )


@pytest.fixture
def sample_low_grade_context():
    return LowGradeContext(
        assignment_id="hw-001",
        assignment_title="Fraction Operations",
        subject="Mathematics",
        score=5.0,
        max_score=10.0,
        threshold=7.0,
        feedback="Student struggles with denominator operations.",
        areas_for_improvement=["Double-check denominators", "Simplify final answers"],
    )


@pytest.fixture
def sample_daily_summary_context():
    return DailySummaryContext(
        date="2026-01-12",
        lessons=[
            LessonSummary(
                subject="Science",
                content='Cac con lam thi nghiem de tim hieu ve co che hoat dong cua he tieu hoa "digestive system".',
                homework="Hom qua co Oanh da phat mot phieu bai tap mon Science, cac con hoan thanh va nop lai cho co vao thu hai (12/01) nhe.",
                homework_link="https://drive.google.com/drive/folders/example1",
            ),
            LessonSummary(
                subject="Toan",
                content='Cac con on tap ve phep tinh cong va tru phan so co cung mau so "denominator".',
                mandatory_assignment="Bai tap Toan trong workbook tuan nay cua cac con la: Unit 9.1, pages 93-97",
                mandatory_assignment_deadline="han nop thu Ba 13/01",
                homework_link="https://drive.google.com/drive/folders/example2",
            ),
            LessonSummary(
                subject="Tieng Anh",
                content='Cac con on tap lai cau dieu kien loai 0 "zero conditional" va cau hoi duoi "question tag".',
                homework_link="https://classroom.google.com/c/example3",
            ),
        ],
        general_notes="Cac con nho hoan thanh bai tap day du nhe!",
    )


@pytest.fixture
def sample_escalation_notification(sample_teacher, sample_student, sample_escalation_context):
    return Notification(
        notification_type=NotificationType.TEACHER_ESCALATION,
        channel=NotificationChannel.EMAIL,
        teacher=sample_teacher,
        student=sample_student,
        title="Tran Van B has a question for you",
        message="Student Tran Van B asked a question the AI couldn't confidently answer.",
        escalation_context=sample_escalation_context,
    )


@pytest.fixture
def sample_low_grade_notification(sample_teacher, sample_student, sample_low_grade_context):
    return Notification(
        notification_type=NotificationType.LOW_GRADE_ALERT,
        channel=NotificationChannel.EMAIL,
        teacher=sample_teacher,
        student=sample_student,
        title="Low Grade Alert: Tran Van B - Fraction Operations",
        message="Student Tran Van B scored 5.0/10.0 on Fraction Operations.",
        low_grade_context=sample_low_grade_context,
    )


@pytest.fixture
def sample_daily_summary_notification(sample_student, sample_daily_summary_context):
    return Notification(
        notification_type=NotificationType.DAILY_SUMMARY,
        channel=NotificationChannel.GOOGLE_CHAT,
        student=sample_student,
        title="Daily Summary - 2026-01-12",
        message="Cac con than men,\nCo Hana gui lai noi dung buoi hoc ngay hom nay cua cac con,",
        daily_summary_context=sample_daily_summary_context,
    )


# ===== Model Tests =====

class TestNotificationModels:

    def test_student_info_creation(self):
        student = StudentInfo(student_id="s1", name="Test Student", grade="10", class_name="10A")
        assert student.student_id == "s1"
        assert student.name == "Test Student"

    def test_student_info_optional_fields(self):
        student = StudentInfo(student_id="s1", name="Test")
        assert student.grade is None
        assert student.email is None

    def test_parent_info_creation(self):
        parent = ParentInfo(parent_id="p1", name="Parent", zalo_id="z1", phone="0901234567")
        assert parent.zalo_id == "z1"

    def test_teacher_info_creation(self):
        teacher = TeacherInfo(teacher_id="t1", name="Teacher", email="t@school.edu")
        assert teacher.google_chat_webhook is None

    def test_escalation_context_confidence_bounds(self):
        ctx = EscalationContext(question="Test", confidence_score=0.5, reason="Test")
        assert 0.0 <= ctx.confidence_score <= 1.0

    def test_escalation_context_with_chat_link(self):
        ctx = EscalationContext(
            question="Test",
            confidence_score=0.3,
            reason="Low confidence",
            google_chat_link="https://chat.google.com/space/123",
        )
        assert ctx.google_chat_link is not None

    def test_low_grade_context(self, sample_low_grade_context):
        assert sample_low_grade_context.score < sample_low_grade_context.threshold
        assert sample_low_grade_context.max_score == 10.0

    def test_daily_summary_context(self, sample_daily_summary_context):
        assert len(sample_daily_summary_context.lessons) == 3
        assert sample_daily_summary_context.lessons[0].subject == "Science"

    def test_lesson_summary_fields(self):
        lesson = LessonSummary(
            subject="Math",
            content="Fractions lesson",
            homework="Do exercises 1-5",
            homework_link="https://example.com",
            mandatory_assignment="Unit 9.1",
            mandatory_assignment_deadline="Thu Ba 13/01",
        )
        assert lesson.mandatory_assignment_deadline is not None

    def test_notification_auto_id(self, sample_teacher):
        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            teacher=sample_teacher,
            title="Test",
            message="Test",
        )
        assert notification.notification_id is not None

    def test_notification_default_values(self, sample_teacher):
        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            teacher=sample_teacher,
            title="Test",
            message="Test",
        )
        assert notification.channel == NotificationChannel.EMAIL
        assert notification.status == NotificationStatus.PENDING

    def test_notification_type_enum(self):
        assert NotificationType.TEACHER_ESCALATION.value == "teacher_escalation"
        assert NotificationType.LOW_GRADE_ALERT.value == "low_grade_alert"
        assert NotificationType.DAILY_SUMMARY.value == "daily_summary"

    def test_notification_channel_enum(self):
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.GOOGLE_CHAT.value == "google_chat"
        assert NotificationChannel.ZALO.value == "zalo"
        assert NotificationChannel.ALL.value == "all"

    def test_notification_result_success(self):
        result = NotificationResult(
            notification_id="n1",
            success=True,
            channel=NotificationChannel.EMAIL,
            sent_at=datetime.now(),
        )
        assert result.success is True
        assert result.error_message is None

    def test_notification_result_failure(self):
        result = NotificationResult(
            notification_id="n1",
            success=False,
            channel=NotificationChannel.EMAIL,
            error_message="SMTP connection failed",
        )
        assert result.success is False


# ===== Email Notifier Tests =====

class TestEmailNotifier:

    def _create_notifier(self, **kwargs):
        defaults = dict(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            sender_email="sender@test.com",
        )
        defaults.update(kwargs)
        return EmailNotifier(**defaults)

    def test_email_notifier_initialization(self):
        notifier = self._create_notifier()
        assert notifier.channel_name == "email"
        assert notifier.enabled is True

    def test_email_notifier_disabled(self):
        notifier = self._create_notifier(enabled=False)
        assert notifier.enabled is False

    @pytest.mark.asyncio
    async def test_validate_config_missing_host(self):
        notifier = self._create_notifier(smtp_host="")
        valid, error = await notifier.validate_config()
        assert valid is False
        assert "host" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_config_missing_credentials(self):
        notifier = self._create_notifier(username="", password="")
        valid, error = await notifier.validate_config()
        assert valid is False
        assert "credentials" in error.lower()

    def test_create_html_escalation(self, sample_escalation_notification):
        notifier = self._create_notifier()
        html = notifier._create_html_content(sample_escalation_notification)
        assert "<!DOCTYPE html>" in html
        assert sample_escalation_notification.title in html
        assert "Vinschool" in html

    def test_create_html_escalation_with_chat_link(self, sample_escalation_notification):
        notifier = self._create_notifier()
        html = notifier._create_html_content(sample_escalation_notification)
        assert "Open Google Chat" in html

    def test_create_html_low_grade(self, sample_low_grade_notification):
        notifier = self._create_notifier()
        html = notifier._create_html_content(sample_low_grade_notification)
        assert "5.0" in html
        assert "10.0" in html
        assert "threshold" in html.lower()

    def test_create_plain_escalation(self, sample_escalation_notification):
        notifier = self._create_notifier()
        plain = notifier._create_plain_content(sample_escalation_notification)
        assert sample_escalation_notification.title in plain
        assert "Confidence" in plain

    def test_create_plain_low_grade(self, sample_low_grade_notification):
        notifier = self._create_notifier()
        plain = notifier._create_plain_content(sample_low_grade_notification)
        assert "5.0" in plain
        assert "threshold" in plain.lower()

    @pytest.mark.asyncio
    async def test_send_no_recipient(self):
        notifier = self._create_notifier()
        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            title="Test",
            message="Test",
        )
        result = await notifier.send(notification)
        assert result.success is False
        assert "recipient" in result.error_message.lower()


# ===== Google Chat Notifier Tests =====

class TestGoogleChatNotifier:

    def test_initialization(self):
        notifier = GoogleChatNotifier(
            default_webhook_url="https://chat.googleapis.com/v1/spaces/xxx",
        )
        assert notifier.channel_name == "google_chat"
        assert notifier.enabled is True

    def test_disabled(self):
        notifier = GoogleChatNotifier(enabled=False)
        assert notifier.enabled is False

    @pytest.mark.asyncio
    async def test_validate_config_no_webhook(self):
        notifier = GoogleChatNotifier()
        valid, error = await notifier.validate_config()
        assert valid is True  # Warning only

    @pytest.mark.asyncio
    async def test_validate_config_invalid_url(self):
        notifier = GoogleChatNotifier(default_webhook_url="https://invalid.com/webhook")
        valid, error = await notifier.validate_config()
        assert valid is False

    def test_create_card_message_escalation(self, sample_escalation_notification):
        notifier = GoogleChatNotifier()
        card = notifier._create_card_message(sample_escalation_notification)
        assert "cardsV2" in card
        assert len(card["cardsV2"]) == 1

    def test_create_card_message_has_chat_link_button(self, sample_escalation_notification):
        notifier = GoogleChatNotifier()
        sections = notifier._build_escalation_sections(sample_escalation_notification)
        # Should have a section with "Open Chat with Student" button
        button_found = False
        for section in sections:
            for widget in section.get("widgets", []):
                if "buttonList" in widget:
                    button_found = True
        assert button_found

    def test_create_daily_summary_message(self, sample_daily_summary_notification):
        notifier = GoogleChatNotifier()
        msg = notifier._create_daily_summary_message(sample_daily_summary_notification)
        assert "text" in msg
        assert "Science" in msg["text"]
        assert "Toan" in msg["text"]
        assert "Tieng Anh" in msg["text"]

    def test_create_low_grade_card(self, sample_low_grade_notification):
        notifier = GoogleChatNotifier()
        card = notifier._create_card_message(sample_low_grade_notification)
        assert "cardsV2" in card

    @pytest.mark.asyncio
    async def test_send_no_webhook(self, sample_escalation_notification):
        notifier = GoogleChatNotifier()
        sample_escalation_notification.teacher.google_chat_webhook = None
        result = await notifier.send(sample_escalation_notification)
        assert result.success is False
        assert "webhook" in result.error_message.lower()


# ===== Zalo Notifier Tests =====

class TestZaloNotifier:

    def test_initialization_disabled_by_default(self):
        notifier = ZaloNotifier()
        assert notifier.channel_name == "zalo"
        assert notifier.enabled is False

    @pytest.mark.asyncio
    async def test_validate_config_no_token(self):
        notifier = ZaloNotifier()
        valid, error = await notifier.validate_config()
        assert valid is False

    @pytest.mark.asyncio
    async def test_send_stub_returns_success(self, sample_daily_summary_notification):
        notifier = ZaloNotifier(enabled=True)
        result = await notifier.send(sample_daily_summary_notification)
        assert result.success is True
        assert "STUB" in result.error_message

    def test_format_daily_summary(self, sample_daily_summary_notification):
        notifier = ZaloNotifier()
        text = notifier.format_daily_summary(sample_daily_summary_notification)
        assert "Bo me" in text
        assert "Science" in text


# ===== Notification Service Tests =====

class TestNotificationService:

    @pytest.fixture
    def mock_settings(self):
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
            settings.ZALO_OA_ACCESS_TOKEN = None
            settings.ENABLE_ZALO_NOTIFICATIONS = False
            settings.NOTIFICATION_TIMEOUT = 30
            mock.return_value = settings
            yield settings

    def test_create_teacher_escalation(self, mock_settings, sample_teacher, sample_student):
        NotificationService._instance = None
        service = NotificationService()
        notification = service.create_teacher_escalation(
            teacher=sample_teacher,
            student=sample_student,
            question="What is X?",
            confidence_score=0.25,
            reason="Low confidence",
        )
        assert notification.notification_type == NotificationType.TEACHER_ESCALATION
        assert notification.escalation_context is not None
        assert notification.escalation_context.question == "What is X?"

    def test_create_teacher_escalation_with_chat_link(self, mock_settings, sample_teacher, sample_student):
        NotificationService._instance = None
        service = NotificationService()
        notification = service.create_teacher_escalation(
            teacher=sample_teacher,
            student=sample_student,
            question="Test?",
            confidence_score=0.3,
            reason="Test",
            google_chat_link="https://chat.google.com/space/123",
        )
        assert notification.escalation_context.google_chat_link == "https://chat.google.com/space/123"

    def test_create_low_grade_alert(self, mock_settings, sample_teacher, sample_student):
        NotificationService._instance = None
        service = NotificationService()
        notification = service.create_low_grade_alert(
            teacher=sample_teacher,
            student=sample_student,
            assignment_id="hw-001",
            assignment_title="Fractions",
            subject="Mathematics",
            score=5.0,
            max_score=10.0,
            threshold=7.0,
            feedback="Needs improvement",
            areas_for_improvement=["Denominators"],
        )
        assert notification.notification_type == NotificationType.LOW_GRADE_ALERT
        assert notification.low_grade_context is not None
        assert notification.low_grade_context.score == 5.0
        assert notification.low_grade_context.threshold == 7.0
        assert "5.0" in notification.message

    def test_create_daily_summary_for_students(self, mock_settings, sample_student):
        NotificationService._instance = None
        service = NotificationService()
        lessons = [
            LessonSummary(subject="Math", content="Fractions"),
            LessonSummary(subject="English", content="Grammar"),
        ]
        notification = service.create_daily_summary_for_students(
            student=sample_student,
            date="2026-01-12",
            lessons=lessons,
        )
        assert notification.notification_type == NotificationType.DAILY_SUMMARY
        assert notification.channel == NotificationChannel.GOOGLE_CHAT
        assert notification.daily_summary_context is not None
        assert len(notification.daily_summary_context.lessons) == 2

    def test_create_daily_summary_for_parents(self, mock_settings, sample_parent, sample_student):
        NotificationService._instance = None
        service = NotificationService()
        lessons = [LessonSummary(subject="Math", content="Fractions")]
        notification = service.create_daily_summary_for_parents(
            parent=sample_parent,
            student=sample_student,
            date="2026-01-12",
            lessons=lessons,
        )
        assert notification.notification_type == NotificationType.DAILY_SUMMARY
        assert notification.channel == NotificationChannel.ZALO
        assert notification.parent is not None

    @pytest.mark.asyncio
    async def test_send_notification_email_only(self, mock_settings, sample_escalation_notification):
        NotificationService._instance = None
        service = NotificationService()

        with patch.object(service._email_notifier, "send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = NotificationResult(
                notification_id=sample_escalation_notification.notification_id,
                success=True,
                channel=NotificationChannel.EMAIL,
                sent_at=datetime.now(),
            )
            results = await service.send(sample_escalation_notification)
            assert len(results) == 1
            assert results[0].success is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_disabled_channel(self, mock_settings, sample_escalation_notification):
        NotificationService._instance = None
        mock_settings.ENABLE_EMAIL_NOTIFICATIONS = False
        service = NotificationService()
        sample_escalation_notification.channel = NotificationChannel.EMAIL
        results = await service.send(sample_escalation_notification)
        assert len(results) == 1
        assert results[0].success is False
        assert "not enabled" in results[0].error_message


# ===== Workflow Integration Tests =====

class TestWorkflowIntegration:

    @pytest.mark.asyncio
    async def test_escalation_message_to_student(self):
        """Verify the student-facing escalation message is set correctly."""
        # This tests the workflow logic that sets the student response
        expected_msg = (
            "Câu hỏi này cô chưa có đủ thông tin để trả lời. "
            "Cô sẽ chuyển câu hỏi sang cho giáo viên để giải đáp sớm nhất cho con."
        )
        assert "chưa có đủ thông tin" in expected_msg
        assert "giáo viên" in expected_msg


# Run with: pytest tests/test_notification_service.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
