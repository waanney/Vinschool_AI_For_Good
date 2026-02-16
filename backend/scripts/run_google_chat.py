"""
Lightweight standalone Google Chat listener demo.

Runs the Google Chat Pub/Sub listener WITHOUT needing PostgreSQL, Milvus,
or the full api/main.py. Only requires:
  - .env with Google Chat Pub/Sub settings
  - credentials/ service account JSON
  - Gemini API key

Usage:
    cd backend
    python -m scripts.run_google_chat

The script also starts a minimal HTTP server on port 8000 so you can
test Zalo /ask chat at the same time via POST /api/zalo/chat.
"""

import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional

from config import settings
from utils.logger import logger


# ---------------------------------------------------------------------------
# Config check — runs before server starts
# ---------------------------------------------------------------------------

def _print_config() -> bool:
    """Print current Google Chat configuration and return True if all OK."""
    print("\n" + "=" * 60)
    print("  Google Chat Pub/Sub Listener — Standalone Demo")
    print("=" * 60)

    checks = {
        "GOOGLE_CLOUD_PROJECT_ID": settings.GOOGLE_CLOUD_PROJECT_ID,
        "GOOGLE_CHAT_PUBSUB_SUBSCRIPTION": settings.GOOGLE_CHAT_PUBSUB_SUBSCRIPTION,
        "GOOGLE_APPLICATION_CREDENTIALS": settings.GOOGLE_APPLICATION_CREDENTIALS,
        "GOOGLE_CHAT_SPACE_ID": getattr(settings, "GOOGLE_CHAT_SPACE_ID", ""),
        "gemini_api_key": ("***" + settings.gemini_api_key[-4:]) if settings.gemini_api_key else "",
        "default_provider": settings.default_provider,
        "default_llm_model": settings.default_llm_model,
        "CHAT_DEBOUNCE_SECONDS": getattr(settings, "CHAT_DEBOUNCE_SECONDS", 3.0),
    }

    all_ok = True
    for key, value in checks.items():
        status = "✅" if value else "❌"
        if not value:
            all_ok = False
        print(f"  {status} {key}: {value or '(not set)'}")

    print()
    return all_ok


# ---------------------------------------------------------------------------
# Lifespan — starts/stops Google Chat listener
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Google Chat listener on startup, stop on shutdown."""
    from services.chat import get_google_chat_listener, get_chat_service

    # Pre-initialize ChatService so we know it works
    try:
        svc = get_chat_service()
        print(f"  ✅ ChatService ready (lesson: {len(svc._lesson_context)} chars)")
    except Exception as e:
        print(f"  ❌ ChatService failed: {e}")
        print("     Check your gemini_api_key in .env")
        yield
        return

    # Start the listener
    listener = get_google_chat_listener()
    listener.start()
    print("  ✅ Google Chat Pub/Sub listener started")
    print()
    print("  Now send a message in Google Chat:")
    print("    @Vinschool Bot Bài tập Toán tuần này là gì?")
    print()
    print("  Or test Zalo /ask via HTTP:")
    print('    curl -X POST http://localhost:8000/api/zalo/chat \\')
    print('      -H "Content-Type: application/json" \\')
    print('      -d \'{"text": "/ask Bài tập Toán tuần này?"}\'')
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    listener.stop()
    print("\n  Google Chat listener stopped.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Google Chat Demo Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "Google Chat demo server running",
        "google_chat": "Pub/Sub listener active — @mention the bot in Google Chat",
        "zalo_chat": "POST /api/zalo/chat with {sender, text} (/ask prefix)",
    }


# ---------------------------------------------------------------------------
# Zalo /ask endpoint (so both platforms can be tested from one server)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    sender: str = "Phụ huynh Alex"
    text: str


class ChatResponse(BaseModel):
    success: bool
    reply: str = ""
    is_ask: bool = False
    error: Optional[str] = None
    user_msg_id: Optional[str] = None
    ai_msg_id: Optional[str] = None


@app.post("/api/zalo/chat", response_model=ChatResponse)
async def chat_ask(request: ChatRequest):
    """Handle /ask chat from Zalo UI (or curl)."""
    text = request.text.strip()
    sender = request.sender.strip()

    is_ask = text.startswith("/ask")
    if not is_ask:
        return ChatResponse(success=True, reply="", is_ask=False)

    question = text[4:].strip()
    if not question:
        return ChatResponse(
            success=True,
            reply="Vui lòng nhập câu hỏi sau /ask ạ.\nVí dụ: /ask Bài tập Toán tuần này là gì?",
            is_ask=True,
        )

    try:
        from services.chat import get_chat_service

        chat_service = get_chat_service()
        user_id = f"zalo-{sender}"
        answer = await chat_service.answer(user_id=user_id, question=question, channel="zalo")

        logger.info(f"[DEMO] /ask from {sender}: {question[:60]} → {len(answer)} chars")
        return ChatResponse(success=True, reply=answer, is_ask=True)

    except Exception as e:
        logger.error(f"[DEMO] Error: {e}")
        return ChatResponse(
            success=False,
            reply="Xin lỗi, hệ thống AI đang gặp sự cố. Vui lòng thử lại sau ạ.",
            is_ask=True,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ok = _print_config()
    if not ok:
        print("  ⚠️  Some settings are missing. Check your .env file.")
        print("  The listener may not work without all settings.\n")

    uvicorn.run(
        "scripts.run_google_chat:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
