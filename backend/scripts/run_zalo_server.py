"""
Lightweight standalone server for testing the Zalo notification API
and chat commands (/ask, /dailysum, /demosum).

Run this directly to test the Zalo notifier -> UI connection
without needing PostgreSQL, Milvus, or other services.

Usage:
    cd backend
    python -m scripts.run_zalo_server
"""

import sys
import os
import uuid

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

# Demo lesson content — imported from scheduler so all commands share the same fixture.
from services.scheduler import DEMO_LESSON_CONTENT, DEMO_LESSON_CONTENT_PARENTS
DEMO_PLAIN_TEXT = DEMO_LESSON_CONTENT
DEMO_PLAIN_TEXT_PARENTS = DEMO_LESSON_CONTENT_PARENTS


# ===== Request/Response models =====

class DemoSendRequest(BaseModel):
    student_name: str = "Alex"
    class_name: str = "4B5"
    date: Optional[str] = None
    message: Optional[str] = None  # if provided, used instead of DEMO_PLAIN_TEXT


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
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


# ===== Shared /chat handler =====

async def _handle_chat(sender: str, text: str) -> ChatResponse:
    """
    Shared chat logic for /ask, /dailysum, and /demosum commands.

    Kept here as a thin wrapper so the standalone script doesn't depend
    on the full api/ package (which needs PostgreSQL/Milvus init).
    """
    now = datetime.now().strftime("%H:%M")
    text = text.strip()
    sender = sender.strip()

    # Generate a stable user-message ID and return it but do NOT push to the
    # store — the frontend adds user messages directly to avoid duplicates.
    user_msg_id = f"user-{str(uuid.uuid4())[:8]}"

    # /help command — show available commands
    if text.lower().startswith("/help"):
        help_text = (
            "📋 Danh sách lệnh Zalo:\n\n"
            "/ask <câu hỏi> — Hỏi đáp AI (Cô Hana sẽ trả lời)\n"
            "/dailysum — Tóm tắt bài học hôm nay (AI tạo tự động)\n"
            "/demosum — Xem bản tóm tắt mẫu (không tốn AI)\n"
            "/help — Hiển thị danh sách lệnh này"
        )
        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": help_text,
            "time": now,
            "is_ai": True,
        })
        return ChatResponse(
            success=True, reply=help_text, is_ask=True,
            user_msg_id=user_msg_id, ai_msg_id=ai_msg_id,
        )

    is_ask = text.startswith("/ask")

    # /dailysum command — AI-generated daily summary
    if text.lower().startswith("/dailysum"):
        try:
            from services.chat.chat_service import get_chat_service
            chat_service = get_chat_service()
            summary = await chat_service.summarize_daily(channel="zalo")
        except Exception as e:
            summary = f"Xin lỗi, hệ thống AI đang gặp sự cố khi tạo tóm tắt. Vui lòng thử lại sau ạ."

        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": summary,
            "time": now,
            "is_ai": True,
        })
        return ChatResponse(
            success=True, reply=summary, is_ask=True,
            user_msg_id=user_msg_id, ai_msg_id=ai_msg_id,
        )

    # /demosum command — hardcoded demo summary (no AI cost)
    if text.lower().startswith("/demosum"):
        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": DEMO_PLAIN_TEXT_PARENTS,
            "time": now,
            "is_ai": True,
        })
        return ChatResponse(
            success=True, reply=DEMO_PLAIN_TEXT_PARENTS, is_ask=True,
            user_msg_id=user_msg_id, ai_msg_id=ai_msg_id,
        )

    if not is_ask:
        return ChatResponse(success=True, reply="", is_ask=False, user_msg_id=user_msg_id)

    question = text[4:].strip()
    if not question:
        hint = "Vui lòng nhập câu hỏi sau /ask ạ.\nVí dụ: /ask Bài tập Toán tuần này là gì?"
        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": hint,
            "time": now,
            "is_ai": True,
        })
        return ChatResponse(success=True, reply=hint, is_ask=True, user_msg_id=user_msg_id, ai_msg_id=ai_msg_id)

    try:
        from services.chat.chat_service import get_chat_service

        chat_service = get_chat_service()
        user_id = f"zalo-{sender}"
        answer = await chat_service.answer(
            user_id=user_id, question=question, channel="zalo", user_name=sender,
        )

        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": answer,
            "time": datetime.now().strftime("%H:%M"),
            "is_ai": True,
        })
        return ChatResponse(success=True, reply=answer, is_ask=True, user_msg_id=user_msg_id, ai_msg_id=ai_msg_id)

    except Exception as e:
        error_text = "Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau ạ."
        ai_msg_id = f"ai-{str(uuid.uuid4())[:8]}"
        zalo_message_store.append({
            "id": ai_msg_id,
            "sender": "Cô Hana (AI)",
            "text": error_text,
            "time": datetime.now().strftime("%H:%M"),
            "is_ai": True,
        })
        return ChatResponse(success=False, reply=error_text, is_ask=True, error=str(e), user_msg_id=user_msg_id, ai_msg_id=ai_msg_id)


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
    """Send the hardcoded demo daily summary to the Zalo message store."""
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


@app.post("/api/zalo/chat", response_model=ChatResponse)
async def chat_ask(request: ChatRequest):
    """
    Handle a chat message from the Zalo clone UI.

    Routes /ask, /dailysum, and /demosum to ChatService.
    Other messages are stored as-is without an AI reply.
    """
    return await _handle_chat(request.sender, request.text)


@app.get("/")
async def root():
    return {
        "status": "Zalo test server running",
        "endpoints": [
            "GET  /api/zalo/messages      — retrieve all stored messages",
            "POST /api/zalo/send-demo     — push the hardcoded demo summary to the Zalo UI",
            "POST /api/zalo/chat          — /ask /dailysum /demosum (used by the clone UI)",
            "DELETE /api/zalo/messages    — clear all stored messages",
        ],
    }


if __name__ == "__main__":
    print("\n🚀 Zalo Test Server starting on http://localhost:8000")
    print("   POST   http://localhost:8000/api/zalo/send-demo    -> push the demo summary to the Zalo UI")
    print("   POST   http://localhost:8000/api/zalo/chat         -> /ask /dailysum /demosum")
    print("   GET    http://localhost:8000/api/zalo/messages     -> see stored messages")
    print("   DELETE http://localhost:8000/api/zalo/messages     -> clear messages")
    print("   Then check http://localhost:3000/zalo/desktop      -> see it in the UI\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
