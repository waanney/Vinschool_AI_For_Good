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
    DailySummaryContext,
    LessonSummary,
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


class DemoSendRequest(BaseModel):
    student_name: str = "Alex"
    class_name: str = "4B5"
    date: Optional[str] = None


@app.get("/api/zalo/messages")
async def get_messages():
    """Return all stored Zalo messages."""
    messages = []
    for msg in zalo_message_store:
        messages.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "greeting": msg["greeting"],
            "intro": msg["intro"],
            "lessons": msg.get("lessons", []),
            "closing": msg["closing"],
            "time": msg["time"],
            "is_ai": msg.get("is_ai", True),
        })
    return {"messages": messages, "count": len(messages)}


@app.post("/api/zalo/send-demo")
async def send_demo(request: DemoSendRequest = DemoSendRequest()):
    """Send a demo daily summary notification."""
    date_str = request.date or datetime.now().strftime("%d/%m/%Y")

    lessons = [
        LessonSummary(
            subject="Science",
            content='Tìm hiểu cơ chế hoạt động của hệ tiêu hoá "digestive system".',
            homework="Cô Oanh đã phát một phiếu bài tập môn Science, các con hoàn thành và nộp lại cho cô vào thứ Hai nhé.",
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
        message="Cô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:",
        daily_summary_context=DailySummaryContext(
            date=date_str,
            lessons=lessons,
            general_notes="Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.\nCảm ơn bố mẹ các con đã đọc tin ạ!",
        ),
    )

    notifier = ZaloNotifier(enabled=True)
    result = await notifier.send(notification)

    return {
        "success": result.success,
        "message": "Demo notification sent to Zalo message store",
        "notification_id": notification.notification_id,
    }


@app.delete("/api/zalo/messages")
async def clear_messages():
    """Clear all messages."""
    zalo_message_store.clear()
    return {"success": True, "message": "Cleared"}


@app.get("/")
async def root():
    return {"status": "Zalo test server running", "endpoints": ["/api/zalo/messages", "/api/zalo/send-demo"]}


if __name__ == "__main__":
    print("\n🚀 Zalo Test Server starting on http://localhost:8000")
    print("   POST http://localhost:8000/api/zalo/send-demo  -> trigger a notification")
    print("   GET  http://localhost:8000/api/zalo/messages    -> see stored messages")
    print("   Then check http://localhost:3000/zalo/desktop   -> see it in the UI\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
