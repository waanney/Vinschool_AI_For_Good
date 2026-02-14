"""
Zalo notification API endpoints.

Provides REST endpoints for the Zalo clone UI to fetch plain-text
messages sent by the notification service. Also includes a demo
endpoint to trigger a sample daily summary, and a send-daily-summary
endpoint for wiring the real workflow output.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from services.notification.zalo_notifier import ZaloNotifier, zalo_message_store
from services.notification.models import (
    Notification,
    NotificationType,
    NotificationChannel,
    StudentInfo,
    ParentInfo,
)
from utils.logger import logger

router = APIRouter()


# ===== Response Models =====

class ZaloMessageResponse(BaseModel):
    """A single Zalo message returned to the frontend (plain text)."""
    id: str
    sender: str
    text: str
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


class SendDailySummaryRequest(BaseModel):
    """Request body for the send-daily-summary endpoint."""
    content: str  # The AI-generated plain text summary
    student_name: str = "Alex"
    class_name: str = "4B5"


# ===== Template strings =====

PARENT_GREETING = "Bố mẹ các con thân mến,\nCô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:\n\n"
PARENT_CLOSING = "\n\nKính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.\nCảm ơn bố mẹ các con đã đọc tin ạ!"

# Demo content (used by send-demo when no real AI summary is available)
DEMO_PLAIN_TEXT = (
    "1. Môn Science:\n"
    "Tìm hiểu cơ chế hoạt động của hệ tiêu hoá \"digestive system\".\n"
    "Cô Oanh đã phát một phiếu bài tập môn Science, các con hoàn thành và nộp lại cho cô vào thứ Hai nhé.\n"
    "📎 https://drive.google.com/drive/folders/example1\n\n"
    "2. Môn Toán:\n"
    "Cộng và trừ phân số có cùng mẫu số \"denominator\". Bắt đầu học khác mẫu số.\n"
    "Bài tập Toán trong workbook tuần này: Unit 9.1, pages 93-97\n"
    "⏰ hạn nộp thứ Ba 13/01\n"
    "📎 https://drive.google.com/drive/folders/example2\n\n"
    "3. Môn Tiếng Anh:\n"
    "Ôn tập câu điều kiện loại 0 \"zero conditional\" và câu hỏi đuôi.\n"
    "📎 https://classroom.google.com/c/example3"
)


# ===== Endpoints =====

@router.get("/messages", response_model=ZaloMessagesListResponse)
async def get_zalo_messages():
    """
    Get all Zalo messages sent by the notification service.

    The Zalo clone UI polls this endpoint to display messages.
    """
    messages = []
    for msg in zalo_message_store:
        messages.append(ZaloMessageResponse(
            id=msg["id"],
            sender=msg["sender"],
            text=msg["text"],
            time=msg["time"],
            is_ai=msg.get("is_ai", True),
        ))

    return ZaloMessagesListResponse(messages=messages, count=len(messages))


@router.post("/send-demo", response_model=DemoSendResponse)
async def send_demo_notification(request: DemoSendRequest = DemoSendRequest()):
    """
    Send a demo daily summary notification to the Zalo message store.

    Uses hardcoded demo content wrapped with greeting/closing templates.
    Use this to test the Zalo clone UI without running the full backend pipeline.
    """
    full_text = PARENT_GREETING + DEMO_PLAIN_TEXT + PARENT_CLOSING

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
        title=f"Daily Summary - {request.date or datetime.now().strftime('%d/%m/%Y')}",
        message=full_text,
    )

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


@router.post("/send-daily-summary", response_model=DemoSendResponse)
async def send_daily_summary(request: SendDailySummaryRequest):
    """
    Send a daily summary notification with AI-generated content.

    Wraps the provided plain-text content with greeting/closing
    templates and stores it in the Zalo message store.
    This is the endpoint the daily content workflow calls.
    """
    full_text = PARENT_GREETING + request.content + PARENT_CLOSING

    notification = Notification(
        notification_type=NotificationType.DAILY_SUMMARY,
        channel=NotificationChannel.ZALO,
        student=StudentInfo(
            student_id="student-001",
            name=request.student_name,
            grade="4",
            class_name=request.class_name,
        ),
        parent=ParentInfo(
            parent_id="parent-001",
            name=f"Phụ huynh {request.student_name}",
        ),
        title=f"Daily Summary - {datetime.now().strftime('%d/%m/%Y')}",
        message=full_text,
    )

    notifier = ZaloNotifier(enabled=True)
    result = await notifier.send(notification)

    if result.success:
        logger.info(f"Daily summary sent to Zalo: {notification.notification_id}")
        return DemoSendResponse(
            success=True,
            message="Daily summary sent to Zalo",
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
