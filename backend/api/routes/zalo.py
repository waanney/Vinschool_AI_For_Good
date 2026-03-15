"""
Zalo notification API endpoints.

Provides REST endpoints for the Zalo clone UI to fetch plain-text
messages sent by the notification service. Also includes a demo
endpoint to trigger a sample daily summary, a send-daily-summary
endpoint for wiring the real workflow output, and a chat endpoint
that handles the ``/dailysum`` command (hardcoded demo summary).
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
from services.scheduler import DEMO_LESSON_CONTENT, DEMO_LESSON_CONTENT_PARENTS
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
    message: Optional[str] = None  # if provided, used instead of DEMO_PLAIN_TEXT


class DemoSendResponse(BaseModel):
    """Response from the demo send endpoint."""
    success: bool
    message: str
    notification_id: Optional[str] = None


class SendDailySummaryRequest(BaseModel):
    """Request body for the send-daily-summary endpoint."""
    content: str  # The plain text summary
    student_name: str = "Alex"
    class_name: str = "4B5"


# Demo content — /send-demo uses the raw lesson data; /dailysum (chat) uses parent-facing text.
DEMO_PLAIN_TEXT = DEMO_LESSON_CONTENT
DEMO_PLAIN_TEXT_PARENTS = DEMO_LESSON_CONTENT_PARENTS


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

    Uses hardcoded demo content as-is.
    """
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
        message=request.message or DEMO_PLAIN_TEXT,
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
    Send a daily summary notification.

    Stores the content as-is in the Zalo message store.
    This is the endpoint the daily content workflow calls.
    """
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
        message=request.content,
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


# ===== Chat /dailysum endpoint =====

class ChatRequest(BaseModel):
    """Request body for the chat endpoint (/dailysum)."""
    sender: str = "Phụ huynh Alex"
    text: str


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    success: bool
    reply: str = ""
    is_ask: bool = False
    error: Optional[str] = None
    user_msg_id: Optional[str] = None
    ai_msg_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_ask(request: ChatRequest):
    """
    Handle a chat message from the Zalo clone UI.

    Routes the ``/dailysum`` command to the hardcoded demo summary.
    All other messages are stored as-is without an AI reply.

    Example:
        POST /api/zalo/chat
        {"sender": "Phụ huynh Alex", "text": "/dailysum"}
    """
    text = request.text.strip()
    sender = request.sender.strip()
    now = datetime.now().strftime("%H:%M")

    # Store user message in the message store
    import uuid
    user_msg_id = f"user-{str(uuid.uuid4())[:8]}"
    zalo_message_store.append({
        "id": user_msg_id,
        "sender": sender,
        "text": text,
        "time": now,
        "is_ai": False,
    })

    # /dailysum — hardcoded demo summary (no AI cost) — the only active command
    if text.lower().startswith("/dailysum"):
        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": DEMO_PLAIN_TEXT_PARENTS,
            "time": now,
            "is_ai": True,
        })
        return ChatResponse(
            success=True,
            reply=DEMO_PLAIN_TEXT_PARENTS,
            is_ask=True,
            user_msg_id=user_msg_id,
            ai_msg_id=ai_msg_id,
        )

    # Any other message — store only, no AI reply
    return ChatResponse(success=True, reply="", is_ask=False, user_msg_id=user_msg_id)
