"""
Lightweight standalone server for testing the Zalo notification API.

Run this directly to test the Zalo notifier -> UI connection
without needing PostgreSQL, Milvus, or other services.

Usage:
    cd backend
    python -m scripts.run_zalo_server
"""

import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.notification.zalo_notifier import ZaloNotifier, zalo_message_store
from services.notification.models import (
    Notification,
    NotificationType,
    NotificationChannel,
    StudentInfo,
    ParentInfo,
)

app = FastAPI(title="Zalo Notification Test Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Template strings =====

PARENT_GREETING = "Bố mẹ các con thân mến,\nCô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:\n\n"
PARENT_CLOSING = "\n\nKính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.\nCảm ơn bố mẹ các con đã đọc tin ạ!"

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


# ===== Request/Response models =====

class DemoSendRequest(BaseModel):
    student_name: str = "Alex"
    class_name: str = "4B5"
    date: Optional[str] = None


class SendDailySummaryRequest(BaseModel):
    content: str
    student_name: str = "Alex"
    class_name: str = "4B5"


# ===== Endpoints =====

@app.get("/api/zalo/messages")
async def get_messages():
    """Return all stored Zalo messages."""
    messages = []
    for msg in zalo_message_store:
        messages.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "text": msg["text"],
            "time": msg["time"],
            "is_ai": msg.get("is_ai", True),
        })
    return {"messages": messages, "count": len(messages)}


@app.post("/api/zalo/send-demo")
async def send_demo(request: DemoSendRequest = DemoSendRequest()):
    """Send a demo daily summary notification with hardcoded content."""
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

    return {
        "success": result.success,
        "message": "Demo notification sent to Zalo message store",
        "notification_id": notification.notification_id,
    }


@app.post("/api/zalo/send-daily-summary")
async def send_daily_summary(request: SendDailySummaryRequest):
    """Send a daily summary with AI-generated content wrapped in templates."""
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

    return {
        "success": result.success,
        "message": "Daily summary sent to Zalo",
        "notification_id": notification.notification_id,
    }


@app.delete("/api/zalo/messages")
async def clear_messages():
    """Clear all messages."""
    zalo_message_store.clear()
    return {"success": True, "message": "Cleared"}


@app.get("/")
async def root():
    return {
        "status": "Zalo test server running",
        "endpoints": [
            "/api/zalo/messages",
            "/api/zalo/send-demo",
            "/api/zalo/send-daily-summary",
        ],
    }


if __name__ == "__main__":
    print("\n🚀 Zalo Test Server starting on http://localhost:8000")
    print("   POST http://localhost:8000/api/zalo/send-demo            -> trigger a demo notification")
    print("   POST http://localhost:8000/api/zalo/send-daily-summary   -> send AI content")
    print("   GET  http://localhost:8000/api/zalo/messages             -> see stored messages")
    print("   Then check http://localhost:3000/zalo/desktop            -> see it in the UI\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
