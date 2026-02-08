"""
Demo script for NotificationService features.

Usage (feature-based):
    python scripts/demo_notification.py --escalation      # Teacher escalation: Email + Google Chat
    python scripts/demo_notification.py --low-grade       # Low grade alert: Email to teacher
    python scripts/demo_notification.py --daily-summary   # Daily summary: Google Chat to students
    python scripts/demo_notification.py --daily-parent    # Daily summary: Zalo stub to parents
    python scripts/demo_notification.py --all             # Run all features

    python scripts/demo_notification.py --dry-run         # Preview all without sending
"""

import asyncio
import argparse

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
    LessonSummary,
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
        print(f"   Confidence: {ctx.confidence_score:.1%}")
        if ctx.google_chat_link:
            print(f"   Chat Link:  {ctx.google_chat_link}")

    if notification.low_grade_context:
        ctx = notification.low_grade_context
        print(f"   Assignment: {ctx.assignment_title}")
        print(f"   Score:      {ctx.score}/{ctx.max_score} (threshold: {ctx.threshold})")

    if notification.daily_summary_context:
        ctx = notification.daily_summary_context
        print(f"   Date: {ctx.date}")
        for lesson in ctx.lessons:
            print(f"     - {lesson.subject}: {lesson.content[:50]}...")


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


def get_sample_lessons() -> list[LessonSummary]:
    return [
        LessonSummary(
            subject="Science",
            content='Cac con lam thi nghiem de tim hieu ve co che hoat dong cua he tieu hoa "digestive system".',
            homework="Hom qua co Oanh da phat mot phieu bai tap mon Science, cac con hoan thanh va nop lai cho co vao thu hai (12/01) nhe.",
            homework_link="https://drive.google.com/drive/folders/1NRTD6RqkqZD7BJMuKbYtK8lQA93ouHma?usp=drive_link",
        ),
        LessonSummary(
            subject="Toan",
            content='Cac con on tap ve phep tinh cong va tru phan so co cung mau so "denominator". Cac con bat dau hoc ve cong va tru phan so khac mau so "denominator". Vi du nhu: 1/2 + 1/4; 1/3 - 1/6;...',
            homework="Co gui lai phieu Toan + Tieng Anh ma co da phat trong tuan nay cho cac con:",
            homework_link="https://drive.google.com/drive/folders/13VGznRDf_VggXSkonI-SeGztkLri0bXI?usp=drive_link",
            mandatory_assignment="Bai tap Toan trong workbook tuan nay cua cac con la: Unit 9.1, pages 93-97",
            mandatory_assignment_deadline="han nop thu Ba 13/01",
        ),
        LessonSummary(
            subject="Tieng Anh",
            content='Cac con on tap lai cau dieu kien loai 0 "zero conditional" va cau hoi duoi "question tag".',
            homework_link="https://classroom.google.com/c/ODAzMTk4Mzg1ODc5/a/ODI0MTg2MTAwMDQ5/details",
        ),
    ]


# ===== Feature Demos =====

async def demo_teacher_escalation():
    """
    FEATURE: Teacher Escalation
    When AI can't answer a student question:
      1. Student sees a Vietnamese message in chat
      2. Teacher gets an email with question details + Google Chat link
      3. Teacher gets a Google Chat card with "Open Chat" button
    """
    print_header("FEATURE: Teacher Escalation")
    print("""
  Scenario: Student asks "Thu 6 tuan nay co kiem tra Tieng Viet khong?"
  AI confidence is low (28%) -> triggers escalation.

  What happens:
    1. Student sees: "Cau hoi nay co chua co du thong tin..."
    2. Teacher gets EMAIL with question + Google Chat link
    3. Teacher gets GOOGLE CHAT card with "Open Chat" button
    """)

    settings = get_settings()
    service = get_service()
    student = get_sample_student()

    # Ask for teacher email
    default_email = settings.SMTP_USERNAME or "teacher@vinschool.edu.vn"
    test_email = input(f"  Teacher email to send to [{default_email}]: ").strip() or default_email

    teacher = get_sample_teacher(email_override=test_email)
    teacher.google_chat_webhook = settings.GOOGLE_CHAT_WEBHOOK_URL

    # Step 1: Show student-facing message
    print_sub("Step 1: Student sees this in chat")
    print('  "Cau hoi nay co chua co du thong tin de tra loi.')
    print('   Co se chuyen cau hoi sang cho giao vien de giai dap')
    print('   som nhat cho con."')

    # Step 2: Send email to teacher
    print_sub("Step 2: Email to teacher")
    email_notification = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="Thu 6 tuan nay co kiem tra Tieng Viet khong co?",
        confidence_score=0.28,
        reason="Khong tim thay thong tin lich kiem tra trong tai lieu",
        ai_response="Cau hoi nay co chua co du thong tin de tra loi.",
        subject="Tieng Viet",
        channel=NotificationChannel.EMAIL,
    )
    print_notification_preview(email_notification)

    if settings.ENABLE_EMAIL_NOTIFICATIONS:
        print(f"\n  Sending email to {test_email}...")
        results = await service.send(email_notification)
        print_results(results, f"-> {test_email}")
    else:
        print("\n  [SKIP] Email disabled in .env")

    # Step 3: Send Google Chat card to teacher
    print_sub("Step 3: Google Chat card to teacher")
    gchat_notification = service.create_teacher_escalation(
        teacher=teacher,
        student=student,
        question="Thu 6 tuan nay co kiem tra Tieng Viet khong co?",
        confidence_score=0.28,
        reason="Khong tim thay thong tin lich kiem tra trong tai lieu",
        ai_response="Cau hoi nay co chua co du thong tin de tra loi.",
        subject="Tieng Viet",
        channel=NotificationChannel.GOOGLE_CHAT,
    )
    print_notification_preview(gchat_notification)

    if settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS and settings.GOOGLE_CHAT_WEBHOOK_URL:
        print(f"\n  Sending to Google Chat...")
        results = await service.send(gchat_notification)
        print_results(results, "-> Google Chat space")
    else:
        print("\n  [SKIP] Google Chat disabled or no webhook in .env")

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
  on "Bai tap Phan so - Chuong 9" (threshold: 7.0)

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
        assignment_title="Bai tap Phan so - Chuong 9",
        subject="Mathematics",
        score=5.0,
        max_score=10.0,
        threshold=7.0,
        feedback="Hoc sinh can on lai phep quy dong mau so. "
                 "Nhieu bai tap chua rut gon ket qua cuoi cung.",
        areas_for_improvement=[
            "Quy dong mau so",
            "Rut gon ket qua",
            "Trinh bay bai giai",
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
        lessons=get_sample_lessons(),
        general_notes="Cac con nho hoan thanh bai tap day du nhe!",
    )
    print_notification_preview(notification)

    if settings.ENABLE_GOOGLE_CHAT_NOTIFICATIONS and settings.GOOGLE_CHAT_WEBHOOK_URL:
        print(f"\n  Sending daily summary to Google Chat...")
        results = await service.send(notification)
        print_results(results, "-> Google Chat space")
    else:
        print("\n  [SKIP] Google Chat disabled or no webhook in .env")

    print("\n  Daily summary (students) demo complete!")


async def demo_daily_summary_parents():
    """
    FEATURE: Daily Summary for Parents (Zalo - stub)
    Same content but more formal tone, sent via Zalo.
    """
    print_header("FEATURE: Daily Summary (Parents -> Zalo)")
    print("""
  Scenario: Same school day summary, sent to parents via Zalo.
  NOTE: Zalo is a STUB - will log but not actually send.

  This is a placeholder for when Zalo OA API is integrated.
    """)

    service = get_service()
    student = get_sample_student()
    parent = get_sample_parent()

    notification = service.create_daily_summary_for_parents(
        parent=parent,
        student=student,
        date="2026-01-12",
        lessons=get_sample_lessons(),
    )
    print_notification_preview(notification)

    print(f"\n  Sending daily summary via Zalo (stub)...")
    results = await service.send(notification)
    print_results(results, f"-> Zalo (parent: {parent.name})")

    print("\n  Daily summary (parents) demo complete!")
    print("  Note: Zalo is a stub. Team will implement the real UI later.")


async def demo_dry_run():
    """Preview all notification types without sending anything."""
    print_header("DRY RUN - All Features Preview")

    service = get_service()
    teacher = get_sample_teacher()
    student = get_sample_student()
    parent = get_sample_parent()

    demos = [
        ("1. Teacher Escalation (Email + Google Chat)",
         service.create_teacher_escalation(
            teacher=teacher, student=student,
            question="Thu 6 tuan nay co kiem tra Tieng Viet khong co?",
            confidence_score=0.25,
            reason="Khong tim thay thong tin lich kiem tra",
            ai_response="Cau hoi nay co chua co du thong tin de tra loi.",
            subject="Tieng Viet",
         )),
        ("2. Low Grade Alert (Email)",
         service.create_low_grade_alert(
            teacher=teacher, student=student,
            assignment_id="hw-demo-001",
            assignment_title="Bai tap Phan so - Chuong 9",
            subject="Mathematics", score=5.0,
            feedback="Hoc sinh can on lai phep quy dong mau so.",
            areas_for_improvement=["Quy dong mau so", "Rut gon ket qua"],
         )),
        ("3. Daily Summary - Students (Google Chat)",
         service.create_daily_summary_for_students(
            student=student, date="2026-01-12",
            lessons=get_sample_lessons(),
            general_notes="Cac con nho hoan thanh bai tap day du nhe!",
         )),
        ("4. Daily Summary - Parents (Zalo stub)",
         service.create_daily_summary_for_parents(
            parent=parent, student=student, date="2026-01-12",
            lessons=get_sample_lessons(),
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
