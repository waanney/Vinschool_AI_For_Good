"""
Demo script to test NotificationService.

Usage:
    # Dry run (no actual sending, just shows what would be sent)
    python scripts/demo_notification.py --dry-run

    # Test email only
    python scripts/demo_notification.py --email

    # Test Google Chat only
    python scripts/demo_notification.py --google-chat

    # Test both channels
    python scripts/demo_notification.py --all
"""

import asyncio
import argparse
from datetime import datetime

# Add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.notification import (
    get_notification_service,
    NotificationService,
    TeacherInfo,
    StudentInfo,
    NotificationChannel,
    NotificationType,
    NotificationPriority,
    Notification,
    EscalationContext,
)
from config.settings import get_settings


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_notification_preview(notification: Notification):
    """Print a preview of what the notification contains."""
    print(f"\n📧 Notification Preview:")
    print(f"   ID: {notification.notification_id[:8]}...")
    print(f"   Type: {notification.notification_type.value}")
    print(f"   Priority: {notification.priority.value}")
    print(f"   Channel: {notification.channel.value}")
    print(f"\n   To: {notification.teacher.name} <{notification.teacher.email}>")
    if notification.student:
        print(f"   About: {notification.student.name} (Grade {notification.student.grade})")
    print(f"\n   Title: {notification.title}")
    print(f"   Message: {notification.message[:100]}...")

    if notification.escalation_context:
        ctx = notification.escalation_context
        print(f"\n   📌 Escalation Context:")
        print(f"      Question: {ctx.question}")
        print(f"      Confidence: {ctx.confidence_score:.1%}")
        print(f"      Reason: {ctx.reason}")


async def test_dry_run():
    """Show what notifications would look like without sending."""
    print_header("DRY RUN - Notification Preview")

    # Reset singleton for fresh test
    NotificationService._instance = None
    service = get_notification_service()

    # Sample teacher and student
    teacher = TeacherInfo(
        teacher_id="demo-teacher-001",
        name="Nguyen Van A",
        email="teacher@vinschool.edu.vn",
    )

    student = StudentInfo(
        student_id="demo-student-001",
        name="Tran Van B",
        grade="9",
        class_name="9A1",
    )

    # Create different notification types
    print("\n" + "-" * 40)
    print("1️⃣  TEACHER ESCALATION (Low Confidence)")
    print("-" * 40)

    notification1 = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="Làm thế nào để giải phương trình vi phân bậc hai?",
        confidence_score=0.25,
        reason="Chủ đề nâng cao không có trong tài liệu học tập",
        ai_response="Xin lỗi, câu hỏi này vượt quá phạm vi tài liệu. Hãy hỏi giáo viên nhé!",
        subject="Mathematics",
        topic="Differential Equations",
    )
    print_notification_preview(notification1)

    print("\n" + "-" * 40)
    print("2️⃣  HOMEWORK GRADED")
    print("-" * 40)

    notification2 = service.create_homework_notification(
        teacher=teacher,
        student=student,
        assignment_id="hw-demo-001",
        assignment_title="Bài tập Phân số - Chương 9",
        subject="Mathematics",
        notification_type=NotificationType.HOMEWORK_GRADED,
        score=78.5,
        max_score=100.0,
        feedback="Làm bài tốt! Cần chú ý hơn khi quy đồng mẫu số.",
        areas_for_improvement=["Quy đồng mẫu số", "Rút gọn kết quả"],
    )
    print_notification_preview(notification2)

    print("\n" + "-" * 40)
    print("3️⃣  STRUGGLING STUDENT ALERT")
    print("-" * 40)

    notification3 = service.create_struggling_student_alert(
        teacher=teacher,
        student=student,
        reason="Điểm bài tập giảm liên tục trong 2 tuần qua",
        subject="Mathematics",
        recent_scores=[65.0, 58.0, 52.0, 48.0],
    )
    print_notification_preview(notification3)

    print("\n✅ Dry run complete! No notifications were actually sent.")
    print("   To send real notifications, use --email or --google-chat flags.")


async def test_email():
    """Test sending email notification."""
    print_header("EMAIL NOTIFICATION TEST")

    settings = get_settings()

    # Check configuration
    print("\n📋 Email Configuration Check:")
    print(f"   ENABLE_EMAIL_NOTIFICATIONS: {settings.ENABLE_EMAIL_NOTIFICATIONS}")
    print(f"   SMTP_HOST: {settings.SMTP_HOST or '(not set)'}")
    print(f"   SMTP_PORT: {settings.SMTP_PORT}")
    print(f"   SMTP_USERNAME: {'✓ set' if settings.SMTP_USERNAME else '✗ not set'}")
    print(f"   SMTP_PASSWORD: {'✓ set' if settings.SMTP_PASSWORD else '✗ not set'}")
    print(f"   SENDER_EMAIL: {settings.NOTIFICATION_SENDER_EMAIL}")

    if not settings.ENABLE_EMAIL_NOTIFICATIONS:
        print("\n⚠️  Email notifications are DISABLED!")
        print("   Set ENABLE_EMAIL_NOTIFICATIONS=true in .env to enable.")
        return

    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        print("\n❌ Email not configured!")
        print("   Please set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD in .env")
        return

    # Get test email address
    test_email = input("\n📧 Enter email address to send test to: ").strip()
    if not test_email:
        print("❌ No email provided, skipping test.")
        return

    # Create notification service
    NotificationService._instance = None
    service = get_notification_service()

    # Validate config
    valid, error = await service._email_notifier.validate_config()
    if not valid:
        print(f"\n❌ Email configuration invalid: {error}")
        return

    print("\n✓ Email configuration valid!")

    # Create test notification
    teacher = TeacherInfo(
        teacher_id="test-001",
        name="Test Teacher",
        email=test_email,
    )

    student = StudentInfo(
        student_id="test-student-001",
        name="Test Student",
        grade="9",
        class_name="9A1",
    )

    notification = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="This is a test question from the notification demo",
        confidence_score=0.35,
        reason="Testing notification system",
        subject="Test Subject",
        channel=NotificationChannel.EMAIL,
    )

    print(f"\n📤 Sending test email to {test_email}...")

    results = await service.send(notification)

    for result in results:
        if result.success:
            print(f"\n✅ Email sent successfully!")
            print(f"   Check your inbox at: {test_email}")
        else:
            print(f"\n❌ Email failed: {result.error_message}")


async def test_google_chat():
    """Test sending Google Chat notification."""
    print_header("GOOGLE CHAT NOTIFICATION TEST")

    settings = get_settings()

    # Check configuration
    print("\n📋 Google Chat Configuration Check:")
    print(f"   ENABLE_GOOGLE_CHAT_NOTIFICATIONS: {settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS}")
    print(f"   GOOGLE_CHAT_WEBHOOK_URL: {'✓ set' if settings.GOOGLE_CHAT_WEBHOOK_URL else '✗ not set'}")

    if not settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS:
        print("\n⚠️  Google Chat notifications are DISABLED!")
        print("   Set ENABLE_GOOGLE_CHAT_NOTIFICATIONS=true in .env to enable.")

    # Ask for webhook URL
    webhook_url = settings.GOOGLE_CHAT_WEBHOOK_URL
    if not webhook_url:
        print("\n💡 To get a webhook URL:")
        print("   1. Open Google Chat")
        print("   2. Go to a Space > Manage webhooks")
        print("   3. Create a new webhook and copy the URL")
        webhook_url = input("\n🔗 Enter Google Chat webhook URL: ").strip()

    if not webhook_url:
        print("❌ No webhook URL provided, skipping test.")
        return

    if not webhook_url.startswith("https://chat.googleapis.com/"):
        print("❌ Invalid webhook URL format!")
        return

    # Create notification service
    NotificationService._instance = None
    service = get_notification_service()

    # Create test notification with webhook
    teacher = TeacherInfo(
        teacher_id="test-001",
        name="Test Teacher",
        email="test@example.com",
        google_chat_webhook=webhook_url,
    )

    student = StudentInfo(
        student_id="test-student-001",
        name="Test Student",
        grade="9",
        class_name="9A1",
    )

    notification = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="Đây là câu hỏi test từ notification demo",
        confidence_score=0.28,
        reason="Testing Google Chat notification",
        ai_response="AI không thể trả lời câu hỏi này một cách tự tin.",
        subject="Test Subject",
        topic="Demo Testing",
        channel=NotificationChannel.GOOGLE_CHAT,
    )

    print(f"\n📤 Sending test message to Google Chat...")

    # Temporarily enable and set webhook
    service._google_chat_notifier._enabled = True

    results = await service.send(notification)

    for result in results:
        if result.success:
            print(f"\n✅ Google Chat message sent successfully!")
            print(f"   Check your Google Chat space.")
        else:
            print(f"\n❌ Google Chat failed: {result.error_message}")


async def test_all():
    """Test both email and Google Chat."""
    await test_email()
    await test_google_chat()


def main():
    parser = argparse.ArgumentParser(
        description="Test NotificationService",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo_notification.py --dry-run    # Preview without sending
  python scripts/demo_notification.py --email      # Test email only
  python scripts/demo_notification.py --google-chat # Test Google Chat only
  python scripts/demo_notification.py --all        # Test both channels
        """
    )

    parser.add_argument("--dry-run", action="store_true",
                        help="Preview notifications without sending")
    parser.add_argument("--email", action="store_true",
                        help="Test email notifications")
    parser.add_argument("--google-chat", action="store_true",
                        help="Test Google Chat notifications")
    parser.add_argument("--all", action="store_true",
                        help="Test all notification channels")

    args = parser.parse_args()

    print("\n" + "╔" + "=" * 58 + "╗")
    print("║  🔔 NOTIFICATION SERVICE DEMO                            ║")
    print("╚" + "=" * 58 + "╝")

    if args.dry_run or (not args.email and not args.google_chat and not args.all):
        asyncio.run(test_dry_run())
    elif args.email:
        asyncio.run(test_email())
    elif args.google_chat:
        asyncio.run(test_google_chat())
    elif args.all:
        asyncio.run(test_all())


if __name__ == "__main__":
    main()
