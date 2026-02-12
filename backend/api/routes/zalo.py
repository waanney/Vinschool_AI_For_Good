"""
Zalo notification API endpoints.

Provides REST endpoints for the Zalo clone UI to fetch messages
sent by the notification service. Also includes a demo endpoint
to trigger a sample daily summary notification.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.notification.zalo_notifier import ZaloNotifier, zalo_message_store
from services.notification.models import (
    Notification,
    NotificationType,
    NotificationChannel,
    DailySummaryContext,
    LessonSummary,
    StudentInfo,
    ParentInfo,
)
from utils.logger import logger

router = APIRouter()


# ===== Response Models =====

class ZaloLessonResponse(BaseModel):
    """A single lesson in the daily summary."""
    subject: str
    content: str
    homework: Optional[str] = None
    homework_link: Optional[str] = None
    mandatory_assignment: Optional[str] = None
    mandatory_assignment_deadline: Optional[str] = None
    mandatory_assignment_link: Optional[str] = None
    reading_materials_link: Optional[str] = None


class ZaloMessageResponse(BaseModel):
    """A single Zalo message returned to the frontend."""
    id: str
    sender: str
    greeting: str
    intro: str
    lessons: list[ZaloLessonResponse] = []
    closing: str
    time: str
    is_ai: bool = True


class ZaloMessagesListResponse(BaseModel):
    """List of all Zalo messages."""
    messages: list[ZaloMessageResponse]
    count: int


class DemoSendRequest(BaseModel):
    """Request body for the demo send endpoint."""
    student_name: str = "Alex"
    class_name: str = "4B5"
    date: Optional[str] = None  # defaults to today


class DemoSendResponse(BaseModel):
    """Response from the demo send endpoint."""
    success: bool
    message: str
    notification_id: Optional[str] = None


# ===== Endpoints =====

@router.get("/messages", response_model=ZaloMessagesListResponse)
async def get_zalo_messages():
    """
    Get all Zalo messages sent by the notification service.

    The Zalo clone UI polls this endpoint to display messages.
    """
    messages = []
    for msg in zalo_message_store:
        lessons = []
        if msg.get("lessons"):
            for lesson in msg["lessons"]:
                lessons.append(ZaloLessonResponse(
                    subject=lesson.get("subject", ""),
                    content=lesson.get("content", ""),
                    homework=lesson.get("homework"),
                    homework_link=lesson.get("homework_link"),
                    mandatory_assignment=lesson.get("mandatory_assignment"),
                    mandatory_assignment_deadline=lesson.get("mandatory_assignment_deadline"),
                    mandatory_assignment_link=lesson.get("mandatory_assignment_link"),
                    reading_materials_link=lesson.get("reading_materials_link"),
                ))

        messages.append(ZaloMessageResponse(
            id=msg["id"],
            sender=msg["sender"],
            greeting=msg["greeting"],
            intro=msg["intro"],
            lessons=lessons,
            closing=msg["closing"],
            time=msg["time"],
            is_ai=msg.get("is_ai", True),
        ))

    return ZaloMessagesListResponse(messages=messages, count=len(messages))


@router.post("/send-demo", response_model=DemoSendResponse)
async def send_demo_notification(request: DemoSendRequest = DemoSendRequest()):
    """
    Send a demo daily summary notification to the Zalo message store.

    This simulates what happens when the daily content workflow
    triggers a Zalo notification for parents. Use this to test
    the Zalo clone UI without running the full backend pipeline.
    """
    date_str = request.date or datetime.now().strftime("%d/%m/%Y")

    # Build sample lessons (matching the existing demo content)
    lessons = [
        LessonSummary(
            subject="Science",
            content='Tìm hiểu cơ chế hoạt động của hệ tiêu hoá "digestive system".',
            homework='Cô Oanh đã phát một phiếu bài tập môn Science, các con hoàn thành và nộp lại cho cô vào thứ Hai nhé.',
            homework_link="https://drive.google.com/drive/folders/example1",
        ),
        LessonSummary(
            subject="Toán",
            content='Cộng và trừ phân số có cùng mẫu số "denominator". Bắt đầu học khác mẫu số.',
            mandatory_assignment="Bài tập Toán trong workbook tuần này: Unit 9.1, pages 93-97",
            mandatory_assignment_deadline="hạn nộp thứ Ba 13/01",
            homework_link="https://drive.google.com/drive/folders/example2",
        ),
        LessonSummary(
            subject="Tiếng Anh",
            content='Ôn tập câu điều kiện loại 0 "zero conditional" và câu hỏi đuôi.',
            homework_link="https://classroom.google.com/c/example3",
        ),
    ]

    # Create the notification using the same models the real workflow uses
    notification = Notification(
        notification_type=NotificationType.DAILY_SUMMARY,
        channel=NotificationChannel.ZALO,
        student=StudentInfo(
            student_id="student-demo",
            name=request.student_name,
            grade="4",
            class_name=request.class_name,
        ),
        parent=ParentInfo(
            parent_id="parent-demo",
            name=f"Phụ huynh {request.student_name}",
        ),
        title=f"Daily Summary - {date_str}",
        message=f"Cô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:",
        daily_summary_context=DailySummaryContext(
            date=date_str,
            lessons=lessons,
            general_notes="Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.\nCảm ơn bố mẹ các con đã đọc tin ạ!",
        ),
    )

    # Send through the ZaloNotifier (which now stores the message)
    notifier = ZaloNotifier(enabled=True)
    result = await notifier.send(notification)

    if result.success:
        logger.info(f"Demo Zalo notification sent: {notification.notification_id}")
        return DemoSendResponse(
            success=True,
            message="Demo notification sent to Zalo message store",
            notification_id=notification.notification_id,
        )
    else:
        return DemoSendResponse(
            success=False,
            message=f"Failed to send: {result.error_message}",
        )


@router.delete("/messages")
async def clear_zalo_messages():
    """Clear all messages from the Zalo message store (for testing)."""
    zalo_message_store.clear()
    return {"success": True, "message": "All Zalo messages cleared"}
