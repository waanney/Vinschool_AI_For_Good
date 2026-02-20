"""
Demo script for NotificationService features.

Usage (feature-based):
    python scripts/demo_notification.py --escalation      # Teacher escalation: Email + Google Chat
    python scripts/demo_notification.py --low-grade       # Low grade alert: Email to teacher
    python scripts/demo_notification.py --daily-summary   # Daily summary: Google Chat to students
    python scripts/demo_notification.py --daily-parent    # Daily summary: Zalo Clone UI to parents
    python scripts/demo_notification.py --all             # Run all features

    python scripts/demo_notification.py --dry-run         # Preview all without sending
"""

import asyncio
import argparse
import httpx

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.notification import (
    get_notification_service,
    NotificationService,
    TeacherInfo,
    StudentInfo,
    ParentInfo,
    NotificationChannel,
    NotificationType,
    Notification,
)
from config.settings import get_settings


# ===== Helpers =====

def print_header(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_sub(text: str):
    print("\n" + "-" * 40)
    print(f"  {text}")
    print("-" * 40)


def print_notification_preview(notification: Notification):
    print(f"\n  Notification Preview:")
    print(f"   ID:      {notification.notification_id[:8]}...")
    print(f"   Type:    {notification.notification_type.value}")
    print(f"   Channel: {notification.channel.value}")
    if notification.teacher:
        print(f"   To (teacher): {notification.teacher.name} <{notification.teacher.email}>")
    if notification.student:
        print(f"   Student: {notification.student.name}")
    if notification.parent:
        print(f"   To (parent): {notification.parent.name}")
    print(f"   Title:   {notification.title}")
    print(f"   Message: {notification.message[:100]}...")

    if notification.escalation_context:
        ctx = notification.escalation_context
        print(f"   Question:   {ctx.question}")
        print(f"   Confidence: {f'{ctx.confidence_score:.1%}' if ctx.confidence_score is not None else 'N/A'}")
        if ctx.google_chat_link:
            print(f"   Chat Link:  {ctx.google_chat_link}")

    if notification.low_grade_context:
        ctx = notification.low_grade_context
        print(f"   Assignment: {ctx.assignment_title}")
        print(f"   Score:      {ctx.score}/{ctx.max_score} (threshold: {ctx.threshold})")

    if notification.notification_type == NotificationType.DAILY_SUMMARY:
        # The full message already contains greeting + content + closing
        print(f"   Full text preview:")
        for line in notification.message.split('\n')[:6]:
            print(f"     {line}")
        if notification.message.count('\n') > 6:
            print(f"     ... ({notification.message.count(chr(10)) - 6} more lines)")


def print_results(results, label: str = ""):
    for r in results:
        status = "OK" if r.success else "FAILED"
        channel = r.channel.value if hasattr(r, 'channel') else "?"
        if r.success:
            print(f"   [{status}] {channel} {label}")
        else:
            print(f"   [{status}] {channel} - {r.error_message}")


def get_service() -> NotificationService:
    """Get a fresh service instance."""
    NotificationService._instance = None
    return get_notification_service()


# ===== Sample Data =====

def get_sample_teacher(email_override: str | None = None) -> TeacherInfo:
    return TeacherInfo(
        teacher_id="demo-teacher-001",
        name="Co Van Anh",
        email=email_override or "teacher@vinschool.edu.vn",
    )


def get_sample_student() -> StudentInfo:
    return StudentInfo(
        student_id="demo-student-001",
        name="Can Tran Quang Bach",
        grade="5",
        class_name="5A1",
        email="bach081559@stu.vinschool.edu.vn",
    )


def get_sample_parent() -> ParentInfo:
    return ParentInfo(
        parent_id="demo-parent-001",
        name="Tran Van C",
        zalo_id="zalo-demo-001",
        phone="0901234567",
    )


# Sample AI-generated summary text (plain text, no structured fields)
SAMPLE_AI_SUMMARY = (
    "1. Môn Science:\n"
    "Các con làm thí nghiệm để tìm hiểu về cơ chế hoạt động của hệ tiêu hóa \"digestive system\".\n"
    "Hôm qua cô Oanh đã phát một phiếu bài tập môn Science, các con hoàn thành và nộp lại cho cô vào thứ hai nhé.\n"
    "https://drive.google.com/drive/folders/1NRTD6RqkqZD7BJMuKbYtK8lQA93ouHma\n\n"
    "2. Môn Toán:\n"
    "Các con ôn tập về phép tính cộng và trừ phân số có cùng mẫu số \"denominator\".\n"
    "Bài tập Toán trong workbook tuần này: Unit 9.1, pages 93-97\n"
    "Hạn nộp thứ Ba 13/01\n"
    "https://drive.google.com/drive/folders/13VGznRDf_VggXSkonI-SeGztkLri0bXI\n\n"
    "3. Môn Tiếng Anh:\n"
    "Các con ôn tập lại câu điều kiện loại 0 \"zero conditional\" và câu hỏi đuôi \"question tag\".\n"
    "https://classroom.google.com/c/ODAzMTk4Mzg1ODc5/a/ODI0MTg2MTAwMDQ5/details"
)


# ===== Feature Demos =====

async def demo_teacher_escalation():
    """
    FEATURE: Teacher Escalation (Email only)
    When the AI can't answer a student's question in Google Chat:
      1. Bot replies in the shared space: "not enough info, escalating..."
         (done by the listener's _on_debounced reply — not this demo)
      2. Teacher gets an EMAIL with the question + a link back to that space
         so they can open Google Chat and answer the student directly.
    """
    print_header("FEATURE: Teacher Escalation")
    print("""
  Scenario: Student @mentions bot, asks about exam schedule.
  Bot cannot find the answer in lesson.txt -> escalation triggered.

  What happens:
    1. Bot says in the shared space: "Cô Hana chưa có thông tin về vấn đề này..."
       (This is handled by the Google Chat listener — not sent here)
    2. Teacher gets an EMAIL with:
       - The student's question
       - A direct link to the shared Google Chat space
       -> Teacher opens the link, goes into the group, answers the student
    """)

    settings = get_settings()
    service = get_service()
    student = get_sample_student()

    # Ask for teacher email
    default_email = settings.SMTP_USERNAME or "teacher@vinschool.edu.vn"
    test_email = input(f"  Teacher email to send to [{default_email}]: ").strip() or default_email

    teacher = get_sample_teacher(email_override=test_email)

    # Step 1: Show student-facing message (what the bot already said in the space)
    print_sub("Step 1: Bot reply in Google Chat space (already sent by listener)")
    print('  "Cô Hana chưa có thông tin về vấn đề này.')
    print('   Cô đã chuyển câu hỏi đến giáo viên chủ nhiệm,')
    print('   thầy/cô sẽ phản hồi sớm nhất nhé con!"')

    # Step 2: Email teacher with a link back to the shared space
    print_sub("Step 2: Email to teacher (with link to Google Chat space)")
    notification = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="Thứ 6 tuần này có kiểm tra Tiếng Việt không ạ?",
        reason="Không tìm thấy thông tin lịch kiểm tra trong tài liệu",
        ai_response="Cô Hana chưa có thông tin về vấn đề này.",
        subject="Tiếng Việt",
        channel=NotificationChannel.EMAIL,
    )
    print_notification_preview(notification)

    if settings.ENABLE_EMAIL_NOTIFICATIONS:
        print(f"\n  Sending escalation email to {test_email}...")
        results = await service.send(notification)
        print_results(results, f"-> {test_email}")
    else:
        print("\n  [SKIP] Email disabled in .env")

    print("\n  Escalation demo complete!")


async def demo_low_grade_alert():
    """
    FEATURE: Low Grade Alert
    When a student scores below threshold on an assignment:
      -> Teacher gets an email with score details + improvement areas
    """
    print_header("FEATURE: Low Grade Alert")
    print("""
  Scenario: Student "Can Tran Quang Bach" scored 5.0/10.0
  on "Bài tập Phân số - Chương 9" (threshold: 7.0)

  What happens:
    -> Teacher gets EMAIL with score, feedback, improvement areas
    """)

    settings = get_settings()
    service = get_service()
    student = get_sample_student()

    default_email = settings.SMTP_USERNAME or "teacher@vinschool.edu.vn"
    test_email = input(f"  Teacher email to send to [{default_email}]: ").strip() or default_email

    teacher = get_sample_teacher(email_override=test_email)

    notification = service.create_low_grade_alert(
        teacher=teacher,
        student=student,
        assignment_id="hw-demo-001",
        assignment_title="Bài tập Phân số - Chương 9",
        subject="Mathematics",
        score=5.0,
        max_score=10.0,
        threshold=7.0,
        feedback="Học sinh cần ôn lại phép quy đồng mẫu số. "
                 "Nhiều bài tập chưa rút gọn kết quả cuối cùng.",
        areas_for_improvement=[
            "Quy đồng mẫu số",
            "Rút gọn kết quả",
            "Trình bày bài giải",
        ],
        channel=NotificationChannel.EMAIL,
    )
    print_notification_preview(notification)

    if settings.ENABLE_EMAIL_NOTIFICATIONS:
        print(f"\n  Sending low grade alert to {test_email}...")
        results = await service.send(notification)
        print_results(results, f"-> {test_email}")
    else:
        print("\n  [SKIP] Email disabled in .env")

    print("\n  Low grade alert demo complete!")


async def demo_daily_summary_students():
    """
    FEATURE: Daily Summary for Students (Google Chat)
    End-of-day summary with lessons, homework, and links.
    """
    print_header("FEATURE: Daily Summary (Students -> Google Chat)")
    print("""
  Scenario: End of school day, 3 subjects today.
  AI sends a plain-text summary to the class Google Chat group.

  Content includes:
    - Lesson recap per subject
    - Homework + Google Drive links
    - Mandatory assignments + deadlines
    """)

    settings = get_settings()
    service = get_service()
    student = get_sample_student()

    notification = service.create_daily_summary_for_students(
        student=student,
        date="2026-01-12",
        content=SAMPLE_AI_SUMMARY,
    )
    print_notification_preview(notification)

    if settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS and (settings.GOOGLE_CHAT_WEBHOOK_URL or settings.GOOGLE_CHAT_SPACE_ID):
        gchat_mode = "Chat API" if settings.GOOGLE_CHAT_SPACE_ID and settings.GOOGLE_APPLICATION_CREDENTIALS else "Webhook"
        print(f"\n  Sending daily summary to Google Chat ({gchat_mode})...")
        results = await service.send(notification)
        print_results(results, "-> Google Chat space")
    else:
        print("\n  [SKIP] Google Chat disabled or no webhook/space in .env")

    print("\n  Daily summary (students) demo complete!")


async def demo_daily_summary_parents():
    """
    FEATURE: Daily Summary for Parents (Zalo clone UI)
    Same content but more formal tone, sent via Zalo.
    Messages appear in the Zalo clone UI at /zalo/desktop.
    """
    print_header("FEATURE: Daily Summary (Parents -> Zalo clone UI)")
    print("""
  Scenario: Same school day summary, sent to parents via Zalo.
  The demo POSTs to the running Zalo server so the message
  appears in the Zalo clone UI.

  To see it: open http://localhost:3000/zalo/desktop
  (requires run_zalo_server.py running on port 8000)
    """)

    service = get_service()
    student = get_sample_student()
    parent = get_sample_parent()

    notification = service.create_daily_summary_for_parents(
        parent=parent,
        student=student,
        date="2026-01-12",
        content=SAMPLE_AI_SUMMARY,
    )
    print_notification_preview(notification)

    # POST to the running Zalo server's send-demo endpoint so the message
    # appears in the Zalo clone UI (in-memory store lives in the server process)
    server_url = "http://localhost:8000/api/zalo/send-demo"
    print(f"\n  POSTing to {server_url}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(server_url, json={
                "student_name": student.name,
                "class_name": student.class_name,
            })
            resp.raise_for_status()
            data = resp.json()
            print(f"  -> Success! notification_id={data.get('notification_id', 'N/A')}")
    except httpx.ConnectError:
        print("  [ERROR] Cannot connect to http://localhost:8000")
        print("          Start the server first: python -m scripts.run_zalo_server")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print("\n  Daily summary (parents) demo complete!")
    print("  Check the Zalo clone UI at http://localhost:3000/zalo/desktop")


async def demo_dry_run():
    """Preview all notification types without sending anything."""
    print_header("DRY RUN - All Features Preview")

    service = get_service()
    teacher = get_sample_teacher()
    student = get_sample_student()
    parent = get_sample_parent()

    demos = [
        ("1. Teacher Escalation (Email only — link to Google Chat space)",
         service.create_teacher_escalation(
            teacher=teacher, student=student,
            question="Thứ 6 tuần nay có kiểm tra Tiếng Việt không cô?",
            reason="Không tìm thấy thông tin lịch kiểm tra",
            ai_response="Cô Hana chưa có thông tin về vấn đề này.",
            subject="Tiếng Việt",
         )),
        ("2. Low Grade Alert (Email)",
         service.create_low_grade_alert(
            teacher=teacher, student=student,
            assignment_id="hw-demo-001",
            assignment_title="Bài tập Phân số - Chương 9",
            subject="Toán", score=5.0,
            feedback="Học sinh cần ôn lại phép quy đồng mẫu số.",
            areas_for_improvement=["Quy đồng mẫu số", "Rút gọn kết quả", "Trình bày bài giải"],
         )),
        ("3. Daily Summary - Students (Google Chat)",
         service.create_daily_summary_for_students(
            student=student, date="2026-01-12",
            content=SAMPLE_AI_SUMMARY,
         )),
        ("4. Daily Summary - Parents (Zalo clone UI)",
         service.create_daily_summary_for_parents(
            parent=parent, student=student, date="2026-01-12",
            content=SAMPLE_AI_SUMMARY,
         )),
    ]

    for label, notification in demos:
        print_sub(label)
        print_notification_preview(notification)

    print("\n  Dry run complete! Use feature flags to send real notifications.")


async def demo_all():
    """Run all feature demos in sequence."""
    await demo_teacher_escalation()
    await demo_low_grade_alert()
    await demo_daily_summary_students()
    await demo_daily_summary_parents()


def main():
    parser = argparse.ArgumentParser(
        description="Demo NotificationService features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Feature demos:
  --escalation     Teacher escalation (Email + Google Chat)
  --low-grade      Low grade alert (Email to teacher)
  --daily-summary  Daily summary for students (Google Chat)
  --daily-parent   Daily summary for parents (Zalo stub)
  --all            Run all feature demos

Other:
  --dry-run        Preview all notification types without sending
        """
    )

    parser.add_argument("--escalation", action="store_true",
                        help="Demo teacher escalation: Email + Google Chat")
    parser.add_argument("--low-grade", action="store_true",
                        help="Demo low grade alert: Email to teacher")
    parser.add_argument("--daily-summary", action="store_true",
                        help="Demo daily summary for students: Google Chat")
    parser.add_argument("--daily-parent", action="store_true",
                        help="Demo daily summary for parents: Zalo (stub)")
    parser.add_argument("--all", action="store_true",
                        help="Run all feature demos")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all types without sending")

    args = parser.parse_args()

    print("\n" + "=" * 58)
    print("  NOTIFICATION SERVICE - FEATURE DEMO")
    print("=" * 58)

    if args.escalation:
        asyncio.run(demo_teacher_escalation())
    elif args.low_grade:
        asyncio.run(demo_low_grade_alert())
    elif args.daily_summary:
        asyncio.run(demo_daily_summary_students())
    elif args.daily_parent:
        asyncio.run(demo_daily_summary_parents())
    elif args.all:
        asyncio.run(demo_all())
    elif args.dry_run:
        asyncio.run(demo_dry_run())
    else:
        # No flag -> show help
        parser.print_help()


if __name__ == "__main__":
    main()
