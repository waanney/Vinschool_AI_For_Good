"""
Chat service for bidirectional AI conversations.

Provides:
- ChatService: Main orchestrator — Zalo (/dailysum, parent-facing) and
  Google Chat (@mention commands + demo trigger phrases, student-facing)
- MessageDebouncer: Per-user message debouncing to batch rapid messages
- GoogleChatListener: Pub/Sub consumer + Chat API replier (with
  hardcoded demo phrase support)
"""

from .chat_service import (
    ChatService,
    get_chat_service,
    reset_chat_service,
    load_lesson_context,
    build_system_prompt,
    clear_history,
    CHANNEL_ZALO,
    CHANNEL_GCHAT,
)
from .debouncer import MessageDebouncer
from .google_chat_listener import GoogleChatListener, get_google_chat_listener

__all__ = [
    "ChatService",
    "get_chat_service",
    "reset_chat_service",
    "load_lesson_context",
    "build_system_prompt",
    "clear_history",
    "CHANNEL_ZALO",
    "CHANNEL_GCHAT",
    "MessageDebouncer",
    "GoogleChatListener",
    "get_google_chat_listener",
]
