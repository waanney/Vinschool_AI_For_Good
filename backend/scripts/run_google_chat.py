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

Students interact with the bot in Google Chat using:
    @Vinschool Bot /ask <question>       — AI Q&A
    @Vinschool Bot /grade                — Grade submitted homework images
    @Vinschool Bot /dailysum             — demo daily lesson summary

The script starts a minimal HTTP server on port 8000.
The frontend (Next.js on port 3000) can poll this server
for graded submissions at GET /api/teacher/submissions.
"""

import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===== Mock database modules to avoid requiring Milvus for demo =====
# The grading pipeline (HomeworkGradingWorkflow → GradingAgent → database)
# tries to connect to Milvus at import time. For the demo we don't need
# vector search, so we pre-seed sys.modules with harmless mocks.
from unittest.mock import MagicMock

_mock_db = MagicMock()
for mod_name in [
    "database",
    "database.milvus_client",
    "database.repositories",
    "database.repositories.document_repository",
]:
    sys.modules.setdefault(mod_name, _mock_db)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from utils.logger import logger


# ===== Config check — runs before server starts =====

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


# ===== Lifespan — starts/stops Google Chat listener =====

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
    print("    @Vinschool Bot /ask Bài tập Toán tuần này là gì?")
    print("    @Vinschool Bot /grade (kèm ảnh bài tập)")
    print("    @Vinschool Bot /dailysum")
    print()
    print("  Teacher LMS dashboard:")
    print("    http://localhost:3000 (run frontend with npm run dev)")
    print("    GET http://localhost:8000/api/teacher/submissions")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    listener.stop()
    print("\n  Google Chat listener stopped.")


# ===== FastAPI app =====

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
        "usage": "Send /ask <question>, /grade, /dailysum, or /demosum in Google Chat",
    }


# ===== Lightweight submission endpoints (avoid importing full teacher router) =====
# The full teacher router imports DailyContentWorkflow → database → MilvusClient,
# which crashes without a running Milvus instance. These inline endpoints only
# import submission_store, which has zero heavy dependencies.

from services.chat.submission_store import (
    get_submissions,
    get_unviewed_count,
    mark_viewed,
)


@app.get("/api/teacher/submissions")
async def get_teacher_submissions():
    """Get all graded submissions for the LMS dashboard."""
    submissions = get_submissions()
    return {
        "submissions": submissions,
        "count": len(submissions),
        "unviewed_count": get_unviewed_count(),
    }


@app.post("/api/teacher/submissions/{submission_id}/view")
async def mark_submission_viewed(submission_id: str):
    """Mark a submission as viewed by the teacher."""
    from fastapi import HTTPException

    found = mark_viewed(submission_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found")
    return {"success": True, "submission_id": submission_id}


# ===== Main =====

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
